# Olive 🫒

[![Tests](https://github.com/YaVendio/olive/actions/workflows/tests.yml/badge.svg)](https://github.com/YaVendio/olive/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FYaVendio%2Folive%2Fmain%2Fpyproject.toml)](https://github.com/YaVendio/olive/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Transform Python functions into remote tools for AI agents.**

```python
from olive import olive_tool, create_app

@olive_tool
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    return {"temp": 72, "city": city}

app = create_app()
# Your function is now callable via REST API
```

## Why Olive?

LangChain's `@tool` is local-only—agent and tools run together. Olive makes tools **remote**:

- ✅ One tool server, many agents
- ✅ Centralized credentials (DB, APIs)
- ✅ Works with LangChain, ElevenLabs, or any HTTP client
- ✅ Scale agents and tools independently

## Installation

```bash
pip install git+https://github.com/YaVendio/olive.git
```

## Quick Start

**1. Create your tools:**

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
    return {"id": user_id, "name": "John Doe"}

app = create_app()
```

**2. Run the server:**

```bash
uvicorn server:app
```

**3. Use from LangChain:**

```python
from olive_client import OliveClient
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

async with OliveClient("http://localhost:8000") as client:
    tools = await client.as_langchain_tools()
    
    model = ChatAnthropic(model="claude-3-sonnet")
    agent = create_react_agent(model, tools=tools)
    
    response = await agent.ainvoke({
        "messages": [("user", "Calculate tax on $1000")]
    })
```

## Features

### Type-Safe Schemas

Automatic schema generation from Python type hints:

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

### Multi-Platform Support

```python
# LangChain agents
tools = await client.as_langchain_tools()

# ElevenLabs voice agents
tools = await client.as_elevenlabs_tools()

# Direct HTTP calls
POST /olive/tools/call
{"tool_name": "my_tool", "arguments": {...}}
```

### Context Injection

Inject runtime context (user IDs, sessions) without exposing to LLM:

```python
from typing import Annotated
from olive import olive_tool, Inject

@olive_tool
def update_user(
    name: str,
    user_id: Annotated[str, Inject("user_id")]  # Hidden from LLM
) -> dict:
    """Agent only sees 'name' param. user_id injected at runtime."""
    return update_database(user_id, name)
```

### Async Support

```python
@olive_tool
async def fetch_api_data(url: str) -> dict:
    """Async tools work seamlessly."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

## Examples

### Database Tools

```python
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

### External API Integration

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

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/olive/tools` | List all tools |
| `POST` | `/olive/tools/call` | Execute a tool |
| `GET` | `/olive/tools/elevenlabs` | ElevenLabs format |
| `GET` | `/docs` | Interactive docs |

## Optional: Temporal for Production

For production workloads needing automatic retries and durable execution, Olive supports [Temporal](https://temporal.io):

```bash
pip install "olive[temporal]"
```

```yaml
# .olive.yaml
temporal:
  enabled: true
  address: localhost:7233
```

See [EXTENDED.md](EXTENDED.md#temporal-integration) for full Temporal documentation.

## More Documentation

- **[EXTENDED.md](EXTENDED.md)** — Advanced usage, Temporal, architecture, configuration, API reference
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Development setup and contribution guidelines
- **[INSTALL_WITH_UV.md](INSTALL_WITH_UV.md)** — Detailed installation options

## License

MIT License - see [LICENSE](LICENSE)

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/YaVendio">YaVendio</a>
</p>
