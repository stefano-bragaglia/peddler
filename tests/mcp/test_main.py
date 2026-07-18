import io
import json

from peddler.mcp.main import build_registry, main

_EXPECTED_TOOLS = {
    "read_credentials",
    "write_credentials",
    "record_application",
    "list_applications",
    "open_session",
    "close_session",
    "fill_field",
    "fill_credential_field",
    "advance_page",
}


def test_build_registry_registers_all_nine_tools():
    registry = build_registry()

    names = {spec["name"] for spec in registry.list_tools()}
    assert names == _EXPECTED_TOOLS


def test_build_registry_honors_env_var_paths(monkeypatch, tmp_path):
    cred_path = tmp_path / "creds.json"
    applog_path = tmp_path / "applog.log"
    monkeypatch.setenv("PEDDLER_CREDENTIALS_PATH", str(cred_path))
    monkeypatch.setenv("PEDDLER_APPLOG_PATH", str(applog_path))

    registry = build_registry()
    registry.get("write_credentials").handler(
        {"site": "acme.example.com", "username": "alice", "password": "s3cr3t"}
    )
    registry.get("record_application").handler({"url": "https://acme.example.com", "outcome": "success"})

    assert cred_path.exists()
    assert applog_path.exists()


def test_build_registry_falls_back_to_default_paths_when_env_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("PEDDLER_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("PEDDLER_APPLOG_PATH", raising=False)
    fake_default_cred = tmp_path / "default_creds.json"
    fake_default_applog = tmp_path / "default_applog.log"
    monkeypatch.setattr("peddler.mcp.main.DEFAULT_CREDENTIALS_PATH", fake_default_cred)
    monkeypatch.setattr("peddler.mcp.main.DEFAULT_APPLOG_PATH", fake_default_applog)

    registry = build_registry()
    registry.get("write_credentials").handler({"site": "a.com", "username": "u", "password": "p"})
    registry.get("record_application").handler({"url": "https://a.com", "outcome": "success"})

    assert fake_default_cred.exists()
    assert fake_default_applog.exists()


def test_open_session_adapter_calls_through_with_url(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "peddler.mcp.main.open_session", lambda url: calls.append(url) or {"status": "opened", "content": "<html>"}
    )

    registry = build_registry()
    result = registry.get("open_session").handler({"url": "https://acme.example.com"})

    assert calls == ["https://acme.example.com"]
    assert result == {"status": "opened", "content": "<html>"}


def test_close_session_adapter_calls_through_with_no_args(monkeypatch):
    calls = []
    monkeypatch.setattr("peddler.mcp.main.close_session", lambda: calls.append(1) or {"status": "closed"})

    registry = build_registry()
    result = registry.get("close_session").handler({})

    assert calls == [1]
    assert result == {"status": "closed"}


def test_fill_field_adapter_calls_through_with_field_id_and_value(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "peddler.mcp.main.fill_field",
        lambda field_id, value: calls.append((field_id, value)) or {"status": "ok"},
    )

    registry = build_registry()
    result = registry.get("fill_field").handler({"field_id": "email", "value": "ada@example.com"})

    assert calls == [("email", "ada@example.com")]
    assert result == {"status": "ok"}


def test_fill_credential_field_adapter_calls_through_with_field_id_and_site(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "peddler.mcp.main.fill_credential_field",
        lambda field_id, site: calls.append((field_id, site)) or {"status": "ok"},
    )

    registry = build_registry()
    result = registry.get("fill_credential_field").handler(
        {"field_id": "password", "site": "acme.example.com"}
    )

    assert calls == [("password", "acme.example.com")]
    assert result == {"status": "ok"}


def test_advance_page_adapter_calls_through_with_no_args(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "peddler.mcp.main.advance_page", lambda: calls.append(1) or {"status": "advanced", "content": "<html>"}
    )

    registry = build_registry()
    result = registry.get("advance_page").handler({})

    assert calls == [1]
    assert result == {"status": "advanced", "content": "<html>"}


def test_main_serves_tools_list_over_injected_streams():
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}) + "\n"
    stdin = io.StringIO(request)
    stdout = io.StringIO()

    main(stdin=stdin, stdout=stdout)

    response = json.loads(stdout.getvalue().splitlines()[0])
    tool_names = {tool["name"] for tool in response["result"]["tools"]}
    assert tool_names == _EXPECTED_TOOLS
