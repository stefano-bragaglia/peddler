import json
from pathlib import Path

import pytest

from peddler.applog.store import DEFAULT_APPLOG_PATH, ApplicationLog


def _log(tmp_path: Path) -> ApplicationLog:
    return ApplicationLog(tmp_path / "applications.log")


def test_default_applog_path_is_under_peddler_home_dir():
    assert DEFAULT_APPLOG_PATH == Path.home() / ".peddler" / "applications.log"


def test_append_creates_file_and_parent_directory(tmp_path):
    path = tmp_path / "nested" / "applications.log"
    log = ApplicationLog(path)

    log.append("https://acme.example.com/apply", "2026-07-17T12:00:00+00:00", "success")

    assert path.exists()


def test_append_writes_well_formed_json_line(tmp_path):
    log = _log(tmp_path)

    log.append("https://acme.example.com/apply", "2026-07-17T12:00:00+00:00", "success")

    line = log.path.read_text().strip("\n")
    entry = json.loads(line)
    assert entry == {
        "url": "https://acme.example.com/apply",
        "timestamp": "2026-07-17T12:00:00+00:00",
        "outcome": "success",
    }


def test_two_sequential_appends_produce_two_valid_lines(tmp_path):
    log = _log(tmp_path)

    log.append("https://acme.example.com/apply", "2026-07-17T12:00:00+00:00", "success")
    log.append("https://other.example.com/apply", "2026-07-17T12:05:00+00:00", "aborted")

    lines = log.path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["outcome"] == "success"
    assert json.loads(lines[1])["outcome"] == "aborted"


def test_append_raises_on_write_failure(tmp_path):
    path = tmp_path / "applications.log"
    path.write_text("")
    path.chmod(0o444)
    log = ApplicationLog(path)

    try:
        with pytest.raises(OSError):
            log.append("https://acme.example.com/apply", "2026-07-17T12:00:00+00:00", "success")
    finally:
        path.chmod(0o644)


def test_append_is_a_single_write_call(tmp_path, monkeypatch):
    log = _log(tmp_path)
    write_calls = []
    real_open = open

    def spy_open(*args, **kwargs):
        handle = real_open(*args, **kwargs)
        original_write = handle.write

        def spy_write(data):
            write_calls.append(data)
            return original_write(data)

        handle.write = spy_write
        return handle

    monkeypatch.setattr("builtins.open", spy_open)
    log.append("https://acme.example.com/apply", "2026-07-17T12:00:00+00:00", "success")

    assert len(write_calls) == 1
    assert write_calls[0].endswith("\n")
