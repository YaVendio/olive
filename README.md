# Olive

[![Tests](https://github.com/YaVendio/olive/actions/workflows/tests.yml/badge.svg)](https://github.com/YaVendio/olive/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FYaVendio%2Folive%2Fmain%2Fpyproject.toml)](https://github.com/YaVendio/olive/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Remote tool server for AI agents. One decorator, plain HTTP, production-ready.

```python
from olive import olive_tool, create_app

@olive_tool
def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    return {"temp": 72, "city": city}

app = create_app()
```

```bash
uvicorn server:app
```

Your function is now a REST endpoint any AI agent can call.

---

## The Problem

LangChain's `@tool` is local-only. Agent and tools must run in the same process. That means every agent carries its own database credentials, API keys, and dependencies. You can't scale them independently, and you can't share tools across agents.

## How Olive Solves It

Olive moves tools to a standalone HTTP server. Agents connect over REST.

```
Agent A ──┐
Agent B ──┼── HTTP ──> Olive Tool Server ──> DB, APIs, Services
Agent C ──┘
```

- **One tool server, many agents.** Deploy tools once. Connect any number of agents.
- **Credentials stay on the server.** Agents never touch database connections or API keys.
- **Scale independently.** Add agent replicas without duplicating tool infrastructure.
- **Debug with curl.** Plain HTTP. No protocol adapters, no session state, no pipes.

---

## Install

```bash
pip install git+https://github.com/YaVendio/olive.git
```

With [uv](https://github.com/astral-sh/uv):

```bash
uv add git+https://github.com/YaVendio/olive.git
```

For durable execution with [Temporal](https://temporal.io):

```bash
pip install "olive[temporal] @ git+https://github.com/YaVendio/olive.git"
```

Requires Python 3.12+.

---

## Quick Start

### 1. Define tools

```python
# server.py
from olive import olive_tool, create_app

@olive_tool
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    """Calculate tax on an amount."""
    return amount * rate

@olive_tool
async def fetch_user(user_id: int) -> dict:
    """Fetch user from database."""
    return {"id": user_id, "name": "Jane Doe"}

app = create_app()
```

### 2. Run

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 3. Call from an agent

```python
from olive_client import OliveClient
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

async with OliveClient("http://localhost:8000") as client:
    tools = await client.as_langgraph_tools()

    agent = create_react_agent(ChatAnthropic(model="claude-sonnet-4-20250514"), tools=tools)
    response = await agent.ainvoke({
        "messages": [("user", "Calculate tax on $1000")]
    })
```

Or call directly with HTTP:

```bash
curl -X POST http://localhost:8000/olive/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "calculate_tax", "arguments": {"amount": 1000}}'
```

---

## Core Features

### Context Injection

Pass runtime context (user IDs, session tokens, tenant info) to tools without exposing it to the LLM. Injected parameters are excluded from the tool's schema and type-validated at call time.

```python
from typing import Annotated
from olive import olive_tool, Inject

@olive_tool
def get_orders(
    status: str,                                          # LLM sees this
    merchant_id: Annotated[str, Inject("merchant_id")],   # LLM does not see this
) -> list[dict]:
    """Get orders by status. merchant_id is injected from runtime context."""
    return db.query(merchant_id=merchant_id, status=status)
```

The agent calls `get_orders(status="pending")`. The server fills `merchant_id` from the request context automatically.

### Profiles

Tag tools by profile. Agents load only the tools they need.

```python
@olive_tool(profiles=["base", "shopify"])
async def search_products(query: str) -> list[dict]: ...

@olive_tool(profiles=["shopify"])
async def create_shopify_cart(items: list[dict]) -> dict: ...
```

```python
# Agent loads only "base" tools (search_products, not create_shopify_cart)
tools = await client.as_langgraph_tools(profile="base")
```

### Type-Safe Schemas

Olive generates JSON Schema from Python type hints. Supports `str`, `int`, `float`, `bool`, `list[T]`, `dict[K,V]`, `Optional[T]`, `Literal[...]`, `Union`, `BaseModel`, and `Annotated[T, Field(...)]`.

```python
from pydantic import BaseModel, Field
from typing import Literal

class SearchFilters(BaseModel):
    category: str
    min_price: float = 0

@olive_tool
def search(
    query: str,
    sort: Literal["price", "relevance", "date"] = "relevance",
    filters: SearchFilters | None = None,
) -> list[dict]:
    """Full type information is preserved in the schema."""
    ...
```

### Request Timeouts

Every tool call has an enforced timeout. Configure per-tool via the decorator.

```python
@olive_tool(timeout_seconds=30)
async def slow_api_call(url: str) -> dict:
    """Times out after 30 seconds instead of the default 300."""
    ...
```

Direct execution uses `asyncio.wait_for`. Temporal mode uses workflow-level timeouts with retry policies.

### Structured Errors

Tool failures return machine-readable error types for programmatic retry logic.

```json
{
  "success": false,
  "error": "Tool 'search' timed out after 30s",
  "error_type": "timeout"
}
```

Error types: `tool_not_found`, `missing_context`, `validation_error`, `execution_error`, `timeout`.

### Multi-Platform Client SDK

```python
async with OliveClient("http://localhost:8000") as client:
    # LangGraph agents (recommended) — context via ToolRuntime
    tools = await client.as_langgraph_tools(profile="base")

    # LangChain chains — no context injection
    tools = await client.as_langchain_tools()

    # ElevenLabs voice agents
    tools = await client.as_elevenlabs_tools(context={"user_id": "123"})
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/olive/tools` | List tools. Optional `?profile=` filter. |
| `POST` | `/olive/tools/call` | Execute a tool. |
| `GET` | `/olive/tools/elevenlabs` | Tools in ElevenLabs format. |
| `GET` | `/olive/health` | Health check: tool count, Temporal status. |
| `GET` | `/docs` | Interactive OpenAPI docs. |

---

## Temporal Integration

For production workloads that need automatic retries, durable execution, and fire-and-forget semantics.

```bash
pip install "olive[temporal]"
```

```yaml
# .olive.yaml
temporal:
  enabled: true
  address: localhost:7233
  task_queue: olive-tools
```

Configure per-tool:

```python
@olive_tool(
    timeout_seconds=600,
    retry_policy={"max_attempts": 5, "initial_interval": 2},
    fire_and_forget=True,  # Return workflow ID immediately
)
async def generate_report(report_id: str) -> dict:
    """Long-running task. Executes durably via Temporal."""
    ...
```

Temporal is optional. Without it, tools execute directly in the FastAPI process with timeout enforcement.

---

## CLI

```bash
olive init                           # Scaffold a new project
olive dev                            # Dev server with hot-reload (auto-starts Temporal)
olive serve --config .olive.prd.yaml # Production server
olive version                        # Print version
```

---

## Configuration

Olive reads `.olive.yaml` in the working directory, overridable by environment variables.

```yaml
server:
  host: 0.0.0.0
  port: 8000
  app: app:app
  factory: false

temporal:
  enabled: false
  address: localhost:7233
  namespace: default
  task_queue: olive-tools
```

Environment variable format: `OLIVE_SERVER_PORT=8040`, `OLIVE_TEMPORAL_ENABLED=true`.

---

## Mount on an Existing App

Already have a FastAPI application? Mount Olive as a sub-router instead of using `create_app()`.

```python
from fastapi import FastAPI
from olive import setup_olive

app = FastAPI()
setup_olive(app)  # Adds /olive/* routes

@app.get("/")
def root():
    return {"status": "ok"}
```

---

## Architecture

```
@olive_tool decorator
        |
        v
  ToolRegistry (thread-safe singleton)
        |
        v
  FastAPI Router
   ├── GET  /olive/tools          (list, filter by profile)
   ├── POST /olive/tools/call     (execute with context injection)
   ├── GET  /olive/tools/elevenlabs
   └── GET  /olive/health
        |
        v
  Execution Engine
   ├── Direct: asyncio.wait_for(func(), timeout)
   └── Temporal: OliveToolWorkflow → durable activity execution
```

Two packages ship in one wheel:

| Package | Purpose |
|---------|---------|
| `olive/` | Server: decorator, registry, router, schemas, config, CLI, Temporal |
| `olive_client/` | Client SDK: `OliveClient` for LangChain / LangGraph / ElevenLabs |

---

## Further Reading

- **[EXTENDED_README.md](EXTENDED_README.md)** -- Advanced usage, Temporal deep-dive, full API reference
- **[CONTRIBUTING.md](CONTRIBUTING.md)** -- Development setup and contribution guide
- **[CHANGELOG.md](CHANGELOG.md)** -- Version history

## License

[MIT](LICENSE)
