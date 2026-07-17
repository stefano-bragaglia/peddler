"""In-memory registry mapping tool names to their schema and handler."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    """A registered tool's name, description, parameter schema, and handler."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """Registers tools and looks them up by name."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Register a tool under a unique name.

        :param name: The tool's unique name.
        :type name: str
        :param description: A human-readable description of the tool.
        :type description: str
        :param parameters_schema: The JSON Schema for the tool's arguments.
        :type parameters_schema: dict[str, Any]
        :param handler: The callable invoked with the tool's arguments.
        :type handler: Callable[[dict[str, Any]], dict[str, Any]]
        :raises ValueError: If a tool is already registered under ``name``.
        """
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = ToolSpec(name, description, parameters_schema, handler)

    def get(self, name: str) -> ToolSpec | None:
        """Look up a registered tool by name.

        :param name: The tool's name.
        :type name: str
        :returns: The tool's spec, or ``None`` if no tool is registered
            under that name.
        :rtype: ToolSpec | None
        """
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List every registered tool in MCP ``tools/list`` result format.

        :returns: One dict per registered tool, each with ``name``,
            ``description``, and ``inputSchema`` keys.
        :rtype: list[dict[str, Any]]
        """
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "inputSchema": spec.parameters_schema,
            }
            for spec in self._tools.values()
        ]
