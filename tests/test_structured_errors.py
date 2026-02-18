"""Tests for structured error types in ToolCallResponse."""

import pytest
from httpx import ASGITransport, AsyncClient

from olive import create_app, olive_tool
from olive.registry import _registry


@pytest.fixture(autouse=True)
def _clear_registry():
    _registry.clear()
    yield
    _registry.clear()


@pytest.fixture
def app():
    @olive_tool
    def good_tool(x: int) -> int:
        """A working tool."""
        return x * 2

    @olive_tool
    def bad_tool(x: int) -> int:
        """A tool that raises."""
        raise ValueError("something broke")

    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_error_type_tool_not_found(client):
    resp = await client.post("/olive/tools/call", json={"tool_name": "nonexistent", "arguments": {}})
    data = resp.json()
    assert data["success"] is False
    assert data["error_type"] == "tool_not_found"
    assert "nonexistent" in data["error"]


async def test_error_type_execution_error(client):
    resp = await client.post("/olive/tools/call", json={"tool_name": "bad_tool", "arguments": {"x": 1}})
    data = resp.json()
    assert data["success"] is False
    assert data["error_type"] == "execution_error"
    assert "something broke" in data["error"]


async def test_error_type_missing_context():
    from typing import Annotated

    from olive import Inject

    _registry.clear()

    @olive_tool
    def ctx_tool(name: str, user_id: Annotated[str, Inject(key="user_id")]) -> str:
        """Needs context."""
        return f"{name}-{user_id}"

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Call without context
        resp = await client.post(
            "/olive/tools/call",
            json={"tool_name": "ctx_tool", "arguments": {"name": "test"}},
        )
        data = resp.json()
        assert data["success"] is False
        assert data["error_type"] == "missing_context"
        assert "user_id" in data["error"]


async def test_successful_call_has_no_error_type(client):
    resp = await client.post("/olive/tools/call", json={"tool_name": "good_tool", "arguments": {"x": 5}})
    data = resp.json()
    assert data["success"] is True
    assert data["result"] == 10
    assert data["error_type"] is None
    assert data["error"] is None
