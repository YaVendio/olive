"""Test ElevenLabs ObjectJsonSchemaProperty format compliance."""

from typing import Annotated

import pytest
from fastapi.testclient import TestClient
from pydantic import Field

from olive import Inject, olive_tool
from olive.registry import _registry
from olive.server.app import create_app


@pytest.fixture
def test_app():
    """Create test app with various tool types."""
    _registry.clear()

    @olive_tool
    def string_tool(name: Annotated[str, Field(description="A string")]) -> str:
        return name

    @olive_tool
    def array_tool(emails: Annotated[list[str], Field(description="Emails")]) -> list:
        return emails

    @olive_tool
    def dict_tool(config: Annotated[dict[str, str], Field(description="Config")]) -> dict:
        return config

    @olive_tool
    def with_inject(
        name: str,
        assistant_id: Annotated[str, Inject(key="assistant_id")],
    ) -> str:
        return name

    app = create_app()
    yield app
    _registry.clear()


def test_elevenlabs_object_schema_root(test_app):
    """Test that parameters has type: object at root and expects_response is present."""
    client = TestClient(test_app)

    response = client.get("/olive/tools/elevenlabs")
    tools = response.json()

    for tool in tools:
        # Verify tool-level fields
        assert tool["type"] == "client"
        assert "name" in tool
        assert "description" in tool
        assert "expects_response" in tool
        assert tool["expects_response"] is True

        # Verify parameters structure
        params = tool["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params


def test_no_additional_properties(test_app):
    """Test that additionalProperties is NOT included (not in ElevenLabs schema)."""
    client = TestClient(test_app)

    response = client.get("/olive/tools/elevenlabs")
    tools = response.json()

    # Check dict_tool which has additionalProperties in JSON Schema
    dict_tool = next(t for t in tools if t["name"] == "dict_tool")

    # Root should not have additionalProperties
    assert "additionalProperties" not in dict_tool["parameters"]

    # Property itself should not have additionalProperties
    config_prop = dict_tool["parameters"]["properties"]["config"]
    assert "additionalProperties" not in config_prop


def test_clean_property_schemas(test_app):
    """Test that properties only include allowed fields."""
    client = TestClient(test_app)

    response = client.get("/olive/tools/elevenlabs")
    tools = response.json()

    string_tool = next(t for t in tools if t["name"] == "string_tool")
    name_prop = string_tool["parameters"]["properties"]["name"]

    # Should only have type and description
    assert set(name_prop.keys()) == {"type", "description"}
    assert name_prop["type"] == "string"


def test_array_has_items(test_app):
    """Test that array types include items schema."""
    client = TestClient(test_app)

    response = client.get("/olive/tools/elevenlabs")
    tools = response.json()

    array_tool = next(t for t in tools if t["name"] == "array_tool")
    emails_prop = array_tool["parameters"]["properties"]["emails"]

    assert emails_prop["type"] == "array"
    assert "items" in emails_prop
    assert emails_prop["items"]["type"] == "string"


def test_injected_params_excluded(test_app):
    """Test that injected params are excluded from schema."""
    client = TestClient(test_app)

    response = client.get("/olive/tools/elevenlabs")
    tools = response.json()

    tool = next(t for t in tools if t["name"] == "with_inject")
    props = tool["parameters"]["properties"]

    # Only visible param should be present
    assert "name" in props
    assert "assistant_id" not in props
