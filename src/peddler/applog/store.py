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
