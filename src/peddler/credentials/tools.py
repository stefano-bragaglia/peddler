"""MCP tool registration for reading and writing the credentials log book."""

from typing import Any

from peddler.credentials.store import CredentialStore, CredentialStoreCorruptError
from peddler.mcp.registry import ToolRegistry

_READ_SCHEMA = {
    "type": "object",
    "properties": {"site": {"type": "string"}},
    "required": ["site"],
}

_WRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "site": {"type": "string"},
        "username": {"type": "string"},
        "password": {"type": "string"},
    },
    "required": ["site", "username", "password"],
}


def _make_read_credentials(store: CredentialStore):
    def read_credentials(arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            entry = store.get(arguments["site"])
        except CredentialStoreCorruptError as exc:
            return {"found": False, "username": None, "error": str(exc)}
        if entry is None:
            return {"found": False, "username": None}
        return {"found": True, "username": entry.username}

    return read_credentials


def _make_write_credentials(store: CredentialStore):
    def write_credentials(arguments: dict[str, Any]) -> dict[str, Any]:
        username = arguments["username"]
        password = arguments["password"]
        if not username or not password:
            return {"ok": False, "error": "username and password must not be blank"}
        try:
            store.put(arguments["site"], username, password)
        except CredentialStoreCorruptError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    return write_credentials


def register_credential_tools(registry: ToolRegistry, store: CredentialStore) -> None:
    """Register the ``read_credentials``/``write_credentials`` tools.

    :param registry: The registry to register both tools against.
    :type registry: ToolRegistry
    :param store: The credential store both tools' handlers read from
        and write to.
    :type store: CredentialStore
    """
    registry.register(
        "read_credentials",
        "Look up stored credentials for a site. Never returns the password.",
        _READ_SCHEMA,
        _make_read_credentials(store),
    )
    registry.register(
        "write_credentials",
        "Store credentials for a site.",
        _WRITE_SCHEMA,
        _make_write_credentials(store),
    )
