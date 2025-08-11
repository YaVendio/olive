"""Temporal activities for Olive tools."""

import asyncio
from collections.abc import Callable
from typing import Any

from temporalio import activity

from olive.schemas import ToolInfo


def create_activity_from_tool(tool_info: ToolInfo) -> Callable:
    """Create a Temporal activity from an Olive tool."""

    # Get the original function
    func = tool_info.func

    # Create activity wrapper based on whether the function is async
    if asyncio.iscoroutinefunction(func):
        # Async function
        @activity.defn(name=tool_info.name)
        async def async_activity_wrapper(arguments: dict[str, Any]) -> Any:
            return await func(**arguments)

        # Preserve function metadata
        async_activity_wrapper.__name__ = tool_info.name
        async_activity_wrapper.__doc__ = tool_info.description

        return async_activity_wrapper
    else:
        # Sync function
        @activity.defn(name=tool_info.name)
        def sync_activity_wrapper(arguments: dict[str, Any]) -> Any:
            return func(**arguments)

        # Preserve function metadata
        sync_activity_wrapper.__name__ = tool_info.name
        sync_activity_wrapper.__doc__ = tool_info.description

        return sync_activity_wrapper
