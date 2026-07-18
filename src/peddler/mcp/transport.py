"""stdio-based JSON-line transport for the MCP server."""

import json
from typing import Any, TextIO


class TransportError(Exception):
    """Raised when a message read from stdin cannot be parsed."""


class Transport:
    """Reads and writes newline-delimited JSON objects over stdio."""

    def __init__(self, stdin: TextIO, stdout: TextIO) -> None:
        """Initialize a transport over the given streams.

        :param stdin: The stream messages are read from.
        :type stdin: TextIO
        :param stdout: The stream messages are written to.
        :type stdout: TextIO
        """
        self._stdin = stdin
        self._stdout = stdout

    def read_message(self) -> dict[str, Any] | None:
        """Read the next non-blank line as a JSON object.

        :returns: The parsed message, or ``None`` at end of input.
        :rtype: dict[str, Any] | None
        :raises TransportError: If a non-blank line isn't valid JSON, or
            isn't a JSON object.
        """
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
        """Write a JSON object as one newline-terminated line.

        :param message: The message to serialize and write.
        :type message: dict[str, Any]
        """
        self._stdout.write(json.dumps(message) + "\n")
        self._stdout.flush()
