"""In-memory registry mapping tool names to their schema and handler."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """Registers tools and looks them up by name."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = ToolSpec(name, description, parameters_schema, handler)

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "inputSchema": spec.parameters_schema,
            }
            for spec in self._tools.values()
        ]
