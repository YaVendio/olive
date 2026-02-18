"""FastAPI router for Olive endpoints."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request

from olive.registry import _registry
from olive.schemas import ToolCallRequest, ToolCallResponse

logger = logging.getLogger(__name__)

# Type checks for validating injected context values
_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _get_temporal_worker(request: Request) -> Any | None:
    """Get the temporal worker from app state."""
    return getattr(request.app.state, "temporal_worker", None)


# Backward-compat shim: some tests and external code may call set_temporal_worker().
# Prefer setting app.state.temporal_worker directly in lifespan.
_temporal_worker_fallback: Any | None = None


def set_temporal_worker(worker: Any) -> None:
    """Set the fallback Temporal worker reference (deprecated, use app.state instead)."""
    global _temporal_worker_fallback
    _temporal_worker_fallback = worker


router = APIRouter()


@router.get("/tools")
async def list_tools(request: Request, profile: str | None = None) -> list[dict[str, Any]]:
    """List all registered Olive tools.

    Args:
        profile: Optional profile name to filter tools by (e.g., "javi", "clamy").
                 Comparison is case-insensitive.
    """
    temporal_worker = _get_temporal_worker(request) or _temporal_worker_fallback

    tools = []
    # Normalize profile to lowercase for case-insensitive comparison
    profile_lower = profile.lower() if profile else None

    for tool_info in _registry.list_all():
        # Filter by profile if specified (case-insensitive)
        tool_profiles = getattr(tool_info, "profiles", [])
        if profile_lower and profile_lower not in [p.lower() for p in tool_profiles]:
            continue

        tool_data = {
            "name": tool_info.name,
            "description": tool_info.description,
            "input_schema": tool_info.input_schema,
            "output_schema": tool_info.output_schema,
        }

        # Add profiles metadata
        if tool_profiles:
            tool_data["profiles"] = tool_profiles

        # Add temporal metadata if running in v1 mode
        if temporal_worker is not None:
            tool_data["temporal"] = {
                "enabled": True,
                "timeout_seconds": getattr(tool_info, "timeout_seconds", 300),
                "retry_policy": getattr(tool_info, "retry_policy", {"max_attempts": 3}),
            }

        # Add injection metadata so clients can auto-inject from context
        if getattr(tool_info, "injections", None):
            tool_data["injections"] = [
                {
                    "param": inj.param,
                    "config_key": inj.config_key,
                    "required": inj.required,
                }
                for inj in tool_info.injections
            ]

        tools.append(tool_data)
    return tools


@router.get("/tools/elevenlabs")
async def list_elevenlabs_tools(tool_type: str = "client") -> list[dict[str, Any]]:
    """List all registered Olive tools in ElevenLabs Agents Platform format.

    Note: tool_type must be "client" (not "client_tool") to match ElevenLabs API schema.
    ElevenLabs expects parameters as ObjectJsonSchemaProperty format (JSON Schema compatible).
    """
    tools = []
    for tool_info in _registry.list_all():
        # ElevenLabs ClientToolConfig expects parameters to be ObjectJsonSchemaProperty
        # which is essentially JSON Schema but must have explicit "type": "object" at root
        parameters = _ensure_object_schema(tool_info.input_schema)

        # Convert to ElevenLabs ClientToolConfig format
        el_tool = {
            "type": tool_type,  # Must be "client" for ClientToolConfig
            "name": tool_info.name,
            "description": tool_info.description,
            "parameters": parameters,  # ObjectJsonSchemaProperty format
            "expects_response": True,  # All tools expect a response for the agent
        }

        tools.append(el_tool)
    return tools


def _ensure_object_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Ensure schema is in ObjectJsonSchemaProperty format for ElevenLabs.

    ElevenLabs requires:
    - Root must have "type": "object"
    - Only include "type", "properties", "required", "description"
    - No "additionalProperties" or other JSON Schema fields
    """
    # Start with a clean ObjectJsonSchemaProperty
    clean_schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": schema.get("required", []),
    }

    # Add description if present
    if "description" in schema:
        clean_schema["description"] = schema["description"]

    # Convert properties to ElevenLabs format
    for prop_name, prop_schema in schema.get("properties", {}).items():
        clean_schema["properties"][prop_name] = _convert_property_schema(prop_schema, prop_name)

    return clean_schema


def _convert_property_schema(prop_schema: dict[str, Any], parent_name: str = "") -> dict[str, Any]:
    """Convert a property schema to ElevenLabs ObjectJsonSchemaPropertyOutput format.

    Handles: LiteralJsonSchemaProperty, ObjectJsonSchemaProperty, ArrayJsonSchemaProperty

    Note: ElevenLabs requires all properties to have a NON-EMPTY description,
    dynamic_variable, or constant_value. Empty string is rejected.

    Args:
        prop_schema: The property schema to convert
        parent_name: Name of parent field (for generating meaningful descriptions)
    """
    prop_type = prop_schema.get("type", "string")

    # Create clean property with only allowed fields
    clean_prop: dict[str, Any] = {
        "type": prop_type,
    }

    # Add description (REQUIRED and must be NON-EMPTY)
    if "description" in prop_schema and prop_schema["description"]:
        clean_prop["description"] = prop_schema["description"]
    else:
        # Generate meaningful default description based on context
        if prop_type == "array":
            clean_prop["description"] = f"List of {parent_name}" if parent_name else "Array of items"
        elif prop_type == "object":
            clean_prop["description"] = (
                f"{parent_name.replace('_', ' ').title()} object" if parent_name else "Object value"
            )
        else:
            # For primitives: use type name
            clean_prop["description"] = f"{prop_type.capitalize()} value"

    # Handle specific types
    if prop_type == "array":
        # ArrayJsonSchemaProperty requires items
        items = prop_schema.get("items", {})
        if items:
            # Pass meaningful context for nested items
            item_context = f"{parent_name}_item" if parent_name else "item"
            clean_prop["items"] = _convert_property_schema(items, item_context)

    elif prop_type == "object":
        # ObjectJsonSchemaProperty can have properties and required
        if "properties" in prop_schema:
            clean_prop["properties"] = {k: _convert_property_schema(v, k) for k, v in prop_schema["properties"].items()}
        if "required" in prop_schema:
            clean_prop["required"] = prop_schema["required"]
        # Note: Don't include additionalProperties - not in ElevenLabs schema

    # For literal types (string, boolean, number, integer), type and description is enough

    return clean_prop


@router.post("/tools/call")
async def call_tool(request: Request, tool_request: ToolCallRequest) -> ToolCallResponse:
    """Call a registered Olive tool."""
    temporal_worker = _get_temporal_worker(request) or _temporal_worker_fallback

    # Get the tool
    tool_info = _registry.get(tool_request.tool_name)
    if not tool_info:
        return ToolCallResponse(
            success=False, error=f"Tool '{tool_request.tool_name}' not found", error_type="tool_not_found"
        )

    try:
        logger.info(
            "Olive tool call: name=%s context=%s injections=%s args=%s",
            tool_request.tool_name,
            tool_request.context,
            [{"param": inj.param, "key": inj.config_key} for inj in tool_info.injections],
            tool_request.arguments,
        )

        # Normalize arguments: ensure it's a dict (handle OpenRouter empty string quirk)
        # When tools have no parameters, some providers send "" instead of {}
        arguments = tool_request.arguments
        if not arguments or (isinstance(arguments, dict) and not arguments):
            arguments = {}

        # Merge context into arguments for injection
        final_args = dict(arguments)
        context = tool_request.context or {}
        for injection in tool_info.injections:
            param = injection.param
            config_key = injection.config_key
            # Only inject if not already provided in arguments
            if param not in final_args:
                value = context.get(config_key)
                if value is not None:
                    # Validate type if expected_type is known
                    if injection.expected_type:
                        expected_py_type = _TYPE_CHECKS.get(injection.expected_type)
                        if expected_py_type and not isinstance(value, expected_py_type):
                            return ToolCallResponse(
                                success=False,
                                error=(
                                    f"Context key '{config_key}' for param '{param}' expected type "
                                    f"'{injection.expected_type}', got '{type(value).__name__}'"
                                ),
                                error_type="validation_error",
                            )
                    final_args[param] = value
                    logger.info("Injected %s=%s into tool %s", param, value, tool_request.tool_name)
                elif injection.required:
                    logger.warning(
                        "Missing required context key=%s for param=%s",
                        config_key,
                        param,
                    )
                    return ToolCallResponse(
                        success=False,
                        error=f"Missing required context value '{config_key}' for param '{param}'",
                        error_type="missing_context",
                    )

        logger.info("Final args for %s: %s", tool_request.tool_name, list(final_args.keys()))

        # Use Temporal if available (v1 mode)
        if temporal_worker is not None:
            # Check fire-and-forget mode
            if tool_info.fire_and_forget:
                # Fire-and-forget: start workflow without waiting
                workflow_id = await temporal_worker.start_tool(
                    tool_request.tool_name,
                    final_args,
                    timeout_seconds=tool_info.timeout_seconds,
                    retry_policy=tool_info.retry_policy,
                )
                return ToolCallResponse(
                    success=True,
                    result=f"Workflow started: {workflow_id}",
                    metadata={
                        "executed_via": "temporal",
                        "workflow_id": workflow_id,
                        "fire_and_forget": True,
                    },
                )
            else:
                # Wait for completion
                result = await temporal_worker.execute_tool(
                    tool_request.tool_name,
                    final_args,
                    timeout_seconds=tool_info.timeout_seconds,
                    retry_policy=tool_info.retry_policy,
                )
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
        timeout = tool_info.timeout_seconds
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(func(**final_args), timeout=timeout)
            else:
                # Note: wait_for cancels the future but cannot kill the executor thread.
                # The thread continues running but its result is discarded, unblocking
                # the uvicorn worker to serve other requests.
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: func(**final_args)),
                    timeout=timeout,
                )
        except TimeoutError:
            logger.error("Tool '%s' timed out after %ds", tool_request.tool_name, timeout)
            return ToolCallResponse(
                success=False,
                error=f"Tool '{tool_request.tool_name}' timed out after {timeout}s",
                error_type="timeout",
            )

        return ToolCallResponse(success=True, result=result)
    except Exception as e:
        logger.exception("Tool '%s' execution failed", tool_request.tool_name)
        return ToolCallResponse(success=False, error=str(e), error_type="execution_error")


@router.get("/health")
async def health_check(request: Request) -> dict[str, Any]:
    """Health check endpoint."""
    temporal_worker = _get_temporal_worker(request) or _temporal_worker_fallback
    tools = _registry.list_all()
    return {
        "status": "ok",
        "tools_count": len(tools),
        "temporal_connected": temporal_worker is not None,
    }
