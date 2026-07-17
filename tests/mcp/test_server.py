import io
import json

from peddler.mcp.registry import ToolRegistry
from peddler.mcp.server import Server
from peddler.mcp.transport import Transport


def _make_server(requests: list[dict], registry: ToolRegistry | None = None) -> tuple[Server, io.StringIO]:
    lines = "".join(json.dumps(request) + "\n" for request in requests)
    stdout = io.StringIO()
    transport = Transport(stdin=io.StringIO(lines), stdout=stdout)
    return Server(transport=transport, registry=registry or ToolRegistry()), stdout


def _read_responses(stdout: io.StringIO) -> list[dict]:
    stdout.seek(0)
    return [json.loads(line) for line in stdout.read().splitlines() if line.strip()]


def test_initialize_returns_result_without_error():
    server, stdout = _make_server([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}])

    still_running = server.handle_one()

    responses = _read_responses(stdout)
    assert still_running is True
    assert "result" in responses[0]
    assert "error" not in responses[0]


def test_tools_list_returns_registered_tool():
    registry = ToolRegistry()
    registry.register("echo", "echoes input", {"type": "object"}, lambda arguments: arguments)
    server, stdout = _make_server(
        [{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}], registry=registry
    )

    server.handle_one()

    tools = _read_responses(stdout)[0]["result"]["tools"]
    assert tools == [{"name": "echo", "description": "echoes input", "inputSchema": {"type": "object"}}]


def test_tools_call_success_reflects_handler_result():
    registry = ToolRegistry()
    registry.register("add", "adds one", {"type": "object"}, lambda arguments: {"sum": arguments["n"] + 1})
    server, stdout = _make_server(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "add", "arguments": {"n": 41}},
            }
        ],
        registry=registry,
    )

    server.handle_one()

    result = _read_responses(stdout)[0]["result"]
    assert result["isError"] is False
    assert any("42" in block["text"] for block in result["content"])


def test_tools_call_handler_raises_returns_error_and_server_keeps_serving():
    registry = ToolRegistry()

    def _raising_handler(arguments: dict) -> dict:
        raise ValueError("bad phone number")

    registry.register("dial", "dials a number", {"type": "object"}, _raising_handler)
    server, stdout = _make_server(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "dial", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}},
        ],
        registry=registry,
    )

    assert server.handle_one() is True
    assert server.handle_one() is True

    first, second = _read_responses(stdout)
    assert first["result"]["isError"] is True
    assert any("bad phone number" in block["text"] for block in first["result"]["content"])
    assert "result" in second
    assert "error" not in second


def test_tools_call_unregistered_tool_returns_error():
    server, stdout = _make_server(
        [{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "missing", "arguments": {}}}]
    )

    server.handle_one()

    result = _read_responses(stdout)[0]["result"]
    assert result["isError"] is True
    assert any("missing" in block["text"] for block in result["content"])


def test_unknown_method_returns_method_not_found_error():
    server, stdout = _make_server([{"jsonrpc": "2.0", "id": 1, "method": "frobnicate", "params": {}}])

    server.handle_one()

    response = _read_responses(stdout)[0]
    assert response["error"]["code"] == -32601


def test_tools_call_missing_name_returns_error_not_exception():
    server, stdout = _make_server(
        [{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"arguments": {}}}]
    )

    server.handle_one()

    response = _read_responses(stdout)[0]
    assert response["error"]["code"] in {-32600, -32602}


def test_response_id_matches_request_id():
    registry = ToolRegistry()
    registry.register("echo", "echoes", {"type": "object"}, lambda arguments: arguments)
    server, stdout = _make_server(
        [
            {"jsonrpc": "2.0", "id": "req-1", "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": "req-2", "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": "req-3", "method": "frobnicate", "params": {}},
        ],
        registry=registry,
    )

    server.handle_one()
    server.handle_one()
    server.handle_one()

    responses = _read_responses(stdout)
    assert [response["id"] for response in responses] == ["req-1", "req-2", "req-3"]


def test_serve_forever_processes_all_requests_then_returns():
    requests = [{"jsonrpc": "2.0", "id": i, "method": "initialize", "params": {}} for i in range(3)]
    server, stdout = _make_server(requests)

    server.serve_forever()

    assert len(_read_responses(stdout)) == 3


def test_malformed_line_logged_to_stderr_and_read_loop_continues(capsys):
    stdin = io.StringIO("not json\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n")
    stdout = io.StringIO()
    transport = Transport(stdin=stdin, stdout=stdout)
    server = Server(transport=transport, registry=ToolRegistry())

    assert server.handle_one() is True

    responses = _read_responses(stdout)
    assert len(responses) == 1
    assert responses[0]["id"] == 1
    assert capsys.readouterr().err != ""
