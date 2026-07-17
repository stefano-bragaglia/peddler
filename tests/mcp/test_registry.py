import pytest

from peddler.mcp.registry import ToolRegistry


def _noop(arguments: dict) -> dict:
    return {}


def test_register_then_get_returns_matching_spec():
    registry = ToolRegistry()
    registry.register("greet", "says hello", {"type": "object"}, _noop)

    spec = registry.get("greet")

    assert spec.name == "greet"
    assert spec.description == "says hello"
    assert spec.parameters_schema == {"type": "object"}
    assert spec.handler is _noop


def test_get_unregistered_name_returns_none():
    registry = ToolRegistry()

    assert registry.get("missing") is None


def test_register_duplicate_name_raises_and_keeps_original():
    registry = ToolRegistry()
    registry.register("greet", "first", {"type": "object"}, _noop)

    with pytest.raises(ValueError):
        registry.register("greet", "second", {"type": "object"}, _noop)

    assert registry.get("greet").description == "first"


def test_list_tools_empty_returns_empty_list():
    registry = ToolRegistry()

    assert registry.list_tools() == []


def test_list_tools_after_registering_two_returns_both_in_order():
    registry = ToolRegistry()
    registry.register("first", "first tool", {"type": "object"}, _noop)
    registry.register("second", "second tool", {"type": "object"}, _noop)

    assert registry.list_tools() == [
        {"name": "first", "description": "first tool", "inputSchema": {"type": "object"}},
        {"name": "second", "description": "second tool", "inputSchema": {"type": "object"}},
    ]
