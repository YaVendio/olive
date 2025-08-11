"""Olive client implementation."""

import types
from typing import Any

import httpx
from langchain_core.tools import StructuredTool
from pydantic import create_model


class OliveClient:
    """Client for connecting to Olive-enabled FastAPI servers."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize the Olive client.

        Args:
            base_url: Base URL of the Olive-enabled server (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_tools(self) -> list[dict[str, Any]]:
        """
        Get list of all available tools from the server.

        Returns:
            List of tool definitions with name, description, and schemas
        """
        response = await self._client.get(f"{self.base_url}/olive/tools")
        response.raise_for_status()
        return response.json()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """
        Call a tool on the server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            The result from the tool execution

        Raises:
            Exception: If the tool call fails
        """
        if arguments is None:
            arguments = {}

        response = await self._client.post(
            f"{self.base_url}/olive/tools/call", json={"tool_name": tool_name, "arguments": arguments}
        )
        response.raise_for_status()

        data = response.json()
        if not data["success"]:
            raise Exception(f"Tool call failed: {data.get('error', 'Unknown error')}")

        return data["result"]

    async def as_langchain_tools(self, tool_names: list[str] | None = None) -> list[StructuredTool]:
        """
        Convert Olive tools to LangChain tools.

        Args:
            tool_names: Optional list of specific tool names to convert.
                       If None, converts all available tools.

        Returns:
            List of LangChain StructuredTool instances
        """
        # Get all tools
        tools_info = await self.get_tools()

        # Filter by tool names if specified
        if tool_names:
            tools_info = [t for t in tools_info if t["name"] in tool_names]

        # Convert to LangChain tools
        langchain_tools = []

        for tool_info in tools_info:
            # Create a function that calls the remote tool
            tool_name = tool_info["name"]

            # Create args schema from input schema
            properties = tool_info["input_schema"].get("properties", {})
            required = tool_info["input_schema"].get("required", [])

            # Create a Pydantic model dynamically
            field_definitions = {}
            for field_name, field_info in properties.items():
                field_type = Any  # Default to Any

                # Map JSON schema types to Python types
                if field_info.get("type") == "string":
                    field_type = str
                elif field_info.get("type") == "integer":
                    field_type = int
                elif field_info.get("type") == "number":
                    field_type = float
                elif field_info.get("type") == "boolean":
                    field_type = bool
                elif field_info.get("type") == "array":
                    field_type = list[Any]
                elif field_info.get("type") == "object":
                    field_type = dict[str, Any]

                # Handle optional fields and defaults
                if field_name not in required:
                    if "default" in field_info:
                        field_definitions[field_name] = (field_type, field_info["default"])
                    else:
                        field_definitions[field_name] = (field_type | None, None)
                else:
                    field_definitions[field_name] = (field_type, ...)

            # Create the Pydantic model using create_model
            ArgsSchema = create_model(f"{tool_name}_args", **field_definitions)

            # Bind tool name at definition time to avoid late-binding in closures
            async def bound_acall(__tool_name: str = tool_name, **kwargs: Any) -> Any:
                return await self.call_tool(__tool_name, kwargs)

            def bound_call(__tool_name: str = tool_name, **kwargs: Any) -> Any:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                return loop.run_until_complete(self.call_tool(__tool_name, kwargs))

            # Create the LangChain tool
            tool = StructuredTool(
                name=tool_name,
                description=tool_info["description"],
                func=bound_call,
                coroutine=bound_acall,
                args_schema=ArgsSchema,
            )

            langchain_tools.append(tool)

        return langchain_tools
