"""Temporal worker for Olive."""

import asyncio
import concurrent.futures
import threading
from typing import Any

from temporalio.client import Client
from temporalio.worker import Worker

from olive.config import OliveConfig
from olive.registry import _registry
from olive.temporal.activities import create_activity_from_tool
from olive.temporal.workflows import OliveToolWorkflow


class TemporalWorker:
    """Manages the Temporal worker for Olive tools."""

    def __init__(self, config: OliveConfig):
        self.config = config
        self._client: Client | None = None
        self._worker: Worker | None = None
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    async def _get_client(self) -> Client:
        """Get or create Temporal client."""
        if self._client is None:
            if self.config.temporal.is_cloud:
                # TODO: Add cloud support
                raise NotImplementedError("Temporal Cloud support coming soon!")
            else:
                self._client = await Client.connect(
                    self.config.temporal.address,
                    namespace=self.config.temporal.namespace,
                )
        return self._client

    async def _run_worker(self):
        """Run the worker (called in thread)."""
        client = await self._get_client()

        # Get all registered activities
        activities = []
        for tool_info in _registry.list_all():
            activity = create_activity_from_tool(tool_info)
            activities.append(activity)

        # Create worker with thread pool for activities
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
            self._worker = Worker(
                client,
                task_queue=self.config.temporal.task_queue,
                workflows=[OliveToolWorkflow],
                activities=activities,
                activity_executor=activity_executor,
            )

            # Run worker until stop event is set
            async with self._worker:
                while not self._stop_event.is_set():
                    await asyncio.sleep(0.1)

    def _worker_thread_target(self):
        """Thread target for running the worker."""
        asyncio.run(self._run_worker())

    def start_background(self):
        """Start the worker in a background thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_thread_target, daemon=True, name="olive-temporal-worker"
            )
            self._worker_thread.start()

    def stop(self):
        """Stop the worker."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool via Temporal workflow."""
        client = await self._get_client()

        # Execute workflow
        result = await client.execute_workflow(
            OliveToolWorkflow.run,
            args=[tool_name, arguments],
            id=f"olive-tool-{tool_name}-{asyncio.get_event_loop().time()}",
            task_queue=self.config.temporal.task_queue,
        )

        return result
