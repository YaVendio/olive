"""FastAPI router for Olive endpoints."""

import asyncio
from typing import Any

from fastapi import APIRouter

from olive.registry import _registry
from olive.schemas import ToolCallRequest, ToolCallResponse

# Global reference to Temporal worker (set by v1 mode)
_temporal_worker: Any | None = None


def set_temporal_worker(worker: Any) -> None:
    """Set the global Temporal worker for v1 mode."""
    global _temporal_worker
    _temporal_worker = worker


router = APIRouter()


@router.get("/tools")
async def list_tools() -> list[dict[str, Any]]:
    """List all registered Olive tools."""
    tools = []
    for tool_info in _registry.list_all():
        tool_data = {
            "name": tool_info.name,
            "description": tool_info.description,
            "input_schema": tool_info.input_schema,
            "output_schema": tool_info.output_schema,
        }

        # Add temporal metadata if running in v1 mode
        if _temporal_worker is not None:
            tool_data["temporal"] = {
                "enabled": True,
                "timeout_seconds": getattr(tool_info, "timeout_seconds", 300),
                "retry_policy": getattr(tool_info, "retry_policy", {"max_attempts": 3}),
            }

        tools.append(tool_data)
    return tools


@router.post("/tools/call")
async def call_tool(request: ToolCallRequest) -> ToolCallResponse:
    """Call a registered Olive tool."""
    # Get the tool
    tool_info = _registry.get(request.tool_name)
    if not tool_info:
        return ToolCallResponse(success=False, error=f"Tool '{request.tool_name}' not found")

    try:
        # Use Temporal if available (v1 mode)
        if _temporal_worker is not None:
            result = await _temporal_worker.execute_tool(request.tool_name, request.arguments)
            return ToolCallResponse(
                success=True,
                result=result,
                metadata={
                    "executed_via": "temporal",
                    "workflow_type": "OliveToolWorkflow",
                },
            )

        # Otherwise use direct execution (v0 mode)
        func = tool_info.func
        if asyncio.iscoroutinefunction(func):
            result = await func(**request.arguments)
        else:
            result = func(**request.arguments)

        return ToolCallResponse(success=True, result=result)
    except Exception as e:
        return ToolCallResponse(success=False, error=str(e))
