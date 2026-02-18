# Olive Extended Documentation

Advanced topics, detailed configuration, and in-depth explanations. For a quick start, see [README.md](README.md).

## Table of Contents

- [Installation Options](#installation-options)
- [Local vs Remote Tools](#local-vs-remote-tools)
- [Context Injection](#context-injection)
- [Profiles](#profiles)
- [Temporal Integration](#temporal-integration)
- [Error Handling](#error-handling)
- [Client SDK Reference](#client-sdk-reference)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Configuration Reference](#configuration-reference)
- [Authentication](#authentication)
- [Deployment](#deployment)
- [FAQ](#faq)

---

## Installation Options

### From GitHub

```bash
# Basic
pip install git+https://github.com/YaVendio/olive.git

# With Temporal
pip install "git+https://github.com/YaVendio/olive.git#egg=olive[temporal]"

# SSH
pip install git+ssh://git@github.com/YaVendio/olive.git
```

### Using uv

```bash
uv add git+https://github.com/YaVendio/olive.git

# With Temporal
uv add "olive[temporal] @ git+https://github.com/YaVendio/olive.git"
```

### Development

```bash
git clone https://github.com/YaVendio/olive.git
cd olive
uv sync --all-extras
```

### In pyproject.toml

```toml
[project]
dependencies = [
    "olive @ git+https://github.com/YaVendio/olive.git",
]
```

For CI/CD setup details, see [INSTALL_WITH_UV.md](INSTALL_WITH_UV.md).

---

## Local vs Remote Tools

### The Problem with Local Tools

LangChain's `@tool` runs in the same process as the agent:

```python
from langchain_core.tools import tool

@tool
def query_database(user_id: int) -> dict:
    # Agent needs direct DB access
    return db.query(user_id)
```

Every agent instance carries database credentials, API keys, and dependencies. You can't scale agents without duplicating that infrastructure.

### The Remote Solution

Olive moves tool execution to a standalone server:

```
Agent (anywhere)  ── HTTP ──>  Olive Server (your tools)
  - No DB access                 - DB credentials
  - No API keys                  - API keys
  - Lightweight                  - Business logic
```

### When to Use Each

| Scenario | LangChain `@tool` | Olive `@olive_tool` |
|----------|-------------------|---------------------|
| Quick prototype | Good fit | Overkill |
| Single agent, no external deps | Good fit | Unnecessary |
| Multiple agents sharing tools | Poor fit | Good fit |
| Tools with DB/API access | Credential sprawl | Centralized |
| Voice agents (ElevenLabs) | Not supported | Built-in |
| Microservices architecture | Manual work | One decorator |

---

## Context Injection

Inject runtime context (user IDs, session tokens, tenant info) into tool calls without exposing the parameters to the LLM.

### How It Works

```python
from typing import Annotated
from olive import olive_tool, Inject

@olive_tool
def get_orders(
    status: str,                                          # LLM sees this
    merchant_id: Annotated[str, Inject("merchant_id")],   # Hidden from LLM
) -> list[dict]:
    """Get orders by status."""
    return db.query(merchant_id=merchant_id, status=status)
```

The LLM sees a tool with one parameter (`status`). The server fills `merchant_id` from the request's `context` dict.

### Type Validation

Injected values are type-checked at call time. If the context provides `{"merchant_id": 42}` but the parameter declares `str`, Olive returns a `validation_error` before the function runs.

### Client-Side Context

**LangGraph (recommended):**

```python
tools = await client.as_langgraph_tools(profile="base")
# Context flows via ToolRuntime.context automatically
```

**Direct HTTP:**

```bash
curl -X POST http://localhost:8000/olive/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_orders",
    "arguments": {"status": "pending"},
    "context": {"merchant_id": "m_123"}
  }'
```

### Ordering Rule

Injected parameters without defaults must come before optional parameters with defaults in the function signature.

```python
# Correct
def tool(name: str, user_id: Annotated[str, Inject("uid")], limit: int = 10): ...

# Incorrect — SyntaxError
def tool(name: str, limit: int = 10, user_id: Annotated[str, Inject("uid")]): ...
```

---

## Profiles

Tag tools by profile so different agents load different tool sets.

### Server Side

```python
@olive_tool(profiles=["base", "shopify", "full"])
async def search_products(query: str) -> list[dict]: ...

@olive_tool(profiles=["shopify", "full"])
async def create_shopify_cart(items: list[dict]) -> dict: ...

@olive_tool(profiles=["full"])
async def admin_reset(target: str) -> dict: ...
```

### Client Side

```python
# Base agent: only search_products
tools = await client.as_langgraph_tools(profile="base")

# Shopify agent: search_products + create_shopify_cart
tools = await client.as_langgraph_tools(profile="shopify")

# Full agent: all tools
tools = await client.as_langgraph_tools(profile="full")
```

### HTTP

```
GET /olive/tools?profile=base
```

Profile matching is case-insensitive.

---

## Temporal Integration

Optional durable execution for production workloads. Without Temporal, tools execute directly in the FastAPI process with timeout enforcement.

### When to Enable Temporal

| Scenario | Direct (default) | Temporal |
|----------|------------------|----------|
| Development | Good | Unnecessary |
| Fast tools (<5s) | Good | Unnecessary |
| Long-running tools (minutes+) | Risky | Good |
| Must not lose executions | Risky | Good |
| Need retry with backoff | Manual | Built-in |
| Execution audit trail | Logs only | Full history |

### Setup

```bash
pip install "olive[temporal]"
```

```yaml
# .olive.yaml
temporal:
  enabled: true
  address: localhost:7233
  namespace: default
  task_queue: olive-tools
```

```bash
# Start Temporal (development)
temporal server start-dev

# Run Olive
olive serve
```

### Per-Tool Configuration

Timeout and retry settings from the decorator flow through to Temporal's `execute_activity()`:

```python
@olive_tool(
    timeout_seconds=600,
    retry_policy={
        "max_attempts": 5,
        "initial_interval": 2,
        "maximum_interval": 60,
    },
)
async def generate_report(report_id: str) -> dict:
    """Long-running task with custom retry."""
    ...
```

### Fire-and-Forget

Return a workflow ID immediately without waiting for completion:

```python
@olive_tool(fire_and_forget=True)
async def send_batch_emails(campaign_id: str) -> str:
    """Starts execution, returns workflow ID."""
    ...
```

Response:

```json
{
  "success": true,
  "result": "Workflow started: olive-tool-send_batch_emails-a1b2c3",
  "metadata": {
    "executed_via": "temporal",
    "workflow_id": "olive-tool-send_batch_emails-a1b2c3",
    "fire_and_forget": true
  }
}
```

### Temporal Cloud

```yaml
temporal:
  enabled: true
  namespace_endpoint: prod.your-namespace.tmprl.cloud:7233
  namespace: prod
  cloud_namespace: prod.your-namespace
  cloud_api_key: ${TEMPORAL_CLOUD_API_KEY}
  client_cert_path: /path/to/client.pem
  client_key_path: /path/to/client-key.pem
```

---

## Error Handling

Every tool call returns a structured response with machine-readable error types.

### Response Format

```json
{
  "success": true,
  "result": {"data": "..."},
  "error": null,
  "error_type": null,
  "metadata": null
}
```

### Error Types

| `error_type` | Cause | Retryable |
|--------------|-------|-----------|
| `tool_not_found` | Tool name not in registry | No |
| `missing_context` | Required injection key absent from context | No (fix request) |
| `validation_error` | Injected value type mismatch | No (fix context) |
| `execution_error` | Tool function raised an exception | Maybe |
| `timeout` | Execution exceeded `timeout_seconds` | Maybe |

### Example Error Response

```json
{
  "success": false,
  "result": null,
  "error": "Tool 'search' timed out after 30s",
  "error_type": "timeout",
  "metadata": null
}
```

Full stack traces are logged server-side via `logger.exception()`. The client receives a clean error string.

---

## Client SDK Reference

### OliveClient

```python
from olive_client import OliveClient

async with OliveClient("http://localhost:8000") as client:
    # List tools
    tools = await client.get_tools()
    tools = await client.get_tools(profile="base")

    # Call a tool directly
    result = await client.call_tool("my_tool", {"arg": "value"})
    result = await client.call_tool("my_tool", {"arg": "value"}, context={"user_id": "123"})
```

### Integration Methods

| Method | Use Case | Context Source |
|--------|----------|----------------|
| `as_langgraph_tools()` | LangGraph agents | `ToolRuntime.context` (auto-injected) |
| `as_langchain_tools()` | Basic LangChain chains | None |
| `as_elevenlabs_tools()` | ElevenLabs voice agents | Pre-stored on client |

`as_langchain_tools_injecting()` is deprecated. Use `as_langgraph_tools()` instead.

### LangGraph Example

```python
from olive_client import OliveClient
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

async with OliveClient("http://localhost:8000") as client:
    tools = await client.as_langgraph_tools(profile="base")
    agent = create_react_agent(ChatAnthropic(model="claude-sonnet-4-20250514"), tools=tools)
    response = await agent.ainvoke({"messages": [("user", "Search for laptops")]})
```

### Mixing Local and Remote Tools

```python
from langchain_core.tools import tool

@tool
def local_calc(x: int) -> int:
    """Local tool."""
    return x * 2

async with OliveClient("http://server:8000") as client:
    remote_tools = await client.as_langgraph_tools()

all_tools = [local_calc] + remote_tools
agent = create_react_agent(model, tools=all_tools)
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/olive/tools` | List tools. Optional `?profile=` filter |
| `POST` | `/olive/tools/call` | Execute a tool |
| `GET` | `/olive/tools/elevenlabs` | Tools in ElevenLabs format |
| `GET` | `/olive/health` | Health check |
| `GET` | `/docs` | Interactive OpenAPI docs |

### @olive_tool Decorator

```python
@olive_tool(
    description: str = None,          # Override docstring
    timeout_seconds: int = 300,       # Execution timeout
    retry_policy: dict = None,        # Temporal retry config
    fire_and_forget: bool = False,    # Return workflow ID immediately
    profiles: list[str] = None,       # Profile tags for filtering
)
```

### Health Check

```
GET /olive/health
```

```json
{
  "status": "ok",
  "tools_count": 12,
  "temporal_connected": true
}
```

---

## Architecture

```
Client Side
  LangChain Agent / ElevenLabs Voice Agent / HTTP Client
                          |
                     HTTP / REST
                          |
Server Side
  FastAPI Application
   ├── @olive_tool decorated functions
   ├── ToolRegistry (thread-safe, lock-protected)
   └── Router
        ├── GET  /olive/tools          → list, filter by profile
        ├── POST /olive/tools/call     → inject context, validate types, execute
        ├── GET  /olive/tools/elevenlabs
        └── GET  /olive/health
                    |
             Execution Engine
              ├── Direct: asyncio.wait_for(func(), timeout)
              └── Temporal: OliveToolWorkflow → durable activity
```

Two packages ship in one wheel:

| Package | Contents |
|---------|----------|
| `olive/` | Server: decorator, registry, router, schemas, config, CLI, Temporal worker |
| `olive_client/` | Client SDK: `OliveClient` with LangChain / LangGraph / ElevenLabs integration |

---

## Configuration Reference

### .olive.yaml

```yaml
server:
  host: 0.0.0.0           # Bind address
  port: 8000               # Port
  app: app:app             # Uvicorn import path
  factory: false           # True if app is a factory function
  reload: true             # Hot-reload (dev only)

temporal:
  enabled: false           # Enable Temporal worker
  address: localhost:7233  # Temporal server address
  namespace: default       # Temporal namespace
  task_queue: olive-tools  # Task queue name

  # Temporal Cloud
  namespace_endpoint: null       # Cloud endpoint (overrides address)
  cloud_namespace: null          # Cloud namespace
  cloud_api_key: null            # Cloud API key
  client_cert_path: null         # mTLS client cert
  client_key_path: null          # mTLS client key
  server_root_ca_path: null      # Server root CA
  server_name: null              # TLS server name

tools:
  default_timeout: 300           # Default timeout (seconds)
  default_retry_attempts: 3      # Default retry attempts
```

### Environment Variables

All config values can be overridden with environment variables using the `OLIVE_` prefix:

```bash
OLIVE_SERVER_PORT=8040
OLIVE_SERVER_HOST=127.0.0.1
OLIVE_TEMPORAL_ENABLED=true
OLIVE_TEMPORAL_ADDRESS=temporal.internal:7233
OLIVE_TEMPORAL_NAMESPACE=production
```

### Config Precedence

`.olive.yaml` values are loaded first, then environment variables override them.

Temporal auto-enables when non-default config is detected (custom address, cloud config, TLS) unless `enabled: false` is explicitly set.

---

## Authentication

Olive focuses on tool execution. Add authentication at the FastAPI level:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def verify_token(request, call_next):
    if request.url.path.startswith("/olive/"):
        auth = request.headers.get("authorization")
        if not auth or not verify(auth):
            raise HTTPException(status_code=401)
    return await call_next(request)
```

Or use FastAPI dependencies on the router directly.

---

## Deployment

### Standalone

```bash
olive serve --config .olive.prd.yaml
```

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install . && pip install "olive[temporal]"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Mount on Existing App

```python
from fastapi import FastAPI
from olive import setup_olive

app = FastAPI()
setup_olive(app)  # Adds /olive/* routes
```

---

## FAQ

**Do I need Temporal?**
No. Olive works without it. Enable Temporal for production workloads that need retries, durable execution, or fire-and-forget semantics.

**Can I use this with OpenAI function calling?**
Yes. The tool schemas are JSON Schema, compatible with OpenAI's function calling format.

**How is this different from just using FastAPI?**
Olive adds automatic schema generation from type hints, context injection hidden from the LLM, profile-based filtering, timeout enforcement, structured errors, LangChain/LangGraph/ElevenLabs client SDKs, and optional Temporal integration. You could build this yourself, but Olive does it in one decorator.

**What about rate limiting?**
Add it at the FastAPI level with middleware like `slowapi` or deploy behind an API gateway.

**What about streaming?**
Olive is request/response. For long-running tools, use Temporal's fire-and-forget mode and poll for results via the workflow ID.
