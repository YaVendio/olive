"""Tests for context injection type validation."""

from typing import Annotated

import pytest
from httpx import ASGITransport, AsyncClient

from olive import Inject, create_app, olive_tool
from olive.registry import _registry
from olive.schemas import extract_schema_from_function


@pytest.fixture(autouse=True)
def _clear_registry():
    _registry.clear()
    yield
    _registry.clear()


def test_injection_expected_type_stored():
    """expected_type is populated from the type hint during schema extraction."""

    def tool(name: str, user_id: Annotated[str, Inject(key="user_id")]) -> str:
        return f"{name}-{user_id}"

    _, _, injections = extract_schema_from_function(tool)
    assert len(injections) == 1
    assert injections[0].expected_type == "string"


def test_injection_expected_type_integer():
    def tool(count: Annotated[int, Inject(key="count")]) -> int:
        return count

    _, _, injections = extract_schema_from_function(tool)
    assert injections[0].expected_type == "integer"


async def test_injection_type_mismatch():
    @olive_tool
    def greet(name: str, user_id: Annotated[str, Inject(key="user_id")]) -> str:
        """Greet user."""
        return f"Hello {user_id}: {name}"

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/olive/tools/call",
            json={
                "tool_name": "greet",
                "arguments": {"name": "Alice"},
                "context": {"user_id": 42},  # int instead of str
            },
        )
        data = resp.json()
        assert data["success"] is False
        assert data["error_type"] == "validation_error"
        assert "expected type 'string'" in data["error"]
        assert "got 'int'" in data["error"]


async def test_injection_type_match():
    @olive_tool
    def greet(name: str, user_id: Annotated[str, Inject(key="user_id")]) -> str:
        """Greet user."""
        return f"Hello {user_id}: {name}"

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/olive/tools/call",
            json={
                "tool_name": "greet",
                "arguments": {"name": "Alice"},
                "context": {"user_id": "user-123"},
            },
        )
        data = resp.json()
        assert data["success"] is True
        assert data["result"] == "Hello user-123: Alice"


async def test_injection_integer_validation():
    @olive_tool
    def count_items(n: Annotated[int, Inject(key="n")]) -> int:
        """Count."""
        return n * 2

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Correct type
        resp = await client.post(
            "/olive/tools/call",
            json={"tool_name": "count_items", "arguments": {}, "context": {"n": 5}},
        )
        assert resp.json()["success"] is True
        assert resp.json()["result"] == 10

        # Wrong type
        resp = await client.post(
            "/olive/tools/call",
            json={"tool_name": "count_items", "arguments": {}, "context": {"n": "five"}},
        )
        data = resp.json()
        assert data["success"] is False
        assert data["error_type"] == "validation_error"


async def test_injection_no_expected_type_skips_check():
    """When expected_type is None (e.g., Any type), no validation is performed."""

    @olive_tool
    def flex_tool(data: Annotated[dict, Inject(key="data")]) -> dict:
        """Flexible."""
        return data

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # dict expected_type is "object", passing a dict should work
        resp = await client.post(
            "/olive/tools/call",
            json={"tool_name": "flex_tool", "arguments": {}, "context": {"data": {"key": "val"}}},
        )
        assert resp.json()["success"] is True
