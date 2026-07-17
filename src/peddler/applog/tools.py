"""MCP tool registration for recording `/apply` attempt outcomes."""

from datetime import UTC, datetime
from typing import Any

from peddler.applog.store import ApplicationLog
from peddler.mcp.registry import ToolRegistry

_ALLOWED_OUTCOMES = {"success", "aborted", "stuck-unresolved"}

_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "outcome": {"type": "string", "enum": sorted(_ALLOWED_OUTCOMES)},
    },
    "required": ["url", "outcome"],
}


def _make_record_application(log: ApplicationLog):
    def record_application(arguments: dict[str, Any]) -> dict[str, Any]:
        outcome = arguments["outcome"]
        if outcome not in _ALLOWED_OUTCOMES:
            return {"ok": False, "error": f"invalid outcome: {outcome!r}"}
        timestamp = datetime.now(UTC).isoformat()
        try:
            log.append(arguments["url"], timestamp, outcome)
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    return record_application


def register_applog_tools(registry: ToolRegistry, log: ApplicationLog) -> None:
    """Register the ``record_application`` tool against a tool registry.

    :param registry: The registry to register the tool against.
    :type registry: ToolRegistry
    :param log: The application log the tool's handler appends to.
    :type log: ApplicationLog
    """
    registry.register(
        "record_application",
        "Record the outcome of one /apply attempt to the persistent application log.",
        _SCHEMA,
        _make_record_application(log),
    )
