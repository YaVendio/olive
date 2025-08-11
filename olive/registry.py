"""Tool registry for storing olive tools."""

from olive.schemas import ToolInfo


class ToolRegistry:
    """Registry for storing and managing olive tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolInfo] = {}

    def register(self, tool_info: ToolInfo) -> None:
        """Register a new tool."""
        if tool_info.name in self._tools:
            raise ValueError(f"Tool '{tool_info.name}' is already registered")
        self._tools[tool_info.name] = tool_info

    def get(self, name: str) -> ToolInfo | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_all(self) -> list[ToolInfo]:
        """List all registered tools."""
        return list(self._tools.values())

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


# Global registry instance
_registry = ToolRegistry()
