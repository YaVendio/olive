"""Temporal worker for Olive."""

import asyncio
import concurrent.futures
import threading
from pathlib import Path
from typing import Any

from temporalio.client import Client
from temporalio.service import TLSConfig
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
        if self._client is not None:
            return self._client

        temporal_config = self.config.temporal

        tls_config: TLSConfig | None = None
        if temporal_config.client_cert_path and temporal_config.client_key_path:
            cert_path = Path(temporal_config.client_cert_path)
            key_path = Path(temporal_config.client_key_path)

            if not cert_path.exists():
                raise FileNotFoundError(f"Temporal client certificate not found: {cert_path}")
            if not key_path.exists():
                raise FileNotFoundError(f"Temporal client key not found: {key_path}")

            server_root_ca = None
            if temporal_config.server_root_ca_path:
                ca_path = Path(temporal_config.server_root_ca_path)
                if not ca_path.exists():
                    raise FileNotFoundError(f"Temporal server root CA not found: {ca_path}")
                server_root_ca = ca_path.read_bytes()

            tls_config = TLSConfig(
                client_cert=cert_path.read_bytes(),
                client_private_key=key_path.read_bytes(),
                server_root_ca_cert=server_root_ca,
                domain=temporal_config.server_name,
            )

        address = temporal_config.namespace_endpoint or temporal_config.address

        connect_kwargs: dict[str, Any] = {
            "target_host": address,
            "namespace": temporal_config.namespace,
        }

        if tls_config is not None:
            connect_kwargs["tls"] = tls_config

        # Temporal Cloud requires API key auth; use data plane address with tls.
        if temporal_config.is_cloud and temporal_config.cloud_api_key:
            connect_kwargs.setdefault("rpc_metadata", {})
            connect_kwargs["rpc_metadata"]["authorization"] = f"Bearer {temporal_config.cloud_api_key}"
            if temporal_config.cloud_namespace:
                connect_kwargs["rpc_metadata"].setdefault("temporal-namespace", temporal_config.cloud_namespace)
        elif temporal_config.namespace_endpoint:
            connect_kwargs.setdefault("rpc_metadata", {})
            connect_kwargs["rpc_metadata"].setdefault("temporal-namespace", temporal_config.namespace)

        self._client = await Client.connect(**connect_kwargs)
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
