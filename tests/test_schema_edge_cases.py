"""Test additional edge cases for schema extraction."""

from olive.schemas import extract_schema_from_function, python_type_to_json_schema


def test_extract_schema_with_method():
    """Test schema extraction skips self parameter correctly."""

    class TestClass:
        def method_with_self(self, x: int, y: str = "default") -> dict:
            """A method with self parameter."""
            return {"x": x, "y": y}

    # Extract schema from unbound method to trigger self parameter handling
    input_schema, output_schema = extract_schema_from_function(TestClass.method_with_self)

    # Should not include 'self' in properties
    assert "self" not in input_schema["properties"]
    assert "x" in input_schema["properties"]
    assert "y" in input_schema["properties"]

    # Check required fields
    assert input_schema["required"] == ["x"]
    assert input_schema["properties"]["y"]["default"] == "default"


def test_bare_list_without_args():
    """Test python_type_to_json_schema with bare list (no type args)."""

    # When list has args but they're empty
    class FakeList:
        __origin__ = list
        __args__ = ()  # Empty args

    schema = python_type_to_json_schema(FakeList())
    assert schema == {"type": "array"}
