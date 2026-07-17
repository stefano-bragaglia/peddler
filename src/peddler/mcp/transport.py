"""stdio-based JSON-line transport for the MCP server."""

import json
from typing import Any, TextIO


class TransportError(Exception):
    """Raised when a message read from stdin cannot be parsed."""


class Transport:
    """Reads and writes newline-delimited JSON objects over stdio."""

    def __init__(self, stdin: TextIO, stdout: TextIO) -> None:
        self._stdin = stdin
        self._stdout = stdout

    def read_message(self) -> dict[str, Any] | None:
        while True:
            line = self._stdin.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TransportError(f"invalid JSON: {exc}") from exc
            if not isinstance(message, dict):
                raise TransportError("message must be a JSON object")
            return message

    def write_message(self, message: dict[str, Any]) -> None:
        self._stdout.write(json.dumps(message) + "\n")
