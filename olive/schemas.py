"""Schemas and models for Olive."""

import inspect
import types
from collections.abc import Callable
from typing import Any, Union, get_type_hints

from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    """Information about a registered tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    func: Callable[..., Any] = Field(exclude=True)  # Don't serialize the function

    # Temporal configuration (v1 mode)
    timeout_seconds: int = 300
    retry_policy: dict[str, Any] | None = None


class ToolCallRequest(BaseModel):
    """Request to call a tool."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    """Response from a tool call."""

    success: bool
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


def extract_schema_from_function(func: Callable) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract input and output schemas from a function's type hints."""
    # Get type hints
    hints = get_type_hints(func)
    sig = inspect.signature(func)

    # Build input schema
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        # Get type hint
        param_type = hints.get(param_name, Any)

        # Convert Python type to JSON schema type
        json_type = python_type_to_json_schema(param_type)

        properties[param_name] = json_type

        # Check if required (no default value)
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
        else:
            # Add default value to schema
            if param.default is not None:
                properties[param_name]["default"] = param.default

    input_schema = {"type": "object", "properties": properties, "required": required}

    # Build output schema
    return_type = hints.get("return", Any)
    output_schema = python_type_to_json_schema(return_type)

    return input_schema, output_schema


def python_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    """Convert Python type to JSON schema."""
    # Handle basic types
    if py_type is str:
        return {"type": "string"}
    elif py_type is int:
        return {"type": "integer"}
    elif py_type is float:
        return {"type": "number"}
    elif py_type is bool:
        return {"type": "boolean"}
    elif py_type is list or py_type is list:
        return {"type": "array"}
    elif py_type is dict or py_type is dict:
        return {"type": "object"}
    elif py_type is Any:
        return {}  # No schema constraint
    elif py_type is type(None):
        return {"type": "null"}

    # Handle generic types
    origin = getattr(py_type, "__origin__", None)
    if origin is list:
        args = getattr(py_type, "__args__", ())
        if args:
            return {"type": "array", "items": python_type_to_json_schema(args[0])}
        return {"type": "array"}
    elif origin is dict:
        return {"type": "object"}
    elif origin is Union:
        args = getattr(py_type, "__args__", ())
        # Handle Optional[T] (Union[T, None])
        if len(args) == 2 and type(None) in args:
            non_none_type = args[0] if args[1] is type(None) else args[1]
            schema = python_type_to_json_schema(non_none_type)
            schema["nullable"] = True
            return schema

    # Handle Python 3.10+ union syntax (e.g., dict | None)
    if isinstance(py_type, types.UnionType):
        args = getattr(py_type, "__args__", ())
        # Handle Optional[T] (T | None)
        if len(args) == 2 and type(None) in args:
            non_none_type = args[0] if args[1] is type(None) else args[1]
            schema = python_type_to_json_schema(non_none_type)
            schema["nullable"] = True
            return schema

    # For complex types, just return object
    return {"type": "object"}
