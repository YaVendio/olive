# CLAUDE.md

## What is Olive

Olive is a Python framework for exposing functions as remote LLM-callable tools via REST API. Decorate with `@olive_tool`, get a FastAPI server with JSON Schema generation, context injection, optional Temporal durable execution, and client SDKs for LangChain/LangGraph/ElevenLabs.

## Philosophy

- **One decorator, zero boilerplate**: `@olive_tool` registers the function, extracts schemas from type hints, and exposes it via REST. The original function is returned unmodified.
- **Server owns tools, agent consumes them**: Tools are non-deterministic (HTTP, DB, APIs). Deterministic logic stays in the agent.
- **No hidden tools**: Every `@olive_tool` is visible to the LLM. Don't filter tools from the LLM's view.
- **Temporal is optional**: Works without Temporal (direct execution). Add `olive[temporal]` for durable workflows.

## Architecture

### Two Packages in One Wheel

- **`olive/`** — Server-side: decorator, registry, router, schema generation, CLI, Temporal worker
- **`olive_client/`** — Client SDK: `OliveClient` for loading tools into LangChain/LangGraph/ElevenLabs

### Core Flow

```
@olive_tool decorator → ToolRegistry (global singleton) → FastAPI router
                                                           ├── GET  /olive/tools       (list tools, optional ?profile=)
                                                           ├── GET  /olive/tools/elevenlabs
                                                           └── POST /olive/tools/call  (execute tool)
```

### Key Files

| File | Purpose |
|------|---------|
| `olive/__init__.py` | Exports: `olive_tool`, `Inject`, `create_app` (lazy), `setup_olive` (lazy) |
| `olive/decorator.py` | `@olive_tool` — registers function in global registry with schema |
| `olive/schemas.py` | `Inject`, `ToolInfo`, `ToolCallRequest`, schema extraction from type hints |
| `olive/registry.py` | `ToolRegistry` singleton — stores all registered `ToolInfo` objects |
| `olive/router.py` | FastAPI router: `/olive/tools`, `/olive/tools/call`, `/olive/tools/elevenlabs` |
| `olive/server/app.py` | `create_app()` factory — standalone FastAPI app with lifespan |
| `olive/setup.py` | `setup_olive(app)` — mount Olive routes onto existing FastAPI app |
| `olive/config.py` | `OliveConfig` — YAML file + env vars, Temporal/Server/Tools config |
| `olive/cli.py` | CLI: `olive dev`, `olive serve`, `olive init`, `olive version` |
| `olive/temporal/` | `TemporalWorker`, `OliveToolWorkflow`, activity creation |
| `olive_client/client.py` | `OliveClient` — async HTTP client with 4 integration methods |

## Key Concepts

### @olive_tool Decorator

```python
@olive_tool(
    description="Search products",           # Override docstring
    timeout_seconds=300,                     # Temporal workflow timeout
    retry_policy={"max_attempts": 3},        # Temporal retry config
    fire_and_forget=False,                   # Return immediately without waiting
    profiles=["maia_base", "maia_shopify"],  # Profile tags for filtering
)
async def search_product(query: str, merchant_id: Annotated[str, Inject(key="merchant_id")]) -> dict:
    ...
```

- Supports `@olive_tool` (no parens) and `@olive_tool(...)` (with params)
- Extracts JSON Schema from type hints via `python_type_to_json_schema()`
- Handles: `str`, `int`, `float`, `bool`, `list[T]`, `dict[K,V]`, `Optional[T]`, `Literal[...]`, `Union`, `BaseModel`, `Annotated[T, Field(...)]`
- Returns the original function unchanged (no wrapping)

### Context Injection via Inject

```python
from olive import Inject
from typing import Annotated

@olive_tool(profiles=["maia_base"])
async def confirm_order(
    items: list[dict],                                              # LLM sees this
    merchant_id: Annotated[str, Inject(key="merchant_id")],         # LLM does NOT see this
    notification_email: Annotated[str, Inject(key="notification_email")],
) -> dict:
    ...
```

- `Inject(key="...")` marks a parameter as injected from runtime context
- Injected params are **excluded** from the tool's input schema (invisible to LLM)
- Server fills them from `ToolCallRequest.context` at call time
- **Important**: injected params (no default) must come before optional params (with default) in the function signature

### Profiles

Tools declare which profiles they belong to. Consumers filter by profile:

```python
# Server side
@olive_tool(profiles=["maia_base", "maia_shopify", "maia_full"])
async def search_product(...): ...

@olive_tool(profiles=["maia_shopify", "maia_full"])
async def get_link_for_shopify_cart(...): ...

# Client side
tools = await client.as_langgraph_tools(profile="maia_base")  # Only search, not shopify
```

### OliveClient Integration Methods

| Method | Use Case | Context Injection |
|--------|----------|-------------------|
| `as_langchain_tools()` | Basic LangChain | None |
| `as_langchain_tools_injecting()` | LangChain with `get_config()` | Via `context_provider(config)` callback |
| `as_langgraph_tools()` | LangGraph with `ToolRuntime` | Via `runtime.context` (dict or dataclass) |
| `as_elevenlabs_tools()` | ElevenLabs voice agents | Stored context on client |

**`as_langgraph_tools()`** is the primary method for YV. It:
1. Fetches tools from `/olive/tools?profile=...`
2. Builds Pydantic `ArgsSchema` models (excluding injected params)
3. Creates async callables that extract context from `ToolRuntime.context`
4. Returns `StructuredTool` instances compatible with `create_agent()`

### Configuration (.olive.yaml)

```yaml
server:
  host: 0.0.0.0
  port: 8040
  app: app:app          # Uvicorn import path
  factory: false         # true if app is a factory function

temporal:
  enabled: false         # Set true to enable Temporal worker
  address: localhost:7233
  namespace: default
  task_queue: olive-tools
```

Config hierarchy: `.olive.yaml` → environment variables (`OLIVE_TEMPORAL_ENABLED`, `OLIVE_SERVER_PORT`, etc.)

Temporal auto-enables if non-default config is detected (custom address, cloud config, TLS) **unless** `enabled: false` is explicitly set.

## CLI Commands

```bash
olive dev                        # Dev mode: auto-starts Temporal, hot-reload
olive serve --config .olive.prd.yaml  # Production mode: connects to existing Temporal
olive init                       # Scaffold new project
olive version                    # Show version
```

Both `dev` and `serve` respect `temporal.enabled: false` (fixed in v1.4.2).

## Creating an Olive Tool Server

```python
# src/app.py
from olive import create_app
import tools.search     # triggers @olive_tool registration
import tools.orders     # noqa: F401

app = create_app()

@app.on_event("shutdown")
async def shutdown():
    await close_client()
```

Run with: `olive serve --config .olive.yaml` or `uvicorn app:app`

## Conventions

- Python >=3.12
- Ruff linting (line-length 120, target py313)
- basedpyright for type checking (standard mode)
- pytest with asyncio_mode=auto
- 100% test coverage target
- MIT license
