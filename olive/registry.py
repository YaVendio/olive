"""Tool registry for storing olive tools."""

import threading

from olive.schemas import ToolInfo


class ToolRegistry:
    """Registry for storing and managing olive tools.

    Thread-safe: all access to the internal dict is guarded by a lock.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolInfo] = {}
        self._lock = threading.Lock()

    def register(self, tool_info: ToolInfo) -> None:
        """Register a new tool."""
        with self._lock:
            if tool_info.name in self._tools:
                raise ValueError(f"Tool '{tool_info.name}' is already registered")
            self._tools[tool_info.name] = tool_info

    def get(self, name: str) -> ToolInfo | None:
        """Get a tool by name."""
        with self._lock:
            return self._tools.get(name)

    def list_all(self) -> list[ToolInfo]:
        """List all registered tools."""
        with self._lock:
            return list(self._tools.values())

    def clear(self) -> None:
        """Clear all registered tools."""
        with self._lock:
            self._tools.clear()


# Global registry instance
_registry = ToolRegistry()
