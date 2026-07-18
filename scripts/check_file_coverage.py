"""Fail if any source file's line coverage falls below the required minimum.

pytest-cov/coverage.py only gate on the *aggregate* percentage
(--cov-fail-under); this closes the gap by checking every individual
file too, so one well-tested module can't hide another one sitting
well below the bar.
"""

import json
import sys

MIN_COVERAGE = 90.0


def main() -> int:
    """Check every file in coverage.json against MIN_COVERAGE.

    :returns: 0 if every file with at least one statement meets
        ``MIN_COVERAGE``, 1 otherwise (offending files are printed).
    :rtype: int
    """
    with open("coverage.json") as handle:
        data = json.load(handle)

    failures = [
        (path, summary["summary"]["percent_covered"])
        for path, summary in data["files"].items()
        if summary["summary"]["num_statements"] > 0
        and summary["summary"]["percent_covered"] < MIN_COVERAGE
    ]
    if failures:
        print(f"Per-file coverage below {MIN_COVERAGE}%:")
        for path, pct in sorted(failures):
            print(f"  {path}: {pct:.1f}%")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
