"""Temporal workflows for Olive."""

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class OliveToolWorkflow:
    """Workflow for executing Olive tools."""

    @workflow.run
    async def run(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool as a Temporal activity."""
        # Get retry policy from tool metadata (we'll store this in activity options)
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
        )

        # Execute the activity
        result = await workflow.execute_activity(
            tool_name,
            arguments,
            start_to_close_timeout=timedelta(seconds=300),
            retry_policy=retry_policy,
        )

        return result
