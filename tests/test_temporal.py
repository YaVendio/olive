"""Tests for Olive Temporal integration."""

import asyncio
import threading
from unittest import mock

import pytest

# Check if Temporal is available
try:
    from temporalio import activity, workflow
    from temporalio.client import Client
    from temporalio.worker import Worker

    from olive.temporal.activities import create_activity_from_tool
    from olive.temporal.worker import TemporalWorker
    from olive.temporal.workflows import OliveToolWorkflow

    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    # Create dummy objects for type checking
    activity = None  # type: ignore
    workflow = None  # type: ignore
    Client = None  # type: ignore
    Worker = None  # type: ignore
    create_activity_from_tool = None  # type: ignore
    TemporalWorker = None  # type: ignore
    OliveToolWorkflow = None  # type: ignore

from olive.config import OliveConfig, TemporalConfig
from olive.registry import _registry
from olive.schemas import ToolInfo

# Skip all tests in this module if Temporal not installed
pytestmark = pytest.mark.skipif(not TEMPORAL_AVAILABLE, reason="Temporal not installed (pip install olive[temporal])")


def test_create_activity_from_tool_sync():
    """Test creating a Temporal activity from a sync tool."""

    # Create a mock tool
    def my_tool(name: str) -> str:
        return f"Hello, {name}!"

    tool_info = ToolInfo(
        name="my_tool",
        description="A test tool",
        input_schema={"type": "object"},
        output_schema={"type": "string"},
        func=my_tool,
    )

    # Create activity
    activity_func = create_activity_from_tool(tool_info)

    # Test the activity
    result = activity_func({"name": "World"})
    assert result == "Hello, World!"

    # Check metadata
    assert activity_func.__name__ == "my_tool"
    assert activity_func.__doc__ == "A test tool"


@pytest.mark.asyncio
async def test_create_activity_from_tool_async():
    """Test creating a Temporal activity from an async tool."""

    # Create a mock async tool
    async def my_async_tool(name: str) -> str:
        await asyncio.sleep(0.01)
        return f"Hello async, {name}!"

    tool_info = ToolInfo(
        name="my_async_tool",
        description="An async test tool",
        input_schema={"type": "object"},
        output_schema={"type": "string"},
        func=my_async_tool,
    )

    # Create activity
    activity_func = create_activity_from_tool(tool_info)

    # Test the activity
    result = await activity_func({"name": "World"})
    assert result == "Hello async, World!"

    # Check metadata
    assert activity_func.__name__ == "my_async_tool"
    assert activity_func.__doc__ == "An async test tool"


@pytest.mark.asyncio
async def test_olive_tool_workflow():
    """Test the OliveToolWorkflow."""
    # Mock the activity context
    with mock.patch("olive.temporal.workflows.workflow.execute_activity") as mock_execute:
        mock_execute.return_value = {"result": "success"}

        # Create workflow instance
        workflow_instance = OliveToolWorkflow()

        # Run the workflow
        result = await workflow_instance.run("test_tool", {"arg": "value"})

        # Verify
        assert result == {"result": "success"}
        mock_execute.assert_called_once()

        # Check the call arguments
        call_args = mock_execute.call_args
        assert call_args[0][0] == "test_tool"  # activity name
        assert call_args[0][1] == {"arg": "value"}  # arguments


def test_temporal_worker_init():
    """Test TemporalWorker initialization."""
    config = OliveConfig()
    worker = TemporalWorker(config)

    assert worker.config == config
    assert worker._client is None
    assert worker._worker is None
    assert worker._worker_thread is None
    assert isinstance(worker._stop_event, threading.Event)


@pytest.mark.asyncio
async def test_temporal_worker_get_client():
    """Test TemporalWorker get_client method."""
    config = OliveConfig()
    worker = TemporalWorker(config)

    with mock.patch("olive.temporal.worker.Client.connect") as mock_connect:
        mock_client = mock.Mock(spec=Client)
        mock_connect.return_value = mock_client

        client = await worker._get_client()

        assert worker._client == mock_client
        assert client == mock_client
        mock_connect.assert_called_once_with(target_host=config.temporal.address, namespace=config.temporal.namespace)


@pytest.mark.asyncio
async def test_temporal_worker_execute_tool():
    """Test TemporalWorker execute_tool method."""
    config = OliveConfig()
    worker = TemporalWorker(config)

    # Mock the client
    mock_client = mock.Mock(spec=Client)
    worker._client = mock_client

    # Mock the workflow execution
    mock_client.execute_workflow = mock.AsyncMock(return_value={"result": "success"})

    # Execute tool
    result = await worker.execute_tool("test_tool", {"arg": "value"})

    assert result == {"result": "success"}
    mock_client.execute_workflow.assert_called_once()

    # Check workflow arguments
    call_args = mock_client.execute_workflow.call_args
    assert call_args[0][0] == OliveToolWorkflow.run
    assert call_args[1]["args"] == ["test_tool", {"arg": "value"}]
    assert call_args[1]["task_queue"] == config.temporal.task_queue


@pytest.mark.asyncio
async def test_temporal_worker_execute_tool_no_client():
    """Test execute_tool when client is not connected."""
    config = OliveConfig()
    worker = TemporalWorker(config)

    with mock.patch.object(worker, "_get_client") as mock_get_client:
        mock_client = mock.Mock(spec=Client)
        mock_client.execute_workflow = mock.AsyncMock(return_value={"result": "success"})
        mock_get_client.return_value = mock_client

        # Execute tool
        result = await worker.execute_tool("test_tool", {"arg": "value"})

        assert result == {"result": "success"}
        mock_get_client.assert_called_once()


def test_temporal_worker_start_background():
    """Test starting worker in background thread."""
    config = OliveConfig()
    worker = TemporalWorker(config)

    with mock.patch("threading.Thread") as mock_thread_class:
        mock_thread = mock.Mock()
        mock_thread_class.return_value = mock_thread

        worker.start_background()

        # Verify thread was created and started
        mock_thread_class.assert_called_once_with(
            target=worker._worker_thread_target, daemon=True, name="olive-temporal-worker"
        )
        mock_thread.start.assert_called_once()
        assert worker._worker_thread == mock_thread


def test_temporal_worker_stop():
    """Test stopping the worker."""
    config = OliveConfig()
    worker = TemporalWorker(config)

    # Mock the thread
    mock_thread = mock.Mock()
    mock_thread.is_alive.return_value = True
    worker._worker_thread = mock_thread

    # Stop the worker
    worker.stop()

    # Verify stop event was set
    assert worker._stop_event.is_set()

    # Verify thread was joined
    mock_thread.join.assert_called_once_with(timeout=5)


def test_temporal_worker_stop_no_thread():
    """Test stopping when no thread is running."""
    config = OliveConfig()
    worker = TemporalWorker(config)

    # Should not raise any errors
    worker.stop()
    assert worker._stop_event.is_set()


@pytest.mark.asyncio
async def test_temporal_worker_run_worker():
    """Test the _run_worker method."""
    config = OliveConfig()
    worker = TemporalWorker(config)

    # Add a test tool
    def test_tool(x: int) -> int:
        return x * 2

    tool_info = ToolInfo(
        name="test_tool",
        description="Test tool",
        input_schema={},
        output_schema={},
        func=test_tool,
        timeout_seconds=300,
        retry_policy=None,
    )
    _registry.register(tool_info)

    # Mock the client
    with mock.patch.object(worker, "_get_client") as mock_get_client:
        mock_client = mock.Mock(spec=Client)
        mock_get_client.return_value = mock_client

        # Mock Worker and ThreadPoolExecutor
        mock_temporal_worker = mock.Mock(spec=Worker)

        # Create a mock async context manager
        mock_temporal_worker.__aenter__ = mock.AsyncMock(return_value=mock_temporal_worker)
        mock_temporal_worker.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("olive.temporal.worker.Worker") as mock_worker_class:
            with mock.patch("concurrent.futures.ThreadPoolExecutor"):
                mock_worker_class.return_value = mock_temporal_worker

                # Set stop event after a short delay
                async def stop_after_delay():
                    await asyncio.sleep(0.1)
                    worker._stop_event.set()

                # Run worker and stop task concurrently
                await asyncio.gather(worker._run_worker(), stop_after_delay())

                # Verify worker was created with activities
                mock_worker_class.assert_called_once()
                call_args = mock_worker_class.call_args
                assert call_args[1]["task_queue"] == config.temporal.task_queue
                assert call_args[1]["workflows"] == [OliveToolWorkflow]
                assert len(call_args[1]["activities"]) > 0

    # Clean up
    _registry._tools.pop("test_tool", None)
