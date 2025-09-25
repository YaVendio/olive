"""Unit tests for schema extraction."""

from typing import Optional

from olive.schemas import extract_schema_from_function, python_type_to_json_schema


def test_basic_type_conversion():
    """Test conversion of basic Python types to JSON schema."""
    assert python_type_to_json_schema(str) == {"type": "string"}
    assert python_type_to_json_schema(int) == {"type": "integer"}
    assert python_type_to_json_schema(float) == {"type": "number"}
    assert python_type_to_json_schema(bool) == {"type": "boolean"}
    assert python_type_to_json_schema(list) == {"type": "array"}
    assert python_type_to_json_schema(dict) == {"type": "object"}


def test_optional_type_conversion():
    """Test conversion of Optional types."""
    schema = python_type_to_json_schema(str | None)
    assert schema["type"] == "string"
    assert schema["nullable"] is True


def test_list_type_conversion():
    """Test conversion of List types."""
    schema = python_type_to_json_schema(list[int])
    assert schema["type"] == "array"
    assert schema["items"]["type"] == "integer"


def test_extract_simple_function_schema():
    """Test schema extraction from a simple function."""

    def add(x: int, y: int) -> int:
        return x + y

    input_schema, output_schema, injections = extract_schema_from_function(add)

    # Check input schema
    assert input_schema["type"] == "object"
    assert input_schema["properties"]["x"]["type"] == "integer"
    assert input_schema["properties"]["y"]["type"] == "integer"
    assert input_schema["required"] == ["x", "y"]

    # Check output schema
    assert output_schema["type"] == "integer"


def test_extract_function_with_defaults():
    """Test schema extraction from function with default values."""

    def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}!"

    input_schema, output_schema, injections = extract_schema_from_function(greet)

    # Check required fields
    assert input_schema["required"] == ["name"]  # greeting has default

    # Check default value is included
    assert input_schema["properties"]["greeting"]["default"] == "Hello"


def test_extract_function_with_optional():
    """Test schema extraction with Optional types."""

    def process(data: str, metadata: dict | None = None) -> dict:
        return {"data": data, "metadata": metadata}

    input_schema, output_schema, injections = extract_schema_from_function(process)

    # Check optional parameter
    assert input_schema["properties"]["metadata"]["type"] == "object"
    assert input_schema["properties"]["metadata"]["nullable"] is True

    # Should not be in required since it has a default
    assert "metadata" not in input_schema["required"]


def test_extract_function_no_type_hints():
    """Test schema extraction from function without type hints."""

    def mystery_function(x, y):
        return x + y

    input_schema, output_schema, injections = extract_schema_from_function(mystery_function)

    # Should handle gracefully with no type constraints
    assert input_schema["properties"]["x"] == {}
    assert input_schema["properties"]["y"] == {}
    assert output_schema == {}  # Any type
    assert injections == []
