"""Additional tests for schema module to reach 100% coverage."""

from typing import Any, ForwardRef, Generic, TypeVar

import pytest

from olive.schemas import python_type_to_json_schema


def test_python_type_to_json_schema_generics():
    """Test handling of generic types."""
    # Test with TypeVar
    T = TypeVar("T")

    class GenericClass(Generic[T]):
        pass

    # Generic classes should return object schema
    schema = python_type_to_json_schema(GenericClass)
    assert schema == {"type": "object"}

    # Instantiated generics
    schema = python_type_to_json_schema(GenericClass[int])
    assert schema == {"type": "object"}


def test_python_type_to_json_schema_forward_ref():
    """Test handling of forward references."""
    # Create a forward reference
    forward_ref = ForwardRef("SomeClass")

    # Forward refs should return object schema
    schema = python_type_to_json_schema(forward_ref)
    assert schema == {"type": "object"}


def test_python_type_to_json_schema_any():
    """Test handling of Any type."""
    # Any type doesn't have __origin__ so returns empty dict in basic types check
    schema = python_type_to_json_schema(Any)
    assert schema == {}  # Any matches the "if py_type is Any" condition


def test_python_type_to_json_schema_union_complex():
    """Test handling of complex union types."""
    # Union with more than 2 types (not Optional)
    schema = python_type_to_json_schema(str | int | float)
    assert schema == {"type": "object"}

    # Union with non-None types
    schema = python_type_to_json_schema(str | int)
    assert schema == {"type": "object"}


def test_python_type_to_json_schema_nested_optional():
    """Test handling of nested optional types."""
    # Optional of Optional (edge case)
    schema = python_type_to_json_schema(str | None)
    assert schema["type"] == "string"
    assert schema["nullable"] is True


def test_python_type_to_json_schema_callable():
    """Test handling of callable types."""
    from collections.abc import Callable

    # Callable should return object schema
    schema = python_type_to_json_schema(Callable)
    assert schema == {"type": "object"}

    schema = python_type_to_json_schema(Callable[[int, str], bool])
    assert schema == {"type": "object"}


def test_python_type_to_json_schema_custom_class():
    """Test handling of custom classes."""

    class CustomClass:
        pass

    # Custom classes should return object schema
    schema = python_type_to_json_schema(CustomClass)
    assert schema == {"type": "object"}


def test_python_type_to_json_schema_tuple():
    """Test handling of tuple types."""
    # Plain tuple - not in basic types list, so returns object
    schema = python_type_to_json_schema(tuple)
    assert schema == {"type": "object"}

    # Typed tuple - has __origin__ but not handled specially, so returns object
    schema = python_type_to_json_schema(tuple[int, str])
    assert schema == {"type": "object"}


def test_python_type_to_json_schema_set():
    """Test handling of set types."""
    # Plain set - not in basic types list, so returns object
    schema = python_type_to_json_schema(set)
    assert schema == {"type": "object"}

    # Typed set - has __origin__ but not handled specially, so returns object
    schema = python_type_to_json_schema(set[int])
    assert schema == {"type": "object"}


def test_python_type_to_json_schema_bytes():
    """Test handling of bytes type."""
    # bytes is not in basic types list, so returns object
    schema = python_type_to_json_schema(bytes)
    assert schema == {"type": "object"}


def test_python_type_to_json_schema_none_type():
    """Test handling of None type."""
    schema = python_type_to_json_schema(type(None))
    assert schema == {"type": "null"}


def test_python_type_to_json_schema_complex_nested():
    """Test handling of complex nested types."""
    # Nested dict
    schema = python_type_to_json_schema(dict[str, list[int]])
    assert schema == {"type": "object"}

    # Nested list - list with dict items
    schema = python_type_to_json_schema(list[dict[str, Any]])
    assert schema == {"type": "array", "items": {"type": "object"}}
