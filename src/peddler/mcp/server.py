"""JSON-RPC request dispatch and server loop over a Transport and ToolRegistry."""

import json
import sys
from typing import Any

from peddler.mcp.registry import ToolRegistry
from peddler.mcp.transport import Transport, TransportError

INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


class Server:
    """Reads JSON-RPC requests from a Transport and dispatches them to a ToolRegistry."""

    def __init__(self, transport: Transport, registry: ToolRegistry) -> None:
        """Initialize a server over a transport and a tool registry.

        :param transport: The transport requests are read from and
            responses are written to.
        :type transport: Transport
        :param registry: The registry tool calls are dispatched against.
        :type registry: ToolRegistry
        """
        self._transport = transport
        self._registry = registry

    def handle_one(self) -> bool:
        """Read and dispatch one JSON-RPC request, skipping malformed ones.

        :returns: ``True`` if a request was handled, ``False`` if the
            transport reached end of input.
        :rtype: bool
        """
        request = None
        while request is None:
            try:
                request = self._transport.read_message()
            except TransportError as exc:
                print(f"peddler: malformed request: {exc}", file=sys.stderr)
                continue
            break

        if request is None:
            return False

        self._transport.write_message(self._dispatch(request))
        return True

    def serve_forever(self) -> None:
        """Handle requests in a loop until the transport reaches end of input."""
        while self.handle_one():
            pass

    def _dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        method = request.get("method")

        if method == "initialize":
            return self._response(request_id, self._initialize_result())
        if method == "tools/list":
            return self._response(request_id, {"tools": self._registry.list_tools()})
        if method == "tools/call":
            return self._handle_tools_call(request_id, request.get("params") or {})
        if method is None:
            return self._error(request_id, INVALID_REQUEST, "Invalid Request: missing method")
        return self._error(request_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    def _handle_tools_call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if name is None:
            return self._error(request_id, INVALID_PARAMS, "Invalid params: missing 'name'")

        arguments = params.get("arguments", {})
        spec = self._registry.get(name)
        if spec is None:
            return self._response(request_id, self._tool_error(f"unknown tool: {name}"))

        try:
            result = spec.handler(arguments)
        except Exception as exc:
            return self._response(request_id, self._tool_error(str(exc)))

        content = [{"type": "text", "text": json.dumps(result)}]
        return self._response(request_id, {"content": content, "isError": False})

    @staticmethod
    def _tool_error(message: str) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": message}], "isError": True}

    @staticmethod
    def _initialize_result() -> dict[str, Any]:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "peddler", "version": "0.1.0"},
        }

    @staticmethod
    def _response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
