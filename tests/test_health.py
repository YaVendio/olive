"""Tests for the /olive/health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from olive import create_app, olive_tool
from olive.registry import _registry


@pytest.fixture(autouse=True)
def _clear_registry():
    _registry.clear()
    yield
    _registry.clear()


async def test_health_endpoint_no_tools():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/olive/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["tools_count"] == 0
        assert data["temporal_connected"] is False


async def test_health_endpoint_with_tools():
    @olive_tool
    def tool_a(x: int) -> int:
        """Tool A."""
        return x

    @olive_tool
    def tool_b(y: str) -> str:
        """Tool B."""
        return y

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/olive/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["tools_count"] == 2
        assert data["temporal_connected"] is False


async def test_health_in_root_endpoints():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        data = resp.json()
        assert "health" in data["endpoints"]
        assert data["endpoints"]["health"] == "/olive/health"
