"""Temporal workflows for Olive."""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy


@dataclass
class OliveToolInput:
    """Workflow input carrying tool name, arguments, and execution config."""

    tool_name: str
    arguments: dict[str, Any]
    timeout_seconds: int = 300
    retry_policy: dict[str, Any] = field(default_factory=dict)


@workflow.defn
class OliveToolWorkflow:
    """Workflow for executing Olive tools."""

    @workflow.run
    async def run(self, input: OliveToolInput) -> Any:
        """Execute a tool as a Temporal activity."""
        rp_config = input.retry_policy or {}
        retry_policy = RetryPolicy(
            maximum_attempts=rp_config.get("max_attempts", 3),
            initial_interval=timedelta(seconds=rp_config.get("initial_interval", 1)),
            maximum_interval=timedelta(seconds=rp_config.get("maximum_interval", 10)),
        )

        result = await workflow.execute_activity(
            input.tool_name,
            input.arguments,
            start_to_close_timeout=timedelta(seconds=input.timeout_seconds),
            retry_policy=retry_policy,
        )

        return result
