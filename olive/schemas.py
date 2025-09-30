"""Schemas and models for Olive."""

import inspect
import types
from collections.abc import Callable
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

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

    # Context injections (parameters excluded from input_schema and filled from configurable)
    injections: list["ToolInjection"] = Field(default_factory=list)


class ToolInjection(BaseModel):
    """Descriptor for parameters injected from runtime configurable context."""

    param: str
    config_key: str
    required: bool = True


class ToolCallRequest(BaseModel):
    """Request to call a tool."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] | None = Field(
        default=None,
        description="Runtime context for injection (e.g., assistant_id, phone_number)",
    )


class ToolCallResponse(BaseModel):
    """Response from a tool call."""

    success: bool
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class Inject(BaseModel):
    """Marker used with typing.Annotated to declare context injection.

    Example:
        def tool(arg: int, assistant_id: Annotated[str, Inject(key="assistant_id")]): ...
    """

    key: str
    required: bool = True


def _parse_inject_annotation(py_type: Any) -> tuple[Any, ToolInjection | None]:
    """If py_type is Annotated[..., Inject], return (base_type, ToolInjection)."""
    origin = get_origin(py_type)
    if origin is Annotated:
        args = get_args(py_type)
        if not args:
            return py_type, None
        base = args[0]
        meta = args[1:]
        for m in meta:
            if isinstance(m, Inject):
                return base, ToolInjection(param="", config_key=m.key, required=m.required)
    return py_type, None


def extract_schema_from_function(func: Callable) -> tuple[dict[str, Any], dict[str, Any], list[ToolInjection]]:
    """Extract input/output JSON schemas and injection metadata from function type hints."""
    # Get type hints with include_extras=True to preserve Annotated metadata
    hints = get_type_hints(func, include_extras=True)
    sig = inspect.signature(func)

    # Build input schema
    properties = {}
    required = []
    injections: list[ToolInjection] = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        # Get type hint
        param_type = hints.get(param_name, Any)

        # Check for Annotated[..., Inject]
        base_type, inject_meta = _parse_inject_annotation(param_type)
        if inject_meta is not None:
            # Record injection and skip adding to input schema
            inject_meta.param = param_name
            injections.append(inject_meta)
            continue

        # Convert Python type to JSON schema type
        json_type = python_type_to_json_schema(base_type)

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

    return input_schema, output_schema, injections


def python_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    """Convert Python type to JSON schema."""
    # Handle basic types
    if py_type is str:
        return {"type": "string"}
    if py_type is int:
        return {"type": "integer"}
    if py_type is float:
        return {"type": "number"}
    if py_type is bool:
        return {"type": "boolean"}
    if py_type in {list, tuple, set}:
        return {"type": "array"}
    if py_type is dict:
        return {"type": "object"}
    if py_type is Any:
        return {}  # No schema constraint
    if py_type is type(None):
        return {"type": "null"}

    # Handle typing and collections generics
    origin = get_origin(py_type) or getattr(py_type, "__origin__", None)
    args = get_args(py_type) or getattr(py_type, "__args__", ())

    if origin in {list, set}:
        array_schema: dict[str, Any] = {"type": "array"}
        if args:
            array_schema["items"] = python_type_to_json_schema(args[0])
        return array_schema

    if origin is tuple:
        tuple_schema: dict[str, Any] = {"type": "array"}
        if args:
            item_schemas = [python_type_to_json_schema(arg) for arg in args]
            tuple_schema["items"] = item_schemas
        return tuple_schema

    if origin is dict:
        # Only value type is relevant for JSON schema; keep lean schema when not provided
        dict_schema: dict[str, Any] = {"type": "object"}
        if len(args) > 1:
            dict_schema["additionalProperties"] = python_type_to_json_schema(args[1])
        return dict_schema

    if origin is Union or isinstance(py_type, types.UnionType):
        # Handle Optional[T] or union including None
        union_args = args or getattr(py_type, "__args__", ())
        if len(union_args) == 2 and type(None) in union_args:
            non_none = next(t for t in union_args if t is not type(None))
            schema = python_type_to_json_schema(non_none)
            schema["nullable"] = True
            return schema
        # Generic union: allow any of the schemas
        return {"anyOf": [python_type_to_json_schema(t) for t in union_args]}

    # For Pydantic/BaseModel types, use object schema
    if inspect.isclass(py_type) and issubclass(py_type, BaseModel):
        return {"$ref": f"#/definitions/{py_type.__name__}"}

    # For callables, use generic object
    if callable(py_type):
        return {"type": "object"}

    # Default fallback for unknown types
    return {"type": "object"}
