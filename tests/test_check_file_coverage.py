import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "check_file_coverage.py"


def _run(coverage_data: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    (tmp_path / "coverage.json").write_text(json.dumps(coverage_data))
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=tmp_path, capture_output=True, text=True
    )


def test_passes_when_every_file_meets_threshold(tmp_path):
    result = _run(
        {"files": {"a.py": {"summary": {"num_statements": 10, "percent_covered": 95.0}}}},
        tmp_path,
    )

    assert result.returncode == 0


def test_fails_when_a_file_is_below_threshold(tmp_path):
    result = _run(
        {"files": {"a.py": {"summary": {"num_statements": 10, "percent_covered": 60.0}}}},
        tmp_path,
    )

    assert result.returncode == 1
    assert "a.py" in result.stdout


def test_ignores_files_with_no_statements(tmp_path):
    result = _run(
        {"files": {"__init__.py": {"summary": {"num_statements": 0, "percent_covered": 0.0}}}},
        tmp_path,
    )

    assert result.returncode == 0
