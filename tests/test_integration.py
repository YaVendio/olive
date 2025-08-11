"""Integration tests for Olive server and client."""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from olive import olive_tool, setup_olive
from olive.registry import _registry
from olive_client import OliveClient


@pytest.fixture
def app():
    """Create a test FastAPI app with Olive."""
    # Clear registry before each test
    _registry.clear()

    # Create app and setup Olive
    app = FastAPI()
    setup_olive(app)

    # Register some test tools
    @olive_tool
    def add(x: int, y: int) -> int:
        """Add two numbers."""
        return x + y

    @olive_tool(description="Multiply numbers")
    def multiply(x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    @olive_tool
    async def async_greet(name: str, greeting: str = "Hello") -> str:
        """Greet someone asynchronously."""
        await asyncio.sleep(0.01)  # Simulate async work
        return f"{greeting}, {name}!"

    @olive_tool
    def process_list(items: list[str]) -> dict:
        """Process a list of items."""
        return {"count": len(items), "items": items, "joined": ", ".join(items)}

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_list_tools_endpoint(client):
    """Test the /olive/tools endpoint."""
    response = client.get("/olive/tools")
    assert response.status_code == 200

    tools = response.json()
    assert len(tools) == 4

    # Check that all tools are present
    tool_names = [t["name"] for t in tools]
    assert "add" in tool_names
    assert "multiply" in tool_names
    assert "async_greet" in tool_names
    assert "process_list" in tool_names

    # Check tool details
    add_tool = next(t for t in tools if t["name"] == "add")
    assert add_tool["description"] == "Add two numbers."
    assert add_tool["input_schema"]["required"] == ["x", "y"]


def test_call_tool_endpoint(client):
    """Test the /olive/tools/call endpoint."""
    # Test successful call
    response = client.post("/olive/tools/call", json={"tool_name": "add", "arguments": {"x": 5, "y": 3}})
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["result"] == 8
    assert data["error"] is None

    # Test with missing arguments
    response = client.post(
        "/olive/tools/call",
        json={
            "tool_name": "add",
            "arguments": {"x": 5},  # Missing y
        },
    )
    data = response.json()
    assert data["success"] is False
    assert "error" in data

    # Test non-existent tool
    response = client.post("/olive/tools/call", json={"tool_name": "non_existent", "arguments": {}})
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"]


def test_async_tool_call(client):
    """Test calling an async tool."""
    response = client.post("/olive/tools/call", json={"tool_name": "async_greet", "arguments": {"name": "Alice"}})
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["result"] == "Hello, Alice!"


def test_tool_with_complex_types(client):
    """Test tool with complex types like List."""
    response = client.post(
        "/olive/tools/call", json={"tool_name": "process_list", "arguments": {"items": ["apple", "banana", "cherry"]}}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["result"]["count"] == 3
    assert data["result"]["joined"] == "apple, banana, cherry"


@pytest.mark.asyncio
async def test_olive_client():
    """Test the OliveClient."""
    # Create a test app
    _registry.clear()
    app = FastAPI()
    setup_olive(app)

    @olive_tool
    def echo(message: str) -> str:
        """Echo a message."""
        return message

    # Use TestClient as the transport
    from httpx import ASGITransport

    transport = ASGITransport(app=app)

    async with OliveClient("http://test") as client:
        # Override the client's transport
        client._client._transport = transport

        # Test get_tools
        tools = await client.get_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "echo"

        # Test call_tool
        result = await client.call_tool("echo", {"message": "Hello Olive!"})
        assert result == "Hello Olive!"

        # Test as_langchain_tools
        lc_tools = await client.as_langchain_tools()
        assert len(lc_tools) == 1
        assert lc_tools[0].name == "echo"

        # Test invoking the LangChain tool
        lc_result = await lc_tools[0].ainvoke({"message": "LangChain test"})
        assert lc_result == "LangChain test"


def test_end_to_end_example(client):
    """Test a complete end-to-end example."""
    # List available tools
    response = client.get("/olive/tools")
    tools = response.json()

    # Find the multiply tool
    multiply_tool = next(t for t in tools if t["name"] == "multiply")

    # Check its schema
    assert multiply_tool["input_schema"]["properties"]["x"]["type"] == "integer"
    assert multiply_tool["input_schema"]["properties"]["y"]["type"] == "integer"

    # Call it
    response = client.post("/olive/tools/call", json={"tool_name": "multiply", "arguments": {"x": 7, "y": 6}})

    result = response.json()
    assert result["success"] is True
    assert result["result"] == 42
