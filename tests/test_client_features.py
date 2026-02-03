"""Test client features and edge cases."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from olive_client import OliveClient


@pytest.mark.asyncio
async def test_get_tools_with_profile():
    """Test filtering tools by profile via get_tools."""
    client = OliveClient("http://test.com")

    mock_response = Mock()
    mock_response.json.return_value = [
        {"name": "javi_tool", "description": "Javi tool", "input_schema": {"type": "object", "properties": {}}},
    ]
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response) as mock_get:
        tools = await client.get_tools(profile="javi")

        # Verify profile query parameter was sent
        mock_get.assert_called_once_with("http://test.com/olive/tools", params={"profile": "javi"})
        assert len(tools) == 1
        assert tools[0]["name"] == "javi_tool"

    await client.close()


@pytest.mark.asyncio
async def test_get_tools_without_profile():
    """Test get_tools without profile returns all tools."""
    client = OliveClient("http://test.com")

    mock_response = Mock()
    mock_response.json.return_value = [
        {"name": "tool1", "description": "Tool 1", "input_schema": {"type": "object", "properties": {}}},
        {"name": "tool2", "description": "Tool 2", "input_schema": {"type": "object", "properties": {}}},
    ]
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response) as mock_get:
        tools = await client.get_tools()

        # Verify no profile parameter
        mock_get.assert_called_once_with("http://test.com/olive/tools", params={})
        assert len(tools) == 2

    await client.close()


@pytest.mark.asyncio
async def test_as_langchain_tools_with_profile():
    """Test as_langchain_tools with profile filtering."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "javi_tool",
            "description": "Tool for Javi",
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "output_schema": {"type": "string"},
        },
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response) as mock_get:
        tools = await client.as_langchain_tools(profile="javi")

        # Verify profile was passed
        mock_get.assert_called_once_with("http://test.com/olive/tools", params={"profile": "javi"})
        assert len(tools) == 1
        assert tools[0].name == "javi_tool"

    await client.close()


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


# ============================================================================
# as_langgraph_tools tests
# ============================================================================


@pytest.mark.asyncio
async def test_as_langgraph_tools_basic():
    """Test as_langgraph_tools returns LangChain tools with ToolRuntime injection."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "simple_tool",
            "description": "A simple tool",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "injections": [],
        },
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        tools = await client.as_langgraph_tools()

        assert len(tools) == 1
        assert tools[0].name == "simple_tool"
        assert tools[0].description == "A simple tool"

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_with_profile():
    """Test as_langgraph_tools with profile filtering."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "javi_tool",
            "description": "Tool for Javi",
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "injections": [],
        },
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response) as mock_get:
        tools = await client.as_langgraph_tools(profile="javi")

        mock_get.assert_called_once_with("http://test.com/olive/tools", params={"profile": "javi"})
        assert len(tools) == 1
        assert tools[0].name == "javi_tool"

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_reserved_name_validation():
    """Test that as_langgraph_tools raises error for reserved parameter names."""
    client = OliveClient("http://test.com")

    # Tool with reserved parameter name "config"
    tools_data = [
        {
            "name": "bad_tool",
            "description": "Tool with reserved param",
            "input_schema": {
                "type": "object",
                "properties": {"config": {"type": "string"}},  # Reserved name!
                "required": ["config"],
            },
            "injections": [],
        },
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        with pytest.raises(ValueError) as exc_info:
            await client.as_langgraph_tools()

        assert "reserved parameter 'config'" in str(exc_info.value)

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_reserved_runtime_validation():
    """Test that as_langgraph_tools raises error for 'runtime' parameter name."""
    client = OliveClient("http://test.com")

    # Tool with reserved parameter name "runtime"
    tools_data = [
        {
            "name": "bad_tool",
            "description": "Tool with reserved param",
            "input_schema": {
                "type": "object",
                "properties": {"runtime": {"type": "object"}},  # Reserved name!
                "required": [],
            },
            "injections": [],
        },
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        with pytest.raises(ValueError) as exc_info:
            await client.as_langgraph_tools()

        assert "reserved parameter 'runtime'" in str(exc_info.value)

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_excludes_injected_params_from_schema():
    """Test that injected params are excluded from the tool's args schema."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "injected_tool",
            "description": "Tool with injection",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "case_id": {"type": "string"},  # This should be excluded
                },
                "required": ["query", "case_id"],
            },
            "injections": [
                {"param": "case_id", "config_key": "case_id", "required": True},
            ],
        },
    ]

    mock_response = Mock()
    mock_response.json.return_value = tools_data
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        tools = await client.as_langgraph_tools()

        assert len(tools) == 1
        tool = tools[0]

        # Check that case_id is NOT in the args schema (it's injected)
        schema_fields = tool.args_schema.model_fields
        assert "query" in schema_fields
        assert "case_id" not in schema_fields  # Should be excluded

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_context_injection():
    """Test that ToolRuntime context is properly extracted for injection."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "context_tool",
            "description": "Tool that needs context",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "user_id": {"type": "string"},
                },
                "required": ["query", "user_id"],
            },
            "injections": [
                {"param": "user_id", "config_key": "user_id", "required": True},
            ],
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    call_response = Mock()
    call_response.json.return_value = {"success": True, "result": "success"}
    call_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()
        tool = tools[0]

        # Create a mock runtime with context
        class MockContext:
            user_id = "user-123"

        class MockRuntime:
            context = MockContext()

        # Call the tool with runtime
        with patch.object(client._client, "post", return_value=call_response) as mock_post:
            result = await tool.coroutine(runtime=MockRuntime(), query="test query")

            # Verify the context was included in the call
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["context"] == {"user_id": "user-123"}
            assert payload["arguments"] == {"query": "test query"}
            assert result == "success"

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_missing_required_injection():
    """Test that missing required injection raises a clear error."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "context_tool",
            "description": "Tool that needs context",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "injections": [
                {"param": "user_id", "config_key": "user_id", "required": True},
            ],
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()
        tool = tools[0]

        # Create a mock runtime with MISSING user_id
        class MockContext:
            # user_id is missing!
            pass

        class MockRuntime:
            context = MockContext()

        # Call should raise error about missing context
        with pytest.raises(ValueError) as exc_info:
            await tool.coroutine(runtime=MockRuntime(), query="test")

        assert "user_id" in str(exc_info.value)
        assert "runtime.context" in str(exc_info.value)

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_optional_injection():
    """Test that optional injections don't fail when missing."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "optional_tool",
            "description": "Tool with optional injection",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "injections": [
                {"param": "user_id", "config_key": "user_id", "required": False},  # Optional!
            ],
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    call_response = Mock()
    call_response.json.return_value = {"success": True, "result": "ok"}
    call_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()
        tool = tools[0]

        # Create a mock runtime WITHOUT user_id
        class MockContext:
            pass

        class MockRuntime:
            context = MockContext()

        # Call should NOT raise error because injection is optional
        with patch.object(client._client, "post", return_value=call_response) as mock_post:
            result = await tool.coroutine(runtime=MockRuntime(), query="test")

            # Context should be None (empty dict is converted to None to avoid fallback)
            payload = mock_post.call_args[1]["json"]
            assert "context" not in payload  # None context is not included in payload
            assert result == "ok"

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_missing_required_with_none_context():
    """Test that missing required injection raises error even when context is None."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "required_tool",
            "description": "Tool with required injection",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "injections": [
                {"param": "user_id", "config_key": "user_id", "required": True},
            ],
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()
        tool = tools[0]

        # Create a mock runtime with context=None
        class MockRuntime:
            context = None

        # Should raise error even though context is None
        with pytest.raises(ValueError) as exc_info:
            await tool.coroutine(runtime=MockRuntime(), query="test")

        assert "user_id" in str(exc_info.value)
        assert "runtime.context" in str(exc_info.value)

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_dict_context():
    """Test that dict/Mapping context is supported (not just attribute access)."""
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "dict_context_tool",
            "description": "Tool with dict context",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "injections": [
                {"param": "user_id", "config_key": "user_id", "required": True},
            ],
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    call_response = Mock()
    call_response.json.return_value = {"success": True, "result": "dict works"}
    call_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()
        tool = tools[0]

        # Create a mock runtime with dict context (common in LangGraph)
        class MockRuntime:
            context = {"user_id": "dict-user-456"}  # Dict instead of object

        with patch.object(client._client, "post", return_value=call_response) as mock_post:
            result = await tool.coroutine(runtime=MockRuntime(), query="test")

            # Verify dict context was properly extracted
            payload = mock_post.call_args[1]["json"]
            assert payload["context"] == {"user_id": "dict-user-456"}
            assert result == "dict works"

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_multi_tool_closure():
    """Test that multiple tools don't share the same closure variables (late-binding bug)."""
    client = OliveClient("http://test.com")

    # Two tools with different injections
    tools_data = [
        {
            "name": "tool_one",
            "description": "First tool",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "injections": [
                {"param": "user_id", "config_key": "user_id", "required": True},
            ],
        },
        {
            "name": "tool_two",
            "description": "Second tool",
            "input_schema": {
                "type": "object",
                "properties": {"data": {"type": "string"}},
                "required": ["data"],
            },
            "injections": [
                {"param": "company_id", "config_key": "company_id", "required": True},
            ],
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()

        assert len(tools) == 2
        # Verify each tool has the correct name (not the last one)
        assert tools[0].name == "tool_one"
        assert tools[1].name == "tool_two"

        # Test that tool_one requires user_id (not company_id)
        class MockRuntimeOne:
            context = {"company_id": "comp-123"}  # Has company_id but NOT user_id

        with pytest.raises(ValueError) as exc_info:
            await tools[0].coroutine(runtime=MockRuntimeOne(), query="test")
        assert "user_id" in str(exc_info.value)  # Should require user_id, not company_id

        # Test that tool_two requires company_id (not user_id)
        class MockRuntimeTwo:
            context = {"user_id": "user-123"}  # Has user_id but NOT company_id

        with pytest.raises(ValueError) as exc_info:
            await tools[1].coroutine(runtime=MockRuntimeTwo(), data="test")
        assert "company_id" in str(exc_info.value)  # Should require company_id, not user_id

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_sync_execution():
    """Test sync execution of as_langgraph_tools with runtime injection.

    Verifies that the sync wrapper properly accepts the runtime parameter
    and delegates to the async implementation via run_until_complete.
    """
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "sync_langgraph_tool",
            "description": "Tool for sync execution test",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "injections": [
                {"param": "user_id", "config_key": "user_id", "required": True},
            ],
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()
        tool = tools[0]

        # Create a mock runtime with context
        class MockRuntime:
            context = {"user_id": "sync-user-789"}

        # Test sync execution via func - mock the event loop to capture the call
        with patch("asyncio.get_running_loop", side_effect=RuntimeError("no running loop")):
            with patch("asyncio.get_event_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_get_loop.return_value = mock_loop
                mock_loop.is_closed.return_value = False
                mock_loop.run_until_complete.return_value = "sync success"

                # Call the sync func with runtime parameter
                result = tool.func(runtime=MockRuntime(), query="sync test")

                # Verify run_until_complete was called (sync path used)
                mock_loop.run_until_complete.assert_called_once()

                # Verify the coroutine passed to run_until_complete has the right signature
                # (it should be a coroutine that accepts runtime and kwargs)
                call_args = mock_loop.run_until_complete.call_args
                coro = call_args[0][0]
                # Coroutine should be the bound_acall function
                assert hasattr(coro, "cr_code")  # It's a coroutine

                assert result == "sync success"

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_sync_wrapper_has_runtime_param():
    """Test that the sync wrapper func accepts the runtime parameter.

    This verifies the fix for the bug where the sync wrapper didn't
    declare the runtime parameter, causing signature mismatch.
    """
    client = OliveClient("http://test.com")

    tools_data = [
        {
            "name": "sync_param_tool",
            "description": "Tool for param test",
            "input_schema": {
                "type": "object",
                "properties": {"data": {"type": "string"}},
                "required": ["data"],
            },
            "injections": [
                {"param": "tenant_id", "config_key": "tenant_id", "required": False},
            ],
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()
        tool = tools[0]

        # Inspect the sync func signature - it should accept 'runtime' as a parameter
        import inspect

        sig = inspect.signature(tool.func)
        param_names = list(sig.parameters.keys())

        # The sync wrapper should have 'runtime' in its signature
        assert "runtime" in param_names, f"Expected 'runtime' in params, got: {param_names}"

    await client.close()


@pytest.mark.asyncio
async def test_as_langgraph_tools_no_elevenlabs_fallback():
    """Test that empty context doesn't fall back to ElevenLabs context."""
    client = OliveClient("http://test.com")

    # Set ElevenLabs context that should NOT be used
    client._elevenlabs_context = {"phone_number": "555-1234", "assistant_id": "elevenlabs-123"}

    tools_data = [
        {
            "name": "no_fallback_tool",
            "description": "Tool without injections",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "injections": [],  # No injections
        },
    ]

    get_response = Mock()
    get_response.json.return_value = tools_data
    get_response.raise_for_status = Mock()

    call_response = Mock()
    call_response.json.return_value = {"success": True, "result": "no leak"}
    call_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=get_response):
        tools = await client.as_langgraph_tools()
        tool = tools[0]

        class MockRuntime:
            context = {}  # Empty context

        with patch.object(client._client, "post", return_value=call_response) as mock_post:
            result = await tool.coroutine(runtime=MockRuntime(), query="test")

            # Verify ElevenLabs context was NOT leaked into the call
            payload = mock_post.call_args[1]["json"]
            assert "context" not in payload  # None/empty context should not include context key
            assert result == "no leak"

    await client.close()
