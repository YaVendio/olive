"""Tests for request-level timeout enforcement in direct execution mode."""

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from olive import create_app, olive_tool
from olive.registry import _registry


@pytest.fixture(autouse=True)
def _clear_registry():
    _registry.clear()
    yield
    _registry.clear()


async def test_async_tool_timeout():
    @olive_tool(timeout_seconds=1)
    async def slow_async(x: int) -> int:
        """Slow async tool."""
        await asyncio.sleep(10)
        return x

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = time.monotonic()
        resp = await client.post("/olive/tools/call", json={"tool_name": "slow_async", "arguments": {"x": 1}})
        elapsed = time.monotonic() - start

        data = resp.json()
        assert data["success"] is False
        assert data["error_type"] == "timeout"
        assert "timed out" in data["error"]
        assert elapsed < 5  # Should timeout well before 5s


async def test_sync_tool_timeout():
    @olive_tool(timeout_seconds=1)
    def slow_sync(x: int) -> int:
        """Slow sync tool."""
        time.sleep(10)
        return x

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = time.monotonic()
        resp = await client.post("/olive/tools/call", json={"tool_name": "slow_sync", "arguments": {"x": 1}})
        elapsed = time.monotonic() - start

        data = resp.json()
        assert data["success"] is False
        assert data["error_type"] == "timeout"
        assert elapsed < 5


async def test_tool_completes_within_timeout():
    @olive_tool(timeout_seconds=10)
    async def fast_tool(x: int) -> int:
        """Fast tool."""
        return x * 2

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/olive/tools/call", json={"tool_name": "fast_tool", "arguments": {"x": 5}})
        data = resp.json()
        assert data["success"] is True
        assert data["result"] == 10
        assert data["error_type"] is None


async def test_default_timeout_does_not_immediately_timeout():
    """Tools with default timeout (300s) should not timeout on fast operations."""

    @olive_tool
    async def quick_tool(x: int) -> int:
        """Quick tool with default timeout."""
        return x + 1

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/olive/tools/call", json={"tool_name": "quick_tool", "arguments": {"x": 99}})
        data = resp.json()
        assert data["success"] is True
        assert data["result"] == 100
