"""Test edge cases and error handling for Olive."""

import pytest

from olive.schemas import extract_schema_from_function, python_type_to_json_schema


def test_extract_schema_with_self_parameter():
    """Test that self parameter is properly skipped in class methods."""

    class MyClass:
        def method(self, x: int) -> str:
            return str(x)

    # Extract schema from bound method
    instance = MyClass()
    input_schema, output_schema, injections = extract_schema_from_function(instance.method)

    # Should only have 'x' parameter, not 'self'
    assert list(input_schema["properties"].keys()) == ["x"]
    assert input_schema["properties"]["x"]["type"] == "integer"
    assert output_schema["type"] == "string"


def test_python_type_none():
    """Test conversion of None type."""
    schema = python_type_to_json_schema(type(None))
    assert schema == {"type": "null"}


def test_python_type_bare_list():
    """Test conversion of bare list type without type args."""
    schema = python_type_to_json_schema(list)
    assert schema == {"type": "array"}


def test_python_type_bare_dict():
    """Test conversion of bare dict type without type args."""
    schema = python_type_to_json_schema(dict)
    assert schema == {"type": "object"}


def test_python_type_dict_with_origin():
    """Test conversion of dict with __origin__ attribute."""
    schema = python_type_to_json_schema(dict[str, int])
    assert schema["type"] == "object"
    assert schema["additionalProperties"] == {"type": "integer"}


def test_python_type_fallback_to_object():
    """Test that unknown types fall back to object."""

    class CustomType:
        pass

    schema = python_type_to_json_schema(CustomType)
    assert schema == {"type": "object"}
