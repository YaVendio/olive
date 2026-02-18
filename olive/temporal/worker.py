"""Temporal worker for Olive."""

import asyncio
import concurrent.futures
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from temporalio.client import Client
from temporalio.service import TLSConfig
from temporalio.worker import Worker

from olive.config import OliveConfig
from olive.registry import _registry
from olive.temporal.activities import create_activity_from_tool
from olive.temporal.workflows import OliveToolInput, OliveToolWorkflow


class TemporalWorker:
    """Manages the Temporal worker for Olive tools."""

    def __init__(self, config: OliveConfig):
        self.config = config
        self._client: Client | None = None
        self._worker: Worker | None = None
        self._worker_thread: threading.Thread | None = None
        self._async_stop_event: asyncio.Event | None = None
        self._stop_requested = threading.Event()

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

        # Temporal Cloud always requires TLS, even without mTLS client certs
        if temporal_config.is_cloud and "tls" not in connect_kwargs:
            connect_kwargs["tls"] = True

        # Temporal Cloud API key auth
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

            # Block efficiently until shutdown is requested.
            # asyncio.Event.set() is thread-safe in Python 3.12+.
            self._async_stop_event = asyncio.Event()
            async with self._worker:
                await self._async_stop_event.wait()

    def _worker_thread_target(self):
        """Thread target for running the worker."""
        asyncio.run(self._run_worker())

    async def check_connection(self) -> bool:
        """Check if Temporal server is accessible.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            # Try to get client (will fail if Temporal not available)
            await self._get_client()
            return True
        except Exception:
            return False

    def start_background(self):
        """Start the worker in a background thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_requested.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_thread_target, daemon=True, name="olive-temporal-worker"
            )
            self._worker_thread.start()

    def stop(self):
        """Stop the worker."""
        self._stop_requested.set()
        if self._async_stop_event is not None:
            self._async_stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout_seconds: int = 300,
        retry_policy: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a tool via Temporal workflow."""
        client = await self._get_client()

        input_data = OliveToolInput(
            tool_name=tool_name,
            arguments=arguments,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy or {},
        )

        result = await client.execute_workflow(
            OliveToolWorkflow.run,
            args=[input_data],
            id=f"olive-tool-{tool_name}-{uuid4()}",
            task_queue=self.config.temporal.task_queue,
        )

        return result

    async def start_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout_seconds: int = 300,
        retry_policy: dict[str, Any] | None = None,
    ) -> str:
        """Start tool workflow without waiting (fire-and-forget).

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            timeout_seconds: Workflow timeout
            retry_policy: Retry configuration

        Returns:
            Workflow ID (not the result)
        """
        client = await self._get_client()

        input_data = OliveToolInput(
            tool_name=tool_name,
            arguments=arguments,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy or {},
        )

        workflow_id = f"olive-tool-{tool_name}-{uuid4()}"

        handle = await client.start_workflow(
            OliveToolWorkflow.run,
            args=[input_data],
            id=workflow_id,
            task_queue=self.config.temporal.task_queue,
        )

        return handle.id  # Return workflow ID immediately, don't await result
