"""Wires every feature's tools into one registry and serves them over stdio."""

import os
import sys
from pathlib import Path
from typing import IO

from peddler.applog.store import DEFAULT_APPLOG_PATH, ApplicationLog
from peddler.applog.tools import register_applog_tools
from peddler.browser.fields import fill_credential_field, fill_field
from peddler.browser.navigation import advance_page
from peddler.browser.session import close_session, open_session
from peddler.credentials.store import DEFAULT_CREDENTIALS_PATH, CredentialStore
from peddler.credentials.tools import register_credential_tools
from peddler.mcp.registry import ToolRegistry
from peddler.mcp.server import Server
from peddler.mcp.transport import Transport

_OPEN_SESSION_SCHEMA = {
    "type": "object",
    "properties": {"url": {"type": "string"}},
    "required": ["url"],
}

_FILL_FIELD_SCHEMA = {
    "type": "object",
    "properties": {"field_id": {"type": "string"}, "value": {"type": "string"}},
    "required": ["field_id", "value"],
}

_FILL_CREDENTIAL_FIELD_SCHEMA = {
    "type": "object",
    "properties": {"field_id": {"type": "string"}, "site": {"type": "string"}},
    "required": ["field_id", "site"],
}

_NO_ARGS_SCHEMA: dict = {"type": "object", "properties": {}}


def build_registry() -> ToolRegistry:
    """Wire every feature's tools into a single, freshly-built registry.

    :returns: A registry with all 9 Peddler tools registered:
        ``read_credentials``, ``write_credentials``, ``record_application``,
        ``list_applications``, ``open_session``, ``close_session``,
        ``fill_field``, ``fill_credential_field``, ``advance_page``.
    :rtype: ToolRegistry
    """
    registry = ToolRegistry()

    credentials_path = os.environ.get("PEDDLER_CREDENTIALS_PATH")
    store = CredentialStore(Path(credentials_path) if credentials_path else DEFAULT_CREDENTIALS_PATH)
    register_credential_tools(registry, store)

    applog_path = os.environ.get("PEDDLER_APPLOG_PATH")
    applog = ApplicationLog(Path(applog_path) if applog_path else DEFAULT_APPLOG_PATH)
    register_applog_tools(registry, applog)

    registry.register(
        "open_session",
        "Open a headless browser session and navigate to a URL.",
        _OPEN_SESSION_SCHEMA,
        lambda arguments: open_session(arguments["url"]),
    )
    registry.register(
        "close_session",
        "Close the current browser session, if one is open.",
        _NO_ARGS_SCHEMA,
        lambda arguments: close_session(),
    )
    registry.register(
        "fill_field",
        "Set a form field's value on the current session's page.",
        _FILL_FIELD_SCHEMA,
        lambda arguments: fill_field(arguments["field_id"], arguments["value"]),
    )
    registry.register(
        "fill_credential_field",
        "Fill a field with the password stored for a site, resolved server-side.",
        _FILL_CREDENTIAL_FIELD_SCHEMA,
        lambda arguments: fill_credential_field(arguments["field_id"], arguments["site"]),
    )
    registry.register(
        "advance_page",
        "Submit/advance the current session's page.",
        _NO_ARGS_SCHEMA,
        lambda arguments: advance_page(),
    )

    return registry


def main(stdin: IO[str] = sys.stdin, stdout: IO[str] = sys.stdout) -> None:
    """Serve every Peddler tool over stdio until the transport reaches end of input.

    :param stdin: The stream to read JSON-RPC requests from.
    :type stdin: IO[str]
    :param stdout: The stream to write JSON-RPC responses to.
    :type stdout: IO[str]
    """
    transport = Transport(stdin, stdout)
    Server(transport, build_registry()).serve_forever()


if __name__ == "__main__":
    main()
