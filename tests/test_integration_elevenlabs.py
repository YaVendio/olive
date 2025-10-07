"""Integration test for ElevenLabs tool format conversion.

This test verifies that:
1. Olive server exposes /olive/tools/elevenlabs endpoint
2. OliveClient.as_elevenlabs_tools() works correctly
3. Tool format matches ElevenLabs Agents Platform expectations
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from olive import olive_tool
from olive.registry import _registry
from olive.server.app import create_app


@olive_tool(description="Test tool for ElevenLabs format")
def test_tool_for_elevenlabs(name: str, age: int = 25) -> dict:
    """A test tool with parameters."""
    return {"name": name, "age": age}


@pytest.fixture
def test_app():
    """Create test app with registered tool."""
    app = create_app()
    yield app
    # Cleanup
    _registry.clear()


def test_elevenlabs_endpoint_exists(test_app):
    """Test that /olive/tools/elevenlabs endpoint exists."""
    client = TestClient(test_app)

    response = client.get("/olive/tools/elevenlabs")
    assert response.status_code == 200

    tools = response.json()
    assert isinstance(tools, list)


def test_elevenlabs_tool_format(test_app):
    """Test that tools are converted to correct ElevenLabs format."""
    client = TestClient(test_app)

    response = client.get("/olive/tools/elevenlabs")
    assert response.status_code == 200

    tools = response.json()

    # Should have at least our test tool
    assert len(tools) > 0

    # Check format matches ElevenLabs spec
    tool = tools[0]
    assert "type" in tool
    assert "name" in tool
    assert "description" in tool
    assert "parameters" in tool

    # Type should default to client_tool
    assert tool["type"] == "client_tool"

    # Parameters should be JSON schema
    assert "type" in tool["parameters"]
    assert tool["parameters"]["type"] == "object"


def test_elevenlabs_tool_type_parameter(test_app):
    """Test that tool_type query parameter works."""
    client = TestClient(test_app)

    # Test with server_tool type
    response = client.get("/olive/tools/elevenlabs?tool_type=server_tool")
    assert response.status_code == 200

    tools = response.json()
    if tools:
        assert tools[0]["type"] == "server_tool"


@pytest.mark.asyncio
async def test_olive_client_as_elevenlabs_tools():
    """Test OliveClient.as_elevenlabs_tools() method."""
    from unittest.mock import AsyncMock, patch

    # Mock the HTTP response
    mock_tools = [
        {
            "name": "schedule_appointment",
            "description": "Schedule an appointment",
            "input_schema": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                },
                "required": ["date", "time"],
            },
            "output_schema": {"type": "string"},
        }
    ]

    from olive_client import OliveClient

    client = OliveClient("http://localhost:8000")

    # Mock get_tools to return our test tools
    client.get_tools = AsyncMock(return_value=mock_tools)

    # Convert to ElevenLabs format
    el_tools = await client.as_elevenlabs_tools()

    assert len(el_tools) == 1
    assert el_tools[0]["type"] == "client_tool"
    assert el_tools[0]["name"] == "schedule_appointment"
    assert el_tools[0]["description"] == "Schedule an appointment"
    assert el_tools[0]["parameters"] == mock_tools[0]["input_schema"]


@pytest.mark.asyncio
async def test_olive_client_elevenlabs_with_tool_filter():
    """Test filtering specific tools for ElevenLabs."""
    from unittest.mock import AsyncMock

    from olive_client import OliveClient

    mock_tools = [
        {"name": "tool1", "description": "First tool", "input_schema": {}},
        {"name": "tool2", "description": "Second tool", "input_schema": {}},
        {"name": "tool3", "description": "Third tool", "input_schema": {}},
    ]

    client = OliveClient("http://localhost:8000")
    client.get_tools = AsyncMock(return_value=mock_tools)

    # Request only specific tools
    el_tools = await client.as_elevenlabs_tools(tool_names=["tool1", "tool3"])

    assert len(el_tools) == 2
    assert el_tools[0]["name"] == "tool1"
    assert el_tools[1]["name"] == "tool3"


@pytest.mark.asyncio
async def test_olive_client_elevenlabs_server_tool_type():
    """Test specifying server_tool type."""
    from unittest.mock import AsyncMock

    from olive_client import OliveClient

    mock_tools = [{"name": "api_tool", "description": "API tool", "input_schema": {}}]

    client = OliveClient("http://localhost:8000")
    client.get_tools = AsyncMock(return_value=mock_tools)

    # Request server_tool type
    el_tools = await client.as_elevenlabs_tools(tool_type="server_tool")

    assert len(el_tools) == 1
    assert el_tools[0]["type"] == "server_tool"


@pytest.mark.asyncio
async def test_olive_client_elevenlabs_with_context_injection():
    """Test context injection for ElevenLabs tools."""
    from unittest.mock import AsyncMock, Mock

    from olive_client import OliveClient

    # Mock tools with injections
    mock_tools = [
        {
            "name": "change_name",
            "description": "Change assistant name",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            "injections": [{"param": "assistant_id", "config_key": "assistant_id", "required": True}],
        }
    ]

    client = OliveClient("http://localhost:8000")

    # Mock HTTP client responses
    get_response = Mock()
    get_response.json.return_value = mock_tools
    get_response.raise_for_status = Mock()

    # Get tools with context
    with patch.object(client._client, "get", return_value=get_response):
        el_tools = await client.as_elevenlabs_tools(
            context={"phone_number": "1234567890", "assistant_id": "test-assistant"}
        )

    # Verify context was stored
    assert client._elevenlabs_context is not None
    assert client._elevenlabs_context["phone_number"] == "1234567890"
    assert client._elevenlabs_context["assistant_id"] == "test-assistant"

    # Now test that call_tool uses the stored context automatically
    call_response = Mock()
    call_response.json.return_value = {"success": True, "result": "Updated"}
    call_response.raise_for_status = Mock()

    with patch.object(client._client, "post", return_value=call_response) as mock_post:
        result = await client.call_tool("change_name", {"name": "NewName"})

        # Verify context was included in the payload
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert payload["context"] == {
            "phone_number": "1234567890",
            "assistant_id": "test-assistant",
        }
        assert result == "Updated"

    await client.close()
