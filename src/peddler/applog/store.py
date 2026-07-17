"""Append-only JSON Lines storage for the persistent application log."""

import json
from pathlib import Path

DEFAULT_APPLOG_PATH = Path.home() / ".peddler" / "applications.log"


class ApplicationLog:
    """Appends one JSON Lines entry per recorded application attempt."""

    def __init__(self, path: Path = DEFAULT_APPLOG_PATH) -> None:
        """Initialize the log against a backing file path.

        :param path: The JSON Lines file to append entries to. Its parent
            directory is created on first :meth:`append` call if missing.
        :type path: Path
        """
        self._path = path

    @property
    def path(self) -> Path:
        """The backing file path this log appends to.

        :returns: The configured backing file path.
        :rtype: Path
        """
        return self._path

    def append(self, url: str, timestamp: str, outcome: str) -> None:
        """Append one entry as a single atomic, newline-terminated write.

        :param url: The URL the `/apply` attempt targeted.
        :type url: str
        :param timestamp: An ISO 8601 UTC timestamp for the attempt.
        :type timestamp: str
        :param outcome: One of ``"success"``, ``"aborted"``, or
            ``"stuck-unresolved"``.
        :type outcome: str
        :raises OSError: If the file cannot be written (e.g. disk full,
            permission denied).
        """
        line = json.dumps({"url": url, "timestamp": timestamp, "outcome": outcome}) + "\n"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as handle:
            handle.write(line)

    def list(self, url: str | None = None) -> list[dict[str, str]]:
        """List recorded entries in recording order, optionally filtered by URL.

        Lines that aren't valid JSON are skipped rather than raising, so
        one corrupt line doesn't hide the well-formed entries around it.

        :param url: If given, only entries with a matching ``url`` are
            returned.
        :type url: str | None
        :returns: Matching entries, oldest first. Empty if the log file
            doesn't exist yet.
        :rtype: list[dict[str, str]]
        """
        if not self._path.exists():
            return []
        entries = []
        for line in self._path.read_text().splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if url is None or entry.get("url") == url:
                entries.append(entry)
        return entries
