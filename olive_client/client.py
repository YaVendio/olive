"""Olive client implementation."""

import types
from collections.abc import Callable, Mapping
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
        self._elevenlabs_context: dict[str, Any] | None = None  # Context for ElevenLabs tools

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

    async def get_tools(self, profile: str | None = None) -> list[dict[str, Any]]:
        """
        Get list of available tools from the server.

        Args:
            profile: Optional profile name to filter tools (e.g., "javi", "clamy").
                    If None, returns all tools.

        Returns:
            List of tool definitions with name, description, and schemas
        """
        params = {"profile": profile} if profile else {}
        response = await self._client.get(f"{self.base_url}/olive/tools", params=params)
        response.raise_for_status()
        return response.json()

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """
        Call a tool on the server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            context: Runtime context for injection (e.g., assistant_id, phone_number).
                    If None and _elevenlabs_context is set, uses that instead.

        Returns:
            The result from the tool execution

        Raises:
            Exception: If the tool call fails
        """
        if arguments is None:
            arguments = {}

        # Use provided context if explicitly passed (even if empty), otherwise fall back to ElevenLabs context.
        # This distinguishes "not provided" (None) from "explicitly empty" ({}).
        effective_context = context if context is not None else self._elevenlabs_context

        payload: dict[str, Any] = {"tool_name": tool_name, "arguments": arguments}
        if effective_context:
            payload["context"] = effective_context

        response = await self._client.post(f"{self.base_url}/olive/tools/call", json=payload)
        response.raise_for_status()

        data = response.json()
        if not data["success"]:
            raise Exception(f"Tool call failed: {data.get('error', 'Unknown error')}")

        return data["result"]

    async def as_langchain_tools(
        self,
        tool_names: list[str] | None = None,
        profile: str | None = None,
    ) -> list[StructuredTool]:
        """
        Convert Olive tools to LangChain tools.

        Args:
            tool_names: Optional list of specific tool names to convert.
                       If None, converts all available tools.
            profile: Optional profile name to filter tools (e.g., "javi", "clamy").

        Returns:
            List of LangChain StructuredTool instances
        """
        # Get tools (optionally filtered by profile)
        tools_info = await self.get_tools(profile=profile)

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

    async def as_langchain_tools_injecting(
        self,
        context_provider: Callable[[Any | None], Mapping[str, Any]] | None = None,
        tool_names: list[str] | None = None,
        profile: str | None = None,
    ) -> list[StructuredTool]:
        """
        Convert Olive tools to LangChain tools and auto-inject context values into declared injections.

        Args:
            context_provider: Callable that receives LangChain RunnableConfig (or None) and returns
                              a mapping (e.g., config.configurable) used for injection.
            tool_names: Optional list of tool names to include.
            profile: Optional profile name to filter tools (e.g., "javi", "clamy").
        """
        tools_info = await self.get_tools(profile=profile)
        if tool_names:
            tools_info = [t for t in tools_info if t["name"] in tool_names]

        langchain_tools: list[StructuredTool] = []

        for tool_info in tools_info:
            tool_name = tool_info["name"]

            # Build args schema excluding injected params (already excluded by server schema)
            properties = tool_info.get("input_schema", {}).get("properties", {})
            required = tool_info.get("input_schema", {}).get("required", [])

            field_definitions = {}
            for field_name, field_info in properties.items():
                field_type = Any
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

                if field_name not in required:
                    if "default" in field_info:
                        field_definitions[field_name] = (field_type, field_info["default"])
                    else:
                        field_definitions[field_name] = (field_type | None, None)
                else:
                    field_definitions[field_name] = (field_type, ...)

            ArgsSchema = create_model(f"{tool_name}_args", **field_definitions)

            injections = tool_info.get("injections", [])

            async def bound_acall(__tool_name: str = tool_name, __injections=injections, **kwargs: Any) -> Any:
                # Extract context for injection
                cfg_map: Mapping[str, Any] = {}
                if context_provider is not None:
                    try:
                        # Import lazily to avoid hard dep at import time
                        from langchain_core.runnables.config import get_config

                        cfg = get_config()
                    except Exception:
                        cfg = None
                    cfg_map = context_provider(cfg) or {}

                # Pass context to the server for server-side injection
                return await self.call_tool(__tool_name, kwargs, context=dict(cfg_map) if cfg_map else None)

            def bound_call(__tool_name: str = tool_name, **kwargs: Any) -> Any:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                return loop.run_until_complete(bound_acall(__tool_name=__tool_name, **kwargs))

            tool = StructuredTool(
                name=tool_name,
                description=tool_info["description"],
                func=bound_call,
                coroutine=bound_acall,
                args_schema=ArgsSchema,
            )
            langchain_tools.append(tool)

        return langchain_tools

    async def as_langgraph_tools(
        self,
        tool_names: list[str] | None = None,
        profile: str | None = None,
    ) -> list[StructuredTool]:
        """
        Convert Olive tools to LangChain tools with LangGraph ToolRuntime injection.

        This method creates tools that properly integrate with LangGraph's ToolRuntime,
        automatically extracting injection values from runtime.context.

        Args:
            tool_names: Optional list of specific tool names to convert.
            profile: Optional profile name to filter tools (e.g., "javi", "clamy").

        Returns:
            List of LangChain StructuredTool instances with ToolRuntime injection.

        Raises:
            ValueError: If tool inputs contain reserved names ('config', 'runtime').

        Example:
            ```python
            client = OliveClient("http://localhost:8000")
            tools = await client.as_langgraph_tools(profile="javi")

            # Use with LangGraph's create_agent
            graph = create_agent(
                model=llm,
                tools=tools,
                context_schema=AppContext,  # Must include injection keys
            )
            ```
        """
        from typing import Annotated

        from langchain_core.tools import InjectedToolArg

        # Import ToolRuntime - try multiple locations for compatibility
        # Note: The actual ToolRuntime type is only used at runtime for isinstance checks
        # if needed. The function signature uses Annotated[Any, InjectedToolArg] to satisfy
        # the type checker while LangChain's InjectedToolArg handles the runtime behavior.
        try:
            from langgraph.prebuilt.tool_node import ToolRuntime  # noqa: F401
        except ImportError:
            try:
                # Fallback for newer LangChain/LangGraph versions
                from langchain.tools import ToolRuntime  # type: ignore[import-not-found,no-redef] # noqa: F401
            except ImportError:
                raise ImportError(
                    "langgraph is required for as_langgraph_tools(). "
                    "Install it with: pip install langgraph"
                )

        # Reserved parameter names that conflict with LangChain internals
        RESERVED_NAMES = {"config", "runtime"}

        tools_info = await self.get_tools(profile=profile)
        if tool_names:
            tools_info = [t for t in tools_info if t["name"] in tool_names]

        langchain_tools: list[StructuredTool] = []

        for tool_info in tools_info:
            tool_name = tool_info["name"]
            description = tool_info.get("description", f"Tool: {tool_name}")
            injections = tool_info.get("injections", [])

            # Build injection mapping: param -> config_key
            injection_map = {inj["param"]: inj["config_key"] for inj in injections}
            required_injections = {
                inj["param"]: inj["config_key"]
                for inj in injections
                if inj.get("required", True)
            }
            injected_params = set(injection_map.keys())

            # Build args schema excluding injected params
            properties = tool_info.get("input_schema", {}).get("properties", {})
            required = set(tool_info.get("input_schema", {}).get("required", []))

            # Validate no reserved names
            for prop_name in properties:
                if prop_name in RESERVED_NAMES:
                    raise ValueError(
                        f"Tool '{tool_name}' has reserved parameter '{prop_name}'. "
                        "Rename it to avoid conflicts with LangChain internals."
                    )

            field_definitions: dict[str, Any] = {}
            for field_name, field_info in properties.items():
                # Skip injected params - they come from runtime.context
                if field_name in injected_params:
                    continue

                field_type: Any = Any
                json_type = field_info.get("type", "string")
                if json_type == "string":
                    field_type = str
                elif json_type == "integer":
                    field_type = int
                elif json_type == "number":
                    field_type = float
                elif json_type == "boolean":
                    field_type = bool
                elif json_type == "array":
                    field_type = list[Any]
                elif json_type == "object":
                    field_type = dict[str, Any]

                if field_name not in required:
                    if "default" in field_info:
                        field_definitions[field_name] = (field_type, field_info["default"])
                    else:
                        field_definitions[field_name] = (field_type | None, None)
                else:
                    field_definitions[field_name] = (field_type, ...)

            ArgsSchema = create_model(f"{tool_name}_args", **field_definitions)

            # Create a factory function to properly capture loop variables by value.
            # This avoids the late-binding closure bug where all tools would reference
            # the last iteration's values.
            def make_bound_acall(
                tool_name_: str,
                injection_map_: dict[str, str],
                required_injections_: dict[str, str],
            ) -> Any:
                """Factory to create tool execution function with captured values."""

                async def bound_acall(
                    *,  # All parameters are keyword-only
                    runtime: Annotated[Any, InjectedToolArg],  # ToolRuntime, hidden from model
                    **kwargs: Any,
                ) -> Any:
                    """Execute the tool with context injection from ToolRuntime."""
                    # Extract context from LangGraph runtime
                    ctx = getattr(runtime, "context", None)
                    olive_context: dict[str, Any] = {}

                    # Helper to get value from context (supports both object attributes and dict/Mapping)
                    def get_context_value(context: Any, key: str) -> Any:
                        if context is None:
                            return None
                        # Try dict/Mapping access first (more common in runtime contexts)
                        if isinstance(context, Mapping):
                            return context.get(key)
                        # Fall back to attribute access (dataclass/Pydantic models)
                        return getattr(context, key, None)

                    # Extract injection values and validate required ones
                    for param, config_key in injection_map_.items():
                        value = get_context_value(ctx, config_key)
                        if value is not None:
                            olive_context[config_key] = value
                        elif param in required_injections_:
                            # Raise error for missing required injection (even if ctx is None)
                            raise ValueError(
                                f"Tool '{tool_name_}' requires '{config_key}' in runtime.context "
                                f"but it was not provided. Ensure your context_schema includes this field."
                            )

                    # Pass context explicitly (even if empty) to prevent ElevenLabs context fallback.
                    # Empty dict {} means "no context", while None means "use default fallback".
                    return await self.call_tool(tool_name_, kwargs, context=olive_context)

                # Set function metadata
                bound_acall.__name__ = tool_name_
                bound_acall.__doc__ = f"Execute {tool_name_} with context injection from ToolRuntime."
                return bound_acall

            # Create the async callable with captured values
            bound_acall = make_bound_acall(tool_name, injection_map, required_injections)

            # Create a sync wrapper that runs the async function in an event loop.
            # This is needed because StructuredTool.from_function requires a sync func
            # for the synchronous execution path.
            # IMPORTANT: The sync wrapper must also declare the runtime parameter with
            # InjectedToolArg so LangChain properly injects it during sync execution.
            def make_sync_wrapper(acall: Any, tool_name_: str, description_: str) -> Any:
                def sync_call(
                    *,
                    runtime: Annotated[Any, InjectedToolArg],  # Must match async signature
                    **kwargs: Any,
                ) -> Any:
                    import asyncio

                    # Check if we're in an async context (Jupyter, already-running loop)
                    try:
                        running_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        running_loop = None

                    if running_loop is not None:
                        # We're inside an async context - can't use run_until_complete
                        raise RuntimeError(
                            f"Cannot execute tool '{tool_name_}' synchronously from within an async context. "
                            "Use 'await tool.ainvoke(...)' or 'await tool.coroutine(...)' instead."
                        )

                    # No running loop - safe to create/use one
                    loop = None
                    created_loop = False
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            raise RuntimeError("Event loop is closed")
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        created_loop = True

                    try:
                        return loop.run_until_complete(acall(runtime=runtime, **kwargs))
                    finally:
                        # Clean up if we created a new loop
                        if created_loop and loop is not None:
                            loop.close()

                sync_call.__name__ = tool_name_
                sync_call.__doc__ = description_
                return sync_call

            sync_func = make_sync_wrapper(bound_acall, tool_name, description)

            tool = StructuredTool.from_function(
                func=sync_func,
                name=tool_name,
                description=description,
                args_schema=ArgsSchema,
                coroutine=bound_acall,
            )
            langchain_tools.append(tool)

        return langchain_tools

    async def as_elevenlabs_tools(
        self,
        tool_names: list[str] | None = None,
        tool_type: str = "client",
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get Olive tools in ElevenLabs Agents Platform format.

        Uses the /olive/tools/elevenlabs endpoint which formats tools correctly.

        Args:
            tool_names: Optional list of specific tool names to include.
                       If None, returns all available tools.
            tool_type: Tool type for ElevenLabs ("client", "webhook", "system", "mcp")
            context: Optional context dict to store for later injection during tool calls
                    (e.g., {"phone_number": "...", "assistant_id": "..."})

        Returns:
            List of tool definitions in ElevenLabs ClientToolConfig format:
            {
                "type": "client",
                "name": "tool_name",
                "description": "...",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                },
                "expects_response": true
            }

        Note:
            - The context parameter is stored internally for automatic injection during call_tool()
            - Parameters use ObjectJsonSchemaProperty format (clean JSON Schema without additionalProperties)
            - Injected parameters (via Inject) are automatically excluded from the parameters schema
            - All tools include expects_response: true by default
        """
        # Store context for later use in call_tool
        if context:
            self._elevenlabs_context = context

        # Use the dedicated ElevenLabs endpoint
        response = await self._client.get(
            f"{self.base_url}/olive/tools/elevenlabs",
            params={"tool_type": tool_type},
        )
        response.raise_for_status()
        tools = response.json()

        # Filter by tool names if specified
        if tool_names:
            tools = [t for t in tools if t["name"] in tool_names]

        return tools
