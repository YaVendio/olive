"""Unit tests for the olive_tool decorator."""

import pytest

from olive import olive_tool
from olive.registry import _registry


def test_decorator_registers_function():
    """Test that @olive_tool registers a function in the registry."""
    # Clear registry
    _registry.clear()

    @olive_tool
    def test_func(x: int, y: int) -> int:
        """Add two numbers."""
        return x + y

    # Check that function is registered
    tool_info = _registry.get("test_func")
    assert tool_info is not None
    assert tool_info.name == "test_func"
    assert tool_info.description == "Add two numbers."
    assert tool_info.func == test_func


def test_decorator_with_custom_description():
    """Test decorator with custom description."""
    _registry.clear()

    @olive_tool(description="Custom description")
    def test_func():
        """This docstring is ignored."""
        pass

    tool_info = _registry.get("test_func")
    assert tool_info.description == "Custom description"


def test_decorator_preserves_function():
    """Test that decorator doesn't modify the original function."""

    @olive_tool
    def add(x: int, y: int) -> int:
        return x + y

    # Function should work normally
    assert add(2, 3) == 5
    assert add.__name__ == "add"


def test_decorator_extracts_schema():
    """Test that decorator extracts correct schema from type hints."""
    _registry.clear()

    @olive_tool
    def process_data(text: str, count: int = 5, enabled: bool = True) -> dict:
        """Process some data."""
        return {"text": text, "count": count, "enabled": enabled}

    tool_info = _registry.get("process_data")

    # Check input schema
    assert tool_info.input_schema["type"] == "object"
    assert "text" in tool_info.input_schema["properties"]
    assert "count" in tool_info.input_schema["properties"]
    assert "enabled" in tool_info.input_schema["properties"]

    # Check required fields (only text has no default)
    assert tool_info.input_schema["required"] == ["text"]

    # Check defaults
    assert tool_info.input_schema["properties"]["count"]["default"] == 5
    assert tool_info.input_schema["properties"]["enabled"]["default"] is True

    # Check output schema
    assert tool_info.output_schema["type"] == "object"


def test_duplicate_registration_raises():
    """Test that registering the same tool twice raises an error."""
    _registry.clear()

    @olive_tool
    def my_tool():
        pass

    # Try to register again
    with pytest.raises(ValueError, match="already registered"):

        @olive_tool
        def my_tool():  # Same name
            pass
