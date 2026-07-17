import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_CREDENTIALS_PATH = Path.home() / ".peddler" / "credentials.json"


class CredentialStoreCorruptError(Exception):
    """Raised when the backing credentials file exists but isn't valid JSON."""


@dataclass(frozen=True)
class CredentialEntry:
    username: str
    password: str


def _normalize_site(site: str) -> str:
    hostname = urlparse(site).hostname
    return (hostname or site).lower()


class CredentialStore:
    def __init__(self, path: Path = DEFAULT_CREDENTIALS_PATH) -> None:
        self._path = path

    def _read_all(self) -> dict[str, dict[str, str]]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except json.JSONDecodeError as exc:
            raise CredentialStoreCorruptError(f"corrupt credentials file: {self._path}") from exc

    def get(self, site: str) -> CredentialEntry | None:
        entries = self._read_all()
        entry = entries.get(_normalize_site(site))
        return CredentialEntry(**entry) if entry else None

    def put(self, site: str, username: str, password: str) -> None:
        entries = self._read_all()
        entries[_normalize_site(site)] = {"username": username, "password": password}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(entries))
