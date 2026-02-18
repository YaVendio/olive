"""Tests for thread safety of ToolRegistry."""

import threading

import pytest

from olive.registry import ToolRegistry
from olive.schemas import ToolInfo


def _make_tool(name: str) -> ToolInfo:
    """Create a minimal ToolInfo for testing."""
    return ToolInfo(
        name=name,
        description=f"Test tool {name}",
        input_schema={"type": "object", "properties": {}, "required": []},
        output_schema={"type": "object"},
        func=lambda: None,
    )


def test_concurrent_register():
    """50 threads each register a unique tool — all should succeed."""
    registry = ToolRegistry()
    errors: list[Exception] = []
    count = 50

    def register(i: int):
        try:
            registry.register(_make_tool(f"tool_{i}"))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=register, args=(i,)) for i in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(registry.list_all()) == count


def test_concurrent_register_duplicate():
    """10 threads all try to register the same name — exactly 1 succeeds."""
    registry = ToolRegistry()
    successes = []
    failures = []

    def register():
        try:
            registry.register(_make_tool("duplicate"))
            successes.append(True)
        except ValueError:
            failures.append(True)

    threads = [threading.Thread(target=register) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) == 1
    assert len(failures) == 9


def test_concurrent_list_during_register():
    """Register tools while another thread calls list_all() — no RuntimeError."""
    registry = ToolRegistry()
    errors: list[Exception] = []

    def register_tools():
        for i in range(100):
            try:
                registry.register(_make_tool(f"tool_{i}"))
            except Exception as e:
                errors.append(e)

    def list_tools():
        for _ in range(200):
            try:
                tools = registry.list_all()
                assert isinstance(tools, list)
            except Exception as e:
                errors.append(e)

    t1 = threading.Thread(target=register_tools)
    t2 = threading.Thread(target=list_tools)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(errors) == 0


def test_list_all_returns_snapshot():
    """list_all() returns a snapshot — later registrations don't affect it."""
    registry = ToolRegistry()
    registry.register(_make_tool("tool_a"))
    registry.register(_make_tool("tool_b"))

    snapshot = registry.list_all()
    assert len(snapshot) == 2

    registry.register(_make_tool("tool_c"))
    assert len(snapshot) == 2  # snapshot unchanged
    assert len(registry.list_all()) == 3
