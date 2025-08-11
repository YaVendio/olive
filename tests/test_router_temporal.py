"""Tests for router with Temporal integration."""

import asyncio
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from olive import olive_tool
from olive.router import set_temporal_worker
from olive.server import create_app


# Create test tools
@olive_tool
def simple_tool(message: str) -> str:
    """A simple test tool."""
    return f"Echo: {message}"


@pytest.fixture
def app():
    """Create test app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_call_tool_with_temporal():
    """Test calling a tool when Temporal worker is set."""
    # Import here to ensure clean registry
    from olive import olive_tool
    from olive.registry import _registry
    from olive.server import create_app

    # Define tool in this test scope
    @olive_tool
    def temporal_test_tool(message: str) -> str:
        """A test tool for temporal execution."""
        return f"Echo: {message}"

    # Create app and client
    app = create_app()
    client = TestClient(app)

    # Mock temporal worker
    mock_worker = mock.Mock()

    # Create an async mock that the sync TestClient can handle
    async def mock_execute_tool(tool_name, args):
        return {"result": "temporal result"}

    # Mock execute_tool to return coroutine
    mock_worker.execute_tool = mock.Mock(side_effect=mock_execute_tool)

    # Set the temporal worker
    set_temporal_worker(mock_worker)

    try:
        # Call tool
        response = client.post(
            "/olive/tools/call", json={"tool_name": "temporal_test_tool", "arguments": {"message": "test"}}
        )

        assert response.status_code == 200
        data = response.json()

        # Debug print if the test fails
        if not data.get("success"):
            print(f"Response data: {data}")
            print(f"Available tools: {list(_registry._tools.keys())}")

        assert data["success"] is True
        assert data["result"] == {"result": "temporal result"}
        assert data["metadata"]["executed_via"] == "temporal"
        assert data["metadata"]["workflow_type"] == "OliveToolWorkflow"

        # Verify worker was called
        mock_worker.execute_tool.assert_called_once_with("temporal_test_tool", {"message": "test"})
    finally:
        # Clean up
        set_temporal_worker(None)
        # Clean up tool from registry
        _registry._tools.pop("temporal_test_tool", None)


def test_temporal_cloud_not_implemented():
    """Test that Temporal Cloud raises NotImplementedError."""
    from olive.config import OliveConfig, TemporalConfig
    from olive.temporal.worker import TemporalWorker

    # Create config with cloud settings
    config = OliveConfig(temporal=TemporalConfig(cloud_namespace="test-ns", cloud_api_key="test-key"))

    worker = TemporalWorker(config)

    # Try to get client which should raise
    async def test_cloud():
        with pytest.raises(NotImplementedError, match="Temporal Cloud support coming soon"):
            await worker._get_client()

    # Run the async test

    asyncio.run(test_cloud())


def test_worker_thread_target():
    """Test the worker thread target method."""
    from olive.config import OliveConfig
    from olive.temporal.worker import TemporalWorker

    config = OliveConfig()
    worker = TemporalWorker(config)

    # Mock asyncio.run to verify _run_worker is passed
    with mock.patch("asyncio.run") as mock_asyncio_run:
        # Call thread target
        worker._worker_thread_target()

        # Verify asyncio.run was called with _run_worker coroutine
        mock_asyncio_run.assert_called_once()
        # Get the coroutine that was passed
        coro = mock_asyncio_run.call_args[0][0]
        # Verify it's the _run_worker coroutine
        assert coro.__name__ == "_run_worker"
