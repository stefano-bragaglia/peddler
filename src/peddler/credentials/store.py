"""File-backed store for per-site credential entries, keyed by hostname."""

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_CREDENTIALS_PATH = Path.home() / ".peddler" / "credentials.json"


class CredentialStoreCorruptError(Exception):
    """Raised when the backing credentials file exists but isn't valid JSON."""


@dataclass(frozen=True)
class CredentialEntry:
    """A stored site's username and password."""

    username: str
    password: str


def _normalize_site(site: str) -> str:
    hostname = urlparse(site).hostname
    return (hostname or site).lower()


class CredentialStore:
    """Reads and writes per-site credentials in a local JSON file."""

    def __init__(self, path: Path = DEFAULT_CREDENTIALS_PATH) -> None:
        """Initialize a store against a backing file path.

        :param path: The JSON file to read and write entries in. Its
            parent directory is created on first :meth:`put` call if
            missing.
        :type path: Path
        """
        self._path = path

    def _read_all(self) -> dict[str, dict[str, str]]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except json.JSONDecodeError as exc:
            raise CredentialStoreCorruptError(f"corrupt credentials file: {self._path}") from exc

    def get(self, site: str) -> CredentialEntry | None:
        """Look up the stored credentials for a site.

        :param site: A hostname or URL identifying the site; normalized
            to a lowercased hostname before lookup.
        :type site: str
        :returns: The stored entry, or ``None`` if no entry exists for
            this site.
        :rtype: CredentialEntry | None
        :raises CredentialStoreCorruptError: If the backing file exists
            but contains invalid JSON.
        """
        entries = self._read_all()
        entry = entries.get(_normalize_site(site))
        return CredentialEntry(**entry) if entry else None

    def put(self, site: str, username: str, password: str) -> None:
        """Store (or overwrite) the credentials for a site.

        :param site: A hostname or URL identifying the site; normalized
            to a lowercased hostname before storing.
        :type site: str
        :param username: The username to store.
        :type username: str
        :param password: The password to store.
        :type password: str
        :raises CredentialStoreCorruptError: If the backing file exists
            but contains invalid JSON.
        """
        entries = self._read_all()
        entries[_normalize_site(site)] = {"username": username, "password": password}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(entries))
