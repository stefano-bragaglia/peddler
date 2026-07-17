import json
from pathlib import Path

from peddler.applog.store import ApplicationLog
from peddler.applog.tools import register_applog_tools
from peddler.mcp.registry import ToolRegistry


def _registry(tmp_path: Path) -> tuple[ToolRegistry, ApplicationLog]:
    registry = ToolRegistry()
    log = ApplicationLog(tmp_path / "applications.log")
    register_applog_tools(registry, log)
    return registry, log


def test_record_application_registered_with_expected_name(tmp_path):
    registry, _ = _registry(tmp_path)

    assert registry.get("record_application") is not None


def test_valid_call_appends_one_line_with_generated_timestamp(tmp_path):
    registry, log = _registry(tmp_path)

    result = registry.get("record_application").handler(
        {"url": "https://acme.example.com/apply", "outcome": "success"}
    )

    assert result == {"ok": True}
    lines = log.path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["url"] == "https://acme.example.com/apply"
    assert entry["outcome"] == "success"
    assert "timestamp" in entry and entry["timestamp"]


def test_invalid_outcome_returns_error_and_writes_nothing(tmp_path):
    registry, log = _registry(tmp_path)

    result = registry.get("record_application").handler(
        {"url": "https://acme.example.com/apply", "outcome": "not-a-real-outcome"}
    )

    assert result["ok"] is False
    assert "error" in result
    assert not log.path.exists()


def test_simulated_write_failure_returns_structured_error(tmp_path):
    path = tmp_path / "applications.log"
    path.write_text("")
    path.chmod(0o444)
    registry = ToolRegistry()
    register_applog_tools(registry, ApplicationLog(path))

    try:
        result = registry.get("record_application").handler(
            {"url": "https://acme.example.com/apply", "outcome": "success"}
        )
    finally:
        path.chmod(0o644)

    assert result["ok"] is False
    assert "error" in result
