from pathlib import Path

from peddler.credentials.store import CredentialStore
from peddler.credentials.tools import register_credential_tools
from peddler.mcp.registry import ToolRegistry


def _registry(tmp_path: Path) -> ToolRegistry:
    registry = ToolRegistry()
    store = CredentialStore(tmp_path / "credentials.json")
    register_credential_tools(registry, store)
    return registry


def test_read_credentials_registered_with_expected_name(tmp_path):
    registry = _registry(tmp_path)

    assert registry.get("read_credentials") is not None
    assert registry.get("write_credentials") is not None


def test_read_credentials_never_seen_site_returns_not_found(tmp_path):
    registry = _registry(tmp_path)

    result = registry.get("read_credentials").handler({"site": "acme.example.com"})

    assert result == {"found": False, "username": None}


def test_write_then_read_credentials_returns_matching_username_no_password(tmp_path):
    registry = _registry(tmp_path)

    write_result = registry.get("write_credentials").handler(
        {"site": "acme.example.com", "username": "alice", "password": "s3cr3t"}
    )
    read_result = registry.get("read_credentials").handler({"site": "acme.example.com"})

    assert write_result == {"ok": True}
    assert read_result == {"found": True, "username": "alice"}
    assert "password" not in read_result


def test_write_credentials_blank_username_returns_structured_failure(tmp_path):
    registry = _registry(tmp_path)

    result = registry.get("write_credentials").handler(
        {"site": "acme.example.com", "username": "", "password": "s3cr3t"}
    )

    assert result["ok"] is False
    assert "error" in result


def test_write_credentials_blank_password_returns_structured_failure(tmp_path):
    registry = _registry(tmp_path)

    result = registry.get("write_credentials").handler(
        {"site": "acme.example.com", "username": "alice", "password": ""}
    )

    assert result["ok"] is False
    assert "error" in result


def test_read_credentials_corrupt_store_returns_structured_error_not_raise(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text("{not valid json")
    registry = ToolRegistry()
    register_credential_tools(registry, CredentialStore(path))

    result = registry.get("read_credentials").handler({"site": "acme.example.com"})

    assert result["found"] is False
    assert "error" in result


def test_write_credentials_corrupt_store_returns_structured_error_not_raise(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text("{not valid json")
    registry = ToolRegistry()
    register_credential_tools(registry, CredentialStore(path))

    result = registry.get("write_credentials").handler(
        {"site": "acme.example.com", "username": "alice", "password": "s3cr3t"}
    )

    assert result["ok"] is False
    assert "error" in result
