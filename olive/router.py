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
async def list_tools(profile: str | None = None) -> list[dict[str, Any]]:
    """List all registered Olive tools.

    Args:
        profile: Optional profile name to filter tools by (e.g., "javi", "clamy").
                 Comparison is case-insensitive.
    """
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
        if _temporal_worker is not None:
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
async def call_tool(request: ToolCallRequest) -> ToolCallResponse:
    """Call a registered Olive tool."""
    import logging

    logger = logging.getLogger(__name__)

    # Get the tool
    tool_info = _registry.get(request.tool_name)
    if not tool_info:
        return ToolCallResponse(success=False, error=f"Tool '{request.tool_name}' not found")

    try:
        logger.info(
            "Olive tool call: name=%s context=%s injections=%s args=%s",
            request.tool_name,
            request.context,
            [{"param": inj.param, "key": inj.config_key} for inj in tool_info.injections],
            request.arguments,
        )

        # Normalize arguments: ensure it's a dict (handle OpenRouter empty string quirk)
        # When tools have no parameters, some providers send "" instead of {}
        arguments = request.arguments
        if not arguments or (isinstance(arguments, dict) and not arguments):
            arguments = {}

        # Merge context into arguments for injection
        final_args = dict(arguments)
        if request.context:
            # Inject context values for declared injections
            for injection in tool_info.injections:
                param = injection.param
                config_key = injection.config_key
                # Only inject if not already provided in arguments
                if param not in final_args:
                    value = request.context.get(config_key)
                    if value is not None:
                        final_args[param] = value
                        logger.info("Injected %s=%s into tool %s", param, value, request.tool_name)
                    elif injection.required:
                        logger.warning(
                            "Missing required context key=%s for param=%s",
                            config_key,
                            param,
                        )
                        return ToolCallResponse(
                            success=False,
                            error=f"Missing required context value '{config_key}' for param '{param}'",
                        )

        logger.info("Final args for %s: %s", request.tool_name, list(final_args.keys()))

        # Use Temporal if available (v1 mode)
        if _temporal_worker is not None:
            # Check fire-and-forget mode
            if tool_info.fire_and_forget:
                # Fire-and-forget: start workflow without waiting
                workflow_id = await _temporal_worker.start_tool(request.tool_name, final_args)
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
                result = await _temporal_worker.execute_tool(request.tool_name, final_args)
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
            result = await func(**final_args)
        else:
            result = func(**final_args)

        return ToolCallResponse(success=True, result=result)
    except Exception as e:
        return ToolCallResponse(success=False, error=str(e))
