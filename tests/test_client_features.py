"""Test client features and edge cases."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from olive_client import OliveClient


@pytest.mark.asyncio
async def test_call_tool_with_none_arguments():
    """Test calling a tool with None arguments."""
    client = OliveClient("http://test.com")

    # Mock the HTTP response
    mock_response = Mock()
    mock_response.json.return_value = {"success": True, "result": "test_result"}
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "post", return_value=mock_response) as mock_post:
        result = await client.call_tool("test_tool", None)

        # Should convert None to empty dict
        mock_post.assert_called_once_with(
            "http://test.com/olive/tools/call", json={"tool_name": "test_tool", "arguments": {}}
        )
        assert result == "test_result"

    await client.close()


@pytest.mark.asyncio
async def test_call_tool_failure():
    """Test handling of tool call failures."""
    client = OliveClient("http://test.com")

    # Mock a failure response
    mock_response = Mock()
    mock_response.json.return_value = {"success": False, "error": "Tool not found"}
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "post", return_value=mock_response):
        with pytest.raises(Exception) as exc_info:
            await client.call_tool("missing_tool", {})

        assert "Tool call failed: Tool not found" in str(exc_info.value)

    await client.close()


@pytest.mark.asyncio
async def test_as_langchain_tools_with_filter():
    """Test converting specific tools to LangChain tools."""
    client = OliveClient("http://test.com")

    # Mock get_tools response
    tools_data = [
        {
            "name": "tool1",
            "description": "First tool",
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "output_schema": {"type": "string"},
        },
        {
            "name": "tool2",
            "description": "Second tool",
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "output_schema": {"type": "string"},
        },
        {
            "name": "tool3",
            "description": "Third tool",
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "output_schema": {"type": "string"},
        },
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        # Only request specific tools
        tools = await client.as_langchain_tools(["tool1", "tool3"])

        # Should only get 2 tools
        assert len(tools) == 2
        assert tools[0].name == "tool1"
        assert tools[1].name == "tool3"

    await client.close()


@pytest.mark.asyncio
async def test_langchain_tool_type_mapping():
    """Test all JSON schema type mappings in LangChain tool conversion."""
    client = OliveClient("http://test.com")

    # Mock a tool with various types
    tools_data = [
        {
            "name": "complex_tool",
            "description": "Tool with various types",
            "input_schema": {
                "type": "object",
                "properties": {
                    "str_field": {"type": "string"},
                    "int_field": {"type": "integer"},
                    "float_field": {"type": "number"},
                    "bool_field": {"type": "boolean"},
                    "array_field": {"type": "array"},
                    "object_field": {"type": "object"},
                    "any_field": {},  # No type specified
                },
                "required": ["str_field", "int_field"],
            },
            "output_schema": {"type": "object"},
        }
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        tools = await client.as_langchain_tools()

        assert len(tools) == 1
        tool = tools[0]

        # Check the args schema was created properly
        # The args_schema is a dynamically created Pydantic model
        assert hasattr(tool.args_schema, "model_fields")
        schema_fields = tool.args_schema.model_fields
        assert "str_field" in schema_fields
        assert "int_field" in schema_fields
        assert "float_field" in schema_fields
        assert "bool_field" in schema_fields
        assert "array_field" in schema_fields
        assert "object_field" in schema_fields
        assert "any_field" in schema_fields

    await client.close()


@pytest.mark.asyncio
async def test_langchain_tool_with_defaults():
    """Test handling of fields with default values."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "tool_with_defaults",
            "description": "Tool with default values",
            "input_schema": {
                "type": "object",
                "properties": {
                    "required_field": {"type": "string"},
                    "optional_with_default": {"type": "integer", "default": 42},
                    "optional_no_default": {"type": "boolean"},
                },
                "required": ["required_field"],
            },
            "output_schema": {"type": "string"},
        }
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        tools = await client.as_langchain_tools()

        tool = tools[0]
        # The args_schema is a dynamically created Pydantic model
        assert hasattr(tool.args_schema, "model_fields")
        schema_fields = tool.args_schema.model_fields

        # Check defaults are handled properly
        assert schema_fields["required_field"].is_required()
        assert not schema_fields["optional_with_default"].is_required()
        assert schema_fields["optional_with_default"].default == 42
        assert not schema_fields["optional_no_default"].is_required()
        assert schema_fields["optional_no_default"].default is None

    await client.close()


@pytest.mark.asyncio
async def test_langchain_tool_sync_execution():
    """Test synchronous execution of LangChain tools."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "sync_tool",
            "description": "Test sync execution",
            "input_schema": {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]},
            "output_schema": {"type": "integer"},
        }
    ]

    # Mock responses
    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    call_response = Mock()
    call_response.json.return_value = {"success": True, "result": 42}
    call_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langchain_tools()
        tool = tools[0]

        # Test sync execution - mock the asyncio module to avoid event loop conflicts
        with patch.object(client._client, "post", return_value=call_response):
            with patch("asyncio.get_event_loop") as mock_get_loop:
                # Mock event loop
                mock_loop = Mock()
                mock_get_loop.return_value = mock_loop
                mock_loop.run_until_complete.return_value = 42

                # Call sync function
                result = tool.func(x=21)

                # Verify it used the event loop
                mock_get_loop.assert_called()
                mock_loop.run_until_complete.assert_called()
                assert result == 42

    await client.close()


@pytest.mark.asyncio
async def test_langchain_tool_async_execution():
    """Test async execution of LangChain tools."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "async_tool",
            "description": "Test async execution",
            "input_schema": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
            "output_schema": {"type": "string"},
        }
    ]

    # Mock responses
    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    call_response = Mock()
    call_response.json.return_value = {"success": True, "result": "Hello async!"}
    call_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langchain_tools()
        tool = tools[0]

        # Test async execution via coroutine
        with patch.object(client._client, "post", return_value=call_response):
            result = await tool.coroutine(message="test")
            assert result == "Hello async!"

    await client.close()


@pytest.mark.asyncio
async def test_sync_execution_new_event_loop():
    """Test sync execution when creating new event loop."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "sync_test",
            "description": "Test sync",
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "output_schema": {"type": "string"},
        }
    ]

    # Mock responses
    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    call_response = Mock()
    call_response.json.return_value = {"success": True, "result": "sync result"}
    call_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langchain_tools()
        tool = tools[0]

        # Test the path where get_event_loop raises RuntimeError
        with patch.object(client._client, "post", return_value=call_response):
            with patch("asyncio.get_event_loop") as mock_get_loop:
                # Simulate no current event loop - raises RuntimeError
                mock_get_loop.side_effect = RuntimeError()

                # Mock new_event_loop and set_event_loop
                with patch("asyncio.new_event_loop") as mock_new_loop:
                    with patch("asyncio.set_event_loop") as mock_set_loop:
                        mock_loop = Mock()
                        mock_new_loop.return_value = mock_loop
                        mock_loop.run_until_complete.return_value = "sync result"

                        # Call sync function
                        result = tool.func()

                        # Verify new loop was created
                        mock_new_loop.assert_called_once()
                        mock_set_loop.assert_called_once_with(mock_loop)
                        mock_loop.run_until_complete.assert_called()
                        assert result == "sync result"

    await client.close()
