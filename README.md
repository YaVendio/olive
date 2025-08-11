# Olive 🫒

A minimal framework for exposing FastAPI endpoints as LangChain tools.

## Overview

Olive lets you easily convert your FastAPI endpoints into tools that can be used by LangChain agents. Just decorate your functions with `@olive_tool` and they become available as remote tools.

## Features

- 🎯 **Simple**: Just one decorator to make your functions available as tools
- 🔧 **Type-safe**: Automatic schema extraction from Python type hints
- 🚀 **Async-first**: Full support for async functions
- 🔗 **LangChain-ready**: Seamless conversion to LangChain tools
- 📦 **Minimal dependencies**: Only FastAPI, Pydantic, httpx, and langchain-core

## Installation

### From GitHub Package Registry (Private)

This package is hosted on GitHub's private package registry. You'll need a GitHub personal access token with `read:packages` permission.

#### Using uv (Recommended)

```bash
# Install directly from Git
uv pip install git+ssh://git@github.com/YaVendio/olive.git

# Or add to your project
uv add git+ssh://git@github.com/YaVendio/olive.git
```

#### Using pip

```bash
# Using pip with authentication
pip install olive --index-url https://USERNAME:TOKEN@pypi.pkg.github.com/YaVendio
```

Replace `USERNAME` with your GitHub username and `TOKEN` with your personal access token.

For detailed installation instructions:
- **uv**: See [INSTALL_WITH_UV.md](INSTALL_WITH_UV.md) (recommended)
- **pip**: See [PACKAGE_INSTALLATION.md](PACKAGE_INSTALLATION.md)

### From Source

```bash
git clone git@github.com:YaVendio/olive.git
cd olive
pip install -e .
```

## Quick Start

### Server Side

```python
from fastapi import FastAPI
from olive import olive_tool, setup_olive

app = FastAPI()
setup_olive(app)  # Adds /olive endpoints

@olive_tool
def translate(text: str, target_language: str = "es") -> dict:
    """Translate text to another language."""
    # Your implementation here
    return {"translated": f"{text} in {target_language}"}

@olive_tool(description="Analyze sentiment")
async def analyze_sentiment(text: str) -> dict:
    """Analyze the sentiment of text."""
    # Your async implementation
    return {"sentiment": "positive", "score": 0.8}
```

### Client Side

```python
from olive_client import OliveClient

# Connect to any Olive-enabled server
async with OliveClient("http://localhost:8000") as client:
    # List available tools
    tools = await client.get_tools()

    # Call a tool directly
    result = await client.call_tool("translate", {
        "text": "Hello world",
        "target_language": "fr"
    })

    # Convert to LangChain tools
    lc_tools = await client.as_langchain_tools()
```

### With LangChain

```python
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from olive_client import OliveClient

# Get tools from Olive server
async with OliveClient("http://localhost:8000") as client:
    tools = await client.as_langchain_tools()

# Create agent with remote tools
model = ChatAnthropic(model="claude-3-sonnet")
agent = create_react_agent(model, tools=tools)

# Use naturally
response = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Translate 'Hello' to Spanish"}]
})
```

## How It Works

1. **Decorate your functions** with `@olive_tool`
2. **Run your FastAPI app** as usual
3. **Connect with OliveClient** from anywhere
4. **Use as LangChain tools** in your agents

## API Endpoints

Olive adds these endpoints to your FastAPI app:

- `GET /olive/tools` - List all available tools
- `POST /olive/tools/call` - Execute a tool

## Example

See [example.py](example.py) for a complete working example:

```bash
# Terminal 1: Start the server
python example.py

# Terminal 2: Run the client demo
python example.py client
```

## Testing

Run the test suite:

```bash
pytest tests/
```

## License

MIT
