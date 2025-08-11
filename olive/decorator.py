"""Olive tool decorator for marking functions as tools."""

from collections.abc import Callable
from typing import Any

from olive.registry import _registry
from olive.schemas import ToolInfo, extract_schema_from_function


def olive_tool[T: Callable](
    func: T | None = None,
    *,
    description: str | None = None,
    timeout_seconds: int = 300,
    retry_policy: dict[str, Any] | None = None,
) -> T | Callable[[T], T]:
    """
    Decorator to mark a function as an Olive tool.

    Can be used with or without parentheses:
        @olive_tool
        def my_func(): ...

        @olive_tool(description="My tool")
        def my_func(): ...

        Args:
        func: The function to decorate (when used without parentheses)
        description: Override the tool description (defaults to function docstring)
        timeout_seconds: Timeout for Temporal execution (v1 mode)
        retry_policy: Retry policy for Temporal execution (v1 mode)

    Returns:
        The decorated function (unchanged)
    """

    def decorator(f: T) -> T:
        # Extract tool information
        tool_name = f.__name__
        tool_description = description or (f.__doc__ or "").strip().split("\n")[0] or f"Tool: {tool_name}"

        # Extract schemas from type hints
        input_schema, output_schema = extract_schema_from_function(f)

        # Create tool info
        tool_info = ToolInfo(
            name=tool_name,
            description=tool_description,
            input_schema=input_schema,
            output_schema=output_schema,
            func=f,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy or {"max_attempts": 3},
        )

        # Register the tool
        _registry.register(tool_info)

        # Return the original function unchanged
        return f

    # Handle both @olive_tool and @olive_tool() usage
    if func is None:
        return decorator
    else:
        return decorator(func)
