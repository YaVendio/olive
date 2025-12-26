# Olive 🫒

[![Tests](https://github.com/YaVendio/olive/actions/workflows/tests.yml/badge.svg)](https://github.com/YaVendio/olive/actions/workflows/tests.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FYaVendio%2Folive%2Fmain%2Fpyproject.toml)](https://github.com/YaVendio/olive/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/YaVendio/olive)](https://github.com/YaVendio/olive/releases)

_[Documentación en español](README.md) · [Spanish Documentation](README.md)_

**Transform Python functions into remote tools for AI agents.** Olive lets you expose your functions as REST APIs that LangChain agents, ElevenLabs voice agents, and other AI systems can call remotely.

```python
from olive import olive_tool, create_app

@olive_tool
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    return {"temp": 72, "city": city}

app = create_app()
# That's it! Your function is now a remote tool.
```

> **📦 Installation Note:** Olive is distributed via GitHub, not PyPI.  
> Install with: `pip install git+https://github.com/YaVendio/olive.git`  
> For detailed options, see the [Installation](#installation) section below.

---

## Why Olive?

### The Problem

**LangChain's `@tool` decorator is local-only.** Your agent and tools must run in the same process. This creates problems:

- 🚫 Can't share tools across multiple agents
- 🚫 Agent needs access to all tool dependencies (databases, APIs, credentials)
- 🚫 Can't scale agents and tools independently
- 🚫 No way to call tools from non-Python systems

### The Olive Solution

**Olive makes your tools remote-callable via REST API.** Think of it as "tools-as-a-service."

```
┌─────────────────┐         ┌─────────────────┐
│  Your Agent     │  HTTP   │  Olive Server   │
│  (anywhere)     │────────▶│  (your tools)   │
└─────────────────┘         └─────────────────┘
   - Python                    - Database access
   - JavaScript                - API credentials
   - Voice (ElevenLabs)        - Business logic
   - Multiple agents           - Shared resources
```

**Benefits:**
- ✅ One tool server, many agents
- ✅ Centralized credentials and resources
- ✅ Language-agnostic (any HTTP client)
- ✅ Independent scaling
- ✅ Works immediately - no setup required

---

## Installation

Olive is distributed via GitHub. Choose the installation method that works best for you:

### From GitHub (Recommended)

```bash
# Basic installation (without Temporal)
pip install git+https://github.com/YaVendio/olive.git

# With Temporal support for production
pip install "git+https://github.com/YaVendio/olive.git#egg=olive[temporal]"

# Using SSH (if you have SSH keys configured)
pip install git+ssh://git@github.com/YaVendio/olive.git
```

### Using uv (Faster Alternative)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer:

```bash
# Install with uv
uv pip install git+https://github.com/YaVendio/olive.git

# With Temporal
uv pip install "git+https://github.com/YaVendio/olive.git#egg=olive[temporal]"
```

### Development Installation

For local development or testing:

```bash
# Clone the repository
git clone https://github.com/YaVendio/olive.git
cd olive

# Install in editable mode (changes reflect immediately)
pip install -e .

# Or with Temporal support
pip install -e ".[temporal]"

# Or with all optional dependencies
pip install -e ".[all,dev]"
```

### From Local Path

If you have a local copy:

```bash
# Without Temporal
pip install /path/to/olive

# With Temporal
pip install "/path/to/olive[temporal]"
```

### In pyproject.toml

Add to your project's dependencies:

```toml
[project]
dependencies = [
    "olive @ git+https://github.com/YaVendio/olive.git",
]

# Or for a specific version/tag
dependencies = [
    "olive @ git+https://github.com/YaVendio/olive.git@v1.3.4",
]
```

For detailed installation instructions including CI/CD setup, see [INSTALL_WITH_UV.md](INSTALL_WITH_UV.md).

---

## Quick Start (60 seconds)

### 1. Install

```bash
# From GitHub (no Temporal - fastest start)
pip install git+https://github.com/YaVendio/olive.git

# Or if you need Temporal support for production
pip install "git+https://github.com/YaVendio/olive.git#egg=olive[temporal]"
```

### 2. Create Your Tool Server

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
    # Your database logic here
    return {"id": user_id, "name": "John Doe"}

app = create_app()
```

### 3. Run It

```bash
uvicorn server:app
```

**Done!** Your tools are now accessible at `http://localhost:8000`

### 4. Use from LangChain Agent

```python
from olive_client import OliveClient
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

# Connect to your tool server
async with OliveClient("http://localhost:8000") as client:
    tools = await client.as_langchain_tools()
    
    # Create agent with remote tools
    model = ChatAnthropic(model="claude-3-sonnet")
    agent = create_react_agent(model, tools=tools)
    
    # Agent can now call your tools remotely!
    response = await agent.ainvoke({
        "messages": [("user", "Calculate tax on $1000")]
    })
```

---

## Core Concepts

### Local vs Remote Tools

**LangChain `@tool` (Local)**
```python
from langchain_core.tools import tool

@tool
def my_tool(x: int) -> int:
    """A tool."""
    return x * 2

# Tool runs in SAME process as agent
# Agent needs direct access to tool's dependencies
```

**Olive `@olive_tool` (Remote)**
```python
from olive import olive_tool

@olive_tool
def my_tool(x: int) -> int:
    """A tool."""
    return x * 2

# Tool runs in SEPARATE server
# Agent calls via HTTP - no dependencies needed
```

### When to Use Each

| Use Case | LangChain `@tool` | Olive `@olive_tool` |
|----------|-------------------|---------------------|
| Single agent, simple tools | ✅ | ⚠️ (overkill) |
| Multiple agents sharing tools | ❌ | ✅ |
| Tools need DB/API access | ⚠️ (agent needs credentials) | ✅ (server has credentials) |
| Tools in different languages | ❌ | ✅ |
| Scale agents independently | ❌ | ✅ |
| Voice agents (ElevenLabs) | ❌ | ✅ |
| Production deployment | ⚠️ (complex) | ✅ (microservices) |

**Rule of thumb:** Start with LangChain `@tool` for prototypes. Use Olive when you need to share tools, hide credentials, or scale.

---

## Key Features

### 🎯 **Zero Configuration**
Works out of the box. No setup, no config files, no external services required.

### 🔧 **Type-Safe**
Automatic schema generation from Python type hints. Full Pydantic validation.

```python
@olive_tool
def process_data(
    items: list[str],
    threshold: int = 10,
    options: dict[str, bool] | None = None
) -> dict:
    """Schemas auto-generated from type hints."""
    return {"processed": len(items)}
```

### 🚀 **Async Support**
Seamless support for async functions.

```python
@olive_tool
async def fetch_api_data(url: str) -> dict:
    """Async tools work perfectly."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### 🔗 **Multi-Platform**
Works with LangChain, ElevenLabs, or any HTTP client.

```python
# LangChain
tools = await client.as_langchain_tools()

# ElevenLabs
tools = await client.as_elevenlabs_tools()

# Raw HTTP
POST /olive/tools/call
{"tool_name": "my_tool", "arguments": {...}}
```

### 🔐 **Context Injection**
Inject runtime context (user IDs, session data) without exposing to LLM.

```python
from typing import Annotated
from olive import olive_tool, Inject

@olive_tool
def update_user(
    name: str,
    user_id: Annotated[str, Inject("user_id")]  # Hidden from LLM
) -> dict:
    """Update user. Agent only sees 'name' param."""
    # user_id injected from context at runtime
    return update_database(user_id, name)
```

---

## Production: Optional Temporal Integration

**By default, Olive uses direct execution** - your functions run immediately when called. For production workloads requiring reliability, you can enable [Temporal](https://temporal.io).

### Why Temporal?

Without Temporal (default):
- ✅ Simple, fast
- ❌ No retry on failure
- ❌ Lost work if server crashes

With Temporal (optional):
- ✅ Automatic retries
- ✅ Durable execution (survives crashes)
- ✅ Distributed workers
- ✅ Full observability

### Enable Temporal

**1. Install with Temporal support:**
```bash
pip install olive[temporal]
```

**2. Create `.olive.yaml`:**
```yaml
temporal:
  enabled: true
  address: localhost:7233
  namespace: default
```

**3. Start Temporal server:**
```bash
temporal server start-dev
```

**4. Run your server:**
```bash
uvicorn server:app
# Now uses Temporal for reliability!
```

### Temporal Cloud (Production)

```yaml
temporal:
  enabled: true
  cloud_namespace: prod.your-namespace
  cloud_api_key: ${TEMPORAL_CLOUD_API_KEY}
```

---

## Advanced Usage

### Custom Timeout & Retries

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
    """Process large dataset with custom timeouts."""
    return await process_large_dataset(data)
```

### Fire-and-Forget Mode

```python
@olive_tool(fire_and_forget=True)
async def send_notification(email: str, message: str) -> str:
    """Send email without waiting for result."""
    await email_service.send(email, message)
    return "Queued"

# Returns workflow ID immediately, doesn't wait for completion
```

### Client-Side Features

```python
from olive_client import OliveClient

async with OliveClient("http://your-server.com") as client:
    # List all tools
    tools = await client.get_tools()
    
    # Call tool directly
    result = await client.call_tool("tool_name", {"arg": "value"})
    
    # Filter specific tools
    langchain_tools = await client.as_langchain_tools(
        tool_names=["tool1", "tool2"]
    )
    
    # Context injection for multi-tenant
    tools = await client.as_langchain_tools_injecting(
        context_provider=lambda cfg: cfg.configurable
    )
```

---

## API Reference

### Server Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/olive/tools` | List all registered tools |
| `POST` | `/olive/tools/call` | Execute a tool |
| `GET` | `/olive/tools/elevenlabs` | Get tools in ElevenLabs format |
| `GET` | `/docs` | Interactive API documentation |

### Decorator

```python
@olive_tool(
    func: Callable = None,
    description: str = None,
    timeout_seconds: int = 300,
    retry_policy: dict = None,
    fire_and_forget: bool = False
)
```

**Parameters:**
- `description`: Override docstring (optional)
- `timeout_seconds`: Temporal timeout (default: 300)
- `retry_policy`: Temporal retry config (optional)
- `fire_and_forget`: Return immediately (default: False)

### Client

```python
class OliveClient:
    def __init__(self, base_url: str, timeout: float = 30.0)
    
    async def get_tools(self) -> list[dict]
    async def call_tool(self, tool_name: str, arguments: dict) -> Any
    async def as_langchain_tools(self, tool_names: list[str] = None) -> list[StructuredTool]
    async def as_elevenlabs_tools(self, tool_names: list[str] = None) -> list[dict]
```

---

## Examples

### Example 1: Database Tools

```python
from olive import olive_tool
import asyncpg

@olive_tool
async def search_users(query: str, limit: int = 10) -> list[dict]:
    """Search users in database."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM users WHERE name ILIKE $1 LIMIT $2",
            f"%{query}%", limit
        )
        return [dict(row) for row in rows]
```

### Example 2: External API Integration

```python
@olive_tool
async def get_weather(city: str, units: str = "metric") -> dict:
    """Get weather from OpenWeatherMap."""
    api_key = os.getenv("WEATHER_API_KEY")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": units}
        )
        return response.json()
```

### Example 3: Multi-Agent Setup

```python
# Tool server (one instance)
@olive_tool
def book_appointment(patient_id: str, time: str) -> dict:
    return {"appointment_id": "123", "confirmed": True}

# Voice agent (ElevenLabs)
tools = await client.as_elevenlabs_tools()
# Uses tools during phone calls

# Chat agent (LangChain)
tools = await client.as_langchain_tools()
# Uses same tools in web chat

# Mobile app
POST /olive/tools/call
# Uses same tools via REST API
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

# Specific test file
pytest tests/test_decorator.py -v

# Skip Temporal tests (if not installed)
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

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Client Side                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │ LangChain  │  │ ElevenLabs │  │   HTTP     │   │
│  │   Agent    │  │ Voice Agent│  │   Client   │   │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘   │
│        │                │                │          │
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

---

## Comparison with Other Tools

| Feature | Olive | LangChain Tools | FastAPI Only |
|---------|-------|----------------|--------------|
| **Remote execution** | ✅ Built-in | ❌ Local only | ⚠️ Manual setup |
| **LangChain integration** | ✅ One line | ✅ Native | ❌ Manual |
| **Auto schema generation** | ✅ From types | ✅ From types | ⚠️ Manual |
| **Multi-agent sharing** | ✅ Yes | ❌ No | ✅ Yes |
| **Context injection** | ✅ Built-in | ❌ No | ⚠️ Manual |
| **Reliability (retries)** | ✅ Optional | ❌ No | ⚠️ Manual |
| **Setup complexity** | ⭐ One decorator | ⭐ One decorator | ⭐⭐⭐ High |

---

## FAQ

### Q: Do I need Temporal?

**A:** No. Olive works perfectly without Temporal. Enable it only for production workloads needing retry logic and durability.

### Q: Can I use this with OpenAI function calling?

**A:** Yes! The tool schemas are compatible with OpenAI's function calling format.

### Q: How is this different from just using FastAPI?

**A:** Olive adds automatic schema generation, LangChain integration, and optional reliability features. You could build this yourself, but Olive does it in one decorator.

### Q: Can I mix local and remote tools?

**A:** Absolutely! Use LangChain `@tool` for local tools and Olive `@olive_tool` for remote ones.

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

### Q: What about authentication?

**A:** Olive focuses on tool execution. Add authentication at the FastAPI level:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def verify_token(request, call_next):
    # Your auth logic here
    return await call_next(request)
```

---

## Roadmap

- [ ] Built-in authentication middleware
- [ ] Rate limiting per tool
- [ ] Tool versioning
- [ ] OpenTelemetry integration
- [ ] Metrics dashboard
- [ ] Tool marketplace

---

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Credits

Built with ❤️ by [YaVendio](https://github.com/YaVendio)

**Special thanks to:**
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [LangChain](https://langchain.com/) for pioneering agent tooling
- [Temporal](https://temporal.io/) for reliable distributed execution
- [Pydantic](https://pydantic.dev/) for data validation

---

## Links

- **Documentation**: [README.md](README.md) (Español)
- **GitHub**: [github.com/YaVendio/olive](https://github.com/YaVendio/olive)
- **Issues**: [github.com/YaVendio/olive/issues](https://github.com/YaVendio/olive/issues)
- **Discussions**: [github.com/YaVendio/olive/discussions](https://github.com/YaVendio/olive/discussions)

---

<p align="center">
  <sub>If Olive helps your project, consider giving it a ⭐ on GitHub!</sub>
</p>
