# Olive Extended Documentation 🫒

This document covers advanced topics, detailed configuration, and in-depth explanations. For a quick start, see the main [README.md](README.md).

## Table of Contents

- [Installation Options](#installation-options)
- [Local vs Remote Tools: Deep Dive](#local-vs-remote-tools-deep-dive)
- [Temporal Integration](#temporal-integration)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Development](#development)
- [FAQ](#faq)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Installation Options

### From GitHub (Recommended)

```bash
# Basic installation
pip install git+https://github.com/YaVendio/olive.git

# With Temporal support for production reliability
pip install "git+https://github.com/YaVendio/olive.git#egg=olive[temporal]"

# Using SSH (if you have SSH keys configured)
pip install git+ssh://git@github.com/YaVendio/olive.git
```

### Using uv (Faster Alternative)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer:

```bash
uv pip install git+https://github.com/YaVendio/olive.git

# With Temporal
uv pip install "git+https://github.com/YaVendio/olive.git#egg=olive[temporal]"
```

### Development Installation

```bash
git clone https://github.com/YaVendio/olive.git
cd olive

# Editable mode
pip install -e .

# With all dependencies
pip install -e ".[all,dev]"
```

### In pyproject.toml

```toml
[project]
dependencies = [
    "olive @ git+https://github.com/YaVendio/olive.git",
]

# Pin to a specific version
dependencies = [
    "olive @ git+https://github.com/YaVendio/olive.git@v1.3.4",
]
```

For CI/CD setup details, see [INSTALL_WITH_UV.md](INSTALL_WITH_UV.md).

---

## Local vs Remote Tools: Deep Dive

### The Problem with Local Tools

LangChain's `@tool` decorator is powerful but **local-only**. Your agent and tools must run in the same process:

```python
from langchain_core.tools import tool

@tool
def query_database(user_id: int) -> dict:
    """Query user from database."""
    # Agent needs direct DB access
    return db.query(user_id)
```

**Limitations:**
- 🚫 Every agent instance needs database credentials
- 🚫 Can't share tools across agents/services
- 🚫 Can't scale agents and tools independently
- 🚫 Non-Python systems can't use your tools
- 🚫 Testing requires full environment setup

### The Remote Solution

Olive transforms tools into HTTP endpoints. The agent calls tools via REST API:

```python
from olive import olive_tool

@olive_tool
def query_database(user_id: int) -> dict:
    """Query user from database."""
    # Only the server needs DB access
    return db.query(user_id)
```

```
┌─────────────────┐         ┌─────────────────┐
│  Your Agent     │  HTTP   │  Olive Server   │
│  (anywhere)     │────────▶│  (your tools)   │
└─────────────────┘         └─────────────────┘
   - No DB access              - DB credentials
   - No API keys               - API keys
   - Lightweight               - Business logic
```

### Side-by-Side Comparison

| Aspect | LangChain `@tool` | Olive `@olive_tool` |
|--------|-------------------|---------------------|
| Execution | Same process | Remote server |
| Dependencies | Agent needs all | Server has all |
| Sharing | Copy-paste code | HTTP endpoint |
| Languages | Python only | Any HTTP client |
| Scaling | Monolithic | Independent |
| Testing | Full env needed | Mock HTTP |

### When to Use Each

**Use LangChain `@tool` when:**
- Building a quick prototype
- Single agent, simple tools
- Tools have no external dependencies

**Use Olive `@olive_tool` when:**
- Multiple agents share tools
- Tools need DB/API access
- Voice agents (ElevenLabs) need tools
- Different teams own agents vs tools
- Production microservices architecture

---

## Temporal Integration

> **Note:** Temporal is completely optional. Olive works perfectly without it using direct execution.

### What is Temporal?

[Temporal](https://temporal.io) is a durable execution platform. When enabled, your tool calls become:
- **Retryable**: Automatic retry on transient failures
- **Durable**: Survives server crashes/restarts
- **Observable**: Full execution history and debugging
- **Distributed**: Scale across multiple workers

### When to Enable Temporal

**Direct execution (default) is fine for:**
- Development and testing
- Simple, fast tools
- Tools that can fail gracefully

**Enable Temporal for:**
- Long-running operations (minutes/hours)
- Critical business operations
- Operations that must not be lost
- When you need detailed execution logs

### Setup

**1. Install with Temporal support:**
```bash
pip install "olive[temporal]"
```

**2. Create `.olive.yaml`:**
```yaml
temporal:
  enabled: true
  address: localhost:7233
  namespace: default
  task_queue: olive-tools
```

**3. Start Temporal server:**
```bash
# Development
temporal server start-dev

# Production: Use Temporal Cloud
```

**4. Run your server:**
```bash
uvicorn server:app
# Now uses Temporal!
```

### Temporal Configuration Options

```yaml
temporal:
  enabled: true
  address: localhost:7233
  namespace: default
  task_queue: olive-tools
  
  # Temporal Cloud (production)
  cloud_namespace: prod.your-namespace
  cloud_api_key: ${TEMPORAL_CLOUD_API_KEY}
```

### Custom Timeouts & Retries

```python
@olive_tool(
    timeout_seconds=600,  # 10 minutes
    retry_policy={
        "max_attempts": 5,
        "initial_interval": 2,
        "backoff_coefficient": 2.0
    }
)
async def long_running_task(data: dict) -> dict:
    """Process with custom reliability settings."""
    return await process(data)
```

### Fire-and-Forget Mode

```python
@olive_tool(fire_and_forget=True)
async def send_notification(email: str, message: str) -> str:
    """Send without waiting for completion."""
    await email_service.send(email, message)
    return "Queued"

# Returns workflow ID immediately
```

---

## Advanced Usage

### Context Injection

Inject runtime context (user IDs, session data) without exposing to the LLM:

```python
from typing import Annotated
from olive import olive_tool, Inject

@olive_tool
def update_user_profile(
    name: str,
    user_id: Annotated[str, Inject("user_id")]  # Hidden from LLM
) -> dict:
    """Update profile. Agent only sees 'name' parameter."""
    return update_database(user_id, name)
```

**Client-side:**
```python
tools = await client.as_langchain_tools_injecting(
    context_provider=lambda cfg: cfg.configurable
)
# user_id injected automatically from config.configurable["user_id"]
```

### Client Features

```python
from olive_client import OliveClient

async with OliveClient("http://your-server.com") as client:
    # List all tools
    tools = await client.get_tools()
    
    # Call tool directly
    result = await client.call_tool("my_tool", {"arg": "value"})
    
    # Filter specific tools
    langchain_tools = await client.as_langchain_tools(
        tool_names=["tool1", "tool2"]
    )
    
    # ElevenLabs format
    elevenlabs_tools = await client.as_elevenlabs_tools()
```

### Mixing Local and Remote Tools

```python
from langchain_core.tools import tool
from olive_client import OliveClient

# Local tool
@tool
def local_calc(x: int) -> int:
    return x * 2

# Remote tools
async with OliveClient("http://server:8000") as client:
    remote_tools = await client.as_langchain_tools()

# Combine both
all_tools = [local_calc] + remote_tools
agent = create_react_agent(model, tools=all_tools)
```

---

## API Reference

### Server Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/olive/tools` | List all registered tools |
| `POST` | `/olive/tools/call` | Execute a tool |
| `GET` | `/olive/tools/elevenlabs` | Tools in ElevenLabs format |
| `GET` | `/docs` | Interactive API docs |

### @olive_tool Decorator

```python
@olive_tool(
    func: Callable = None,
    description: str = None,        # Override docstring
    timeout_seconds: int = 300,     # Temporal timeout
    retry_policy: dict = None,      # Temporal retry config
    fire_and_forget: bool = False   # Return immediately
)
```

### OliveClient Class

```python
class OliveClient:
    def __init__(self, base_url: str, timeout: float = 30.0)
    
    async def get_tools(self) -> list[dict]
    async def call_tool(self, tool_name: str, arguments: dict) -> Any
    async def as_langchain_tools(self, tool_names: list[str] = None) -> list[StructuredTool]
    async def as_elevenlabs_tools(self, tool_names: list[str] = None) -> list[dict]
    async def as_langchain_tools_injecting(self, context_provider: Callable) -> list[StructuredTool]
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Client Side                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │ LangChain  │  │ ElevenLabs │  │   HTTP     │   │
│  │   Agent    │  │ Voice Agent│  │   Client   │   │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘   │
│        └────────────────┴────────────────┘          │
│                         │                           │
│                    HTTP/REST                        │
└─────────────────────────┼───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                  Olive Server                       │
│  ┌──────────────────────────────────────────────┐  │
│  │           FastAPI Application                 │  │
│  │  ┌────────────────┐  ┌────────────────┐     │  │
│  │  │  @olive_tool   │  │  @olive_tool   │     │  │
│  │  │   functions    │  │   functions    │     │  │
│  │  └────────────────┘  └────────────────┘     │  │
│  └──────────────────────────────────────────────┘  │
│              │                      │               │
│         Direct Mode          Temporal Mode          │
│         (default)             (optional)            │
│              │                      │               │
│              ▼                      ▼               │
│    Execute immediately    ┌─────────────────┐      │
│                           │ Temporal Server │      │
│                           │  - Retry logic  │      │
│                           │  - Durability   │      │
│                           │  - Workers      │      │
│                           └─────────────────┘      │
└─────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Temporal
export OLIVE_TEMPORAL_ENABLED=true
export OLIVE_TEMPORAL_ADDRESS=localhost:7233
export OLIVE_TEMPORAL_NAMESPACE=default

# Server
export OLIVE_SERVER_HOST=0.0.0.0
export OLIVE_SERVER_PORT=8000
```

### Config File (.olive.yaml)

```yaml
temporal:
  enabled: false  # Default: disabled
  address: localhost:7233
  namespace: default
  task_queue: olive-tools

server:
  host: 0.0.0.0
  port: 8000
  reload: true

tools:
  default_timeout: 300
  default_retry_attempts: 3
```

### Authentication

Olive focuses on tool execution. Add auth at the FastAPI level:

```python
from fastapi import Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def verify_token(request, call_next):
    # Your auth logic
    return await call_next(request)
```

---

## Development

### Setup

```bash
git clone git@github.com:YaVendio/olive.git
cd olive
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=olive --cov=olive_client --cov-report=html

# Skip Temporal tests
pytest -m "not temporal"
```

### Code Quality

```bash
# Format
ruff format olive/ olive_client/ tests/

# Lint
ruff check olive/ olive_client/ tests/

# Type check
basedpyright olive/ olive_client/
```

### Project Structure

```
olive/
├── olive/                  # Core library
│   ├── decorator.py       # @olive_tool
│   ├── registry.py        # Tool registration
│   ├── router.py          # FastAPI endpoints
│   ├── schemas.py         # Pydantic models
│   ├── server/            # Server factory
│   └── temporal/          # Temporal integration
├── olive_client/          # Client library
├── tests/                 # Test suite
└── pyproject.toml
```

---

## FAQ

### Do I need Temporal?

No. Olive works perfectly without it. Only enable Temporal for production workloads needing retry logic and durability.

### Can I use this with OpenAI function calling?

Yes. The tool schemas are compatible with OpenAI's function calling format.

### How is this different from just using FastAPI?

Olive adds automatic schema generation from type hints, LangChain integration, ElevenLabs support, and optional reliability features. You could build this yourself, but Olive does it in one decorator.

### What about rate limiting?

Add it at the FastAPI level with middleware like `slowapi`.

---

## Roadmap

- [ ] Built-in authentication middleware
- [ ] Rate limiting per tool
- [ ] Tool versioning
- [ ] OpenTelemetry integration
- [ ] Metrics dashboard

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Comparison with Other Tools

| Feature | Olive | LangChain Tools | FastAPI Only |
|---------|-------|----------------|--------------|
| Remote execution | ✅ Built-in | ❌ Local only | ⚠️ Manual |
| LangChain integration | ✅ One line | ✅ Native | ❌ Manual |
| Auto schema generation | ✅ From types | ✅ From types | ⚠️ Manual |
| Multi-agent sharing | ✅ Yes | ❌ No | ✅ Yes |
| Context injection | ✅ Built-in | ❌ No | ⚠️ Manual |
| Reliability (retries) | ✅ Optional | ❌ No | ⚠️ Manual |
| Setup complexity | ⭐ Low | ⭐ Low | ⭐⭐⭐ High |

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/YaVendio">YaVendio</a></sub>
</p>
