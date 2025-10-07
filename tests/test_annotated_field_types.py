"""Test that Annotated[type, Field(...)] preserves correct JSON schema types."""

from typing import Annotated, Any

import pytest
from pydantic import Field

from olive import Inject, olive_tool
from olive.registry import _registry


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clean registry before each test."""
    yield
    _registry.clear()


def test_annotated_string_type():
    """Test that Annotated[str, Field(...)] produces type: string."""

    @olive_tool
    def test_tool(
        name: Annotated[str, Field(description="A string field")],
    ) -> str:
        return name

    tool_info = _registry.get("test_tool")
    assert tool_info is not None

    props = tool_info.input_schema["properties"]
    assert props["name"]["type"] == "string"
    assert props["name"]["description"] == "A string field"


def test_annotated_boolean_type():
    """Test that Annotated[bool, Field(...)] produces type: boolean."""

    @olive_tool
    def test_tool(
        enabled: Annotated[bool, Field(description="A boolean field")],
    ) -> bool:
        return enabled

    tool_info = _registry.get("test_tool")
    assert tool_info is not None

    props = tool_info.input_schema["properties"]
    assert props["enabled"]["type"] == "boolean"


def test_annotated_integer_type():
    """Test that Annotated[int, Field(...)] produces type: integer."""

    @olive_tool
    def test_tool(
        count: Annotated[int, Field(description="An integer field")],
    ) -> int:
        return count

    tool_info = _registry.get("test_tool")
    assert tool_info is not None

    props = tool_info.input_schema["properties"]
    assert props["count"]["type"] == "integer"


def test_annotated_array_type():
    """Test that Annotated[list[str], Field(...)] produces type: array."""

    @olive_tool
    def test_tool(
        items: Annotated[list[str], Field(description="A list of strings")],
    ) -> list[str]:
        return items

    tool_info = _registry.get("test_tool")
    assert tool_info is not None

    props = tool_info.input_schema["properties"]
    assert props["items"]["type"] == "array"
    assert props["items"]["items"]["type"] == "string"


def test_annotated_dict_type():
    """Test that Annotated[dict[str, str], Field(...)] produces type: object."""

    @olive_tool
    def test_tool(
        config: Annotated[dict[str, str], Field(description="A dictionary")],
    ) -> dict[str, str]:
        return config

    tool_info = _registry.get("test_tool")
    assert tool_info is not None

    props = tool_info.input_schema["properties"]
    assert props["config"]["type"] == "object"
    assert props["config"]["additionalProperties"]["type"] == "string"


def test_annotated_with_inject_excluded():
    """Test that Annotated[str, Inject(...)] is excluded from schema."""

    @olive_tool
    def test_tool(
        visible_param: Annotated[str, Field(description="Visible to LLM")],
        injected_param: Annotated[str, Inject(key="assistant_id")],
    ) -> str:
        return visible_param

    tool_info = _registry.get("test_tool")
    assert tool_info is not None

    props = tool_info.input_schema["properties"]

    # Visible param should be in schema with correct type
    assert "visible_param" in props
    assert props["visible_param"]["type"] == "string"

    # Injected param should NOT be in schema
    assert "injected_param" not in props

    # But should be in injections list
    assert len(tool_info.injections) == 1
    assert tool_info.injections[0].param == "injected_param"
    assert tool_info.injections[0].config_key == "assistant_id"


def test_mixed_annotated_types():
    """Test a tool with multiple Annotated types."""

    @olive_tool
    def test_tool(
        text: Annotated[str, Field(description="Text input")],
        count: Annotated[int, Field(description="Count value")] = 10,
        enabled: Annotated[bool, Field(description="Enable feature")] = True,
        tags: Annotated[list[str], Field(description="Tags list")] = None,
        metadata: Annotated[dict[str, Any], Field(description="Metadata dict")] = None,
        assistant_id: Annotated[str, Inject(key="assistant_id")] = "",
    ) -> dict:
        return {}

    tool_info = _registry.get("test_tool")
    assert tool_info is not None

    props = tool_info.input_schema["properties"]

    # Check all types are correct
    assert props["text"]["type"] == "string"
    assert props["count"]["type"] == "integer"
    assert props["count"]["default"] == 10
    assert props["enabled"]["type"] == "boolean"
    assert props["enabled"]["default"] is True
    assert props["tags"]["type"] == "array"
    assert props["metadata"]["type"] == "object"

    # Injected param excluded
    assert "assistant_id" not in props
    assert len(tool_info.injections) == 1
