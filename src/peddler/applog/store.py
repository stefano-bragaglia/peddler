import json
from pathlib import Path

DEFAULT_APPLOG_PATH = Path.home() / ".peddler" / "applications.log"


class ApplicationLog:
    def __init__(self, path: Path = DEFAULT_APPLOG_PATH) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def append(self, url: str, timestamp: str, outcome: str) -> None:
        line = json.dumps({"url": url, "timestamp": timestamp, "outcome": outcome}) + "\n"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as handle:
            handle.write(line)
