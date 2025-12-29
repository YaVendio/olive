"""Tests for Olive without Temporal integration."""

import pytest
from fastapi.testclient import TestClient

from olive import create_app, olive_tool
from olive.config import OliveConfig, TemporalConfig
from olive.registry import _registry


def test_server_starts_without_temporal():
    """Test that server starts successfully with temporal.enabled=false."""
    config = OliveConfig(temporal=TemporalConfig(enabled=False))
    app = create_app(config)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Olive Tool Server"


def test_server_starts_with_default_config():
    """Test that server starts with default config (Temporal disabled by default)."""
    config = OliveConfig()
    assert config.temporal.enabled is False

    app = create_app(config)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200


def test_tools_work_without_temporal():
    """Test that tools execute via direct mode without Temporal."""
    # Clear registry
    _registry._tools.clear()

    # Define a test tool
    @olive_tool
    def test_add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    # Create app with Temporal disabled
    config = OliveConfig(temporal=TemporalConfig(enabled=False))
    app = create_app(config)
    client = TestClient(app)

    # List tools
    response = client.get("/olive/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) == 1
    assert tools[0]["name"] == "test_add"

    # Call tool
    response = client.post("/olive/tools/call", json={"tool_name": "test_add", "arguments": {"a": 5, "b": 3}})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result"] == 8
    # When Temporal is disabled, metadata should be None
    assert data["metadata"] is None

    # Clean up
    _registry._tools.clear()


def test_async_tools_work_without_temporal():
    """Test that async tools work in direct execution mode."""
    import asyncio

    _registry._tools.clear()

    @olive_tool
    async def async_greet(name: str) -> str:
        """Async greeting."""
        await asyncio.sleep(0.01)
        return f"Hello {name}!"

    config = OliveConfig(temporal=TemporalConfig(enabled=False))
    app = create_app(config)
    client = TestClient(app)

    response = client.post("/olive/tools/call", json={"tool_name": "async_greet", "arguments": {"name": "World"}})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result"] == "Hello World!"

    _registry._tools.clear()


def test_multiple_tools_without_temporal():
    """Test multiple tools work correctly without Temporal."""
    _registry._tools.clear()

    @olive_tool
    def multiply(x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    @olive_tool
    def uppercase(text: str) -> str:
        """Convert text to uppercase."""
        return text.upper()

    config = OliveConfig(temporal=TemporalConfig(enabled=False))
    app = create_app(config)
    client = TestClient(app)

    # List all tools
    response = client.get("/olive/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) == 2
    tool_names = {t["name"] for t in tools}
    assert tool_names == {"multiply", "uppercase"}

    # Test multiply
    response = client.post("/olive/tools/call", json={"tool_name": "multiply", "arguments": {"x": 7, "y": 6}})
    assert response.status_code == 200
    assert response.json()["result"] == 42

    # Test uppercase
    response = client.post("/olive/tools/call", json={"tool_name": "uppercase", "arguments": {"text": "hello"}})
    assert response.status_code == 200
    assert response.json()["result"] == "HELLO"

    _registry._tools.clear()


def test_tool_not_found_without_temporal():
    """Test that calling non-existent tool returns proper error."""
    config = OliveConfig(temporal=TemporalConfig(enabled=False))
    app = create_app(config)
    client = TestClient(app)

    response = client.post("/olive/tools/call", json={"tool_name": "nonexistent", "arguments": {}})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_tool_error_handling_without_temporal():
    """Test that tool errors are properly caught in direct mode."""
    _registry._tools.clear()

    @olive_tool
    def will_fail(x: int) -> int:
        """A tool that raises an error."""
        raise ValueError("Intentional error for testing")

    config = OliveConfig(temporal=TemporalConfig(enabled=False))
    app = create_app(config)
    client = TestClient(app)

    response = client.post("/olive/tools/call", json={"tool_name": "will_fail", "arguments": {"x": 1}})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Intentional error" in data["error"]

    _registry._tools.clear()


