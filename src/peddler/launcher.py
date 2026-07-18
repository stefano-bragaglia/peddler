"""The peddler console script: launches Claude Code with the MCP server registered."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from peddler.applog.store import DEFAULT_APPLOG_PATH
from peddler.browser import session as browser_session
from peddler.credentials.store import DEFAULT_CREDENTIALS_PATH


class McpRegistrationError(Exception):
    """Raised when MCP server registration fails for a reason other than already being registered."""


def _split_passthrough(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" in argv:
        index = argv.index("--")
        return argv[:index], argv[index + 1 :]
    return argv, []


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="peddler")
    parser.add_argument("--dir", default=os.getcwd())
    parser.add_argument("--credentials", default=str(DEFAULT_CREDENTIALS_PATH))
    parser.add_argument("--applog", default=str(DEFAULT_APPLOG_PATH))
    return parser


def _default_check_playwright() -> bool:  # pragma: no cover
    # ponytail: real Playwright launch-and-close, deliberately untested here (needs
    # real browser binaries); every main() test injects a fake check_playwright.
    try:
        page = browser_session._default_browser_factory()
        page.close()
    except Exception:
        return False
    return True


def _register_mcp_server(  # pragma: no cover
    target_dir: str,
    credentials_path: str,
    applog_path: str,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> None:
    # ponytail: real `claude mcp add` subprocess call, deliberately untested here
    # (needs the real claude CLI); every main() test injects a fake register_mcp.
    result = run(
        [
            "claude",
            "mcp",
            "add",
            "peddler-mcp",
            "--scope",
            "local",
            "--env",
            f"PEDDLER_CREDENTIALS_PATH={credentials_path}",
            "--env",
            f"PEDDLER_APPLOG_PATH={applog_path}",
            "--",
            "peddler-mcp",
        ],
        cwd=target_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "already exists" not in result.stderr.lower():
        raise McpRegistrationError(result.stderr.strip())


def main(
    argv: list[str] | None = None,
    check_playwright: Callable[[], bool] = _default_check_playwright,
    register_mcp: Callable[[str, str, str], None] = _register_mcp_server,
    exec_fn: Callable[[str, list[str]], None] = os.execvp,
    chdir: Callable[[str], None] = os.chdir,
    which: Callable[[str], str | None] = shutil.which,
) -> int:
    """Check prerequisites, register the MCP server, and hand off to Claude Code.

    :param argv: Command-line arguments, excluding the program name.
        Defaults to ``sys.argv[1:]``.
    :type argv: list[str] | None
    :param check_playwright: Returns whether Playwright's browser
        binaries are usable. Injectable for testing.
    :type check_playwright: Callable[[], bool]
    :param register_mcp: Registers the MCP server for ``target_dir``.
        Raises :class:`McpRegistrationError` on genuine failure;
        returns normally on success or "already registered". Injectable
        for testing.
    :type register_mcp: Callable[[str, str, str], None]
    :param exec_fn: Replaces the current process with ``claude``.
        Injectable for testing (defaults to :func:`os.execvp`).
    :type exec_fn: Callable[[str, list[str]], None]
    :param chdir: Changes the current working directory. Injectable for
        testing (defaults to :func:`os.chdir`).
    :type chdir: Callable[[str], None]
    :param which: Resolves an executable's path on ``PATH``. Injectable
        for testing (defaults to :func:`shutil.which`).
    :type which: Callable[[str], str | None]
    :returns: 0 on success (though ``exec_fn`` normally never returns in
        production); 1 on any failure.
    :rtype: int
    """
    own_argv, claude_args = _split_passthrough(sys.argv[1:] if argv is None else argv)
    args = _build_parser().parse_args(own_argv)

    if not Path(args.dir).is_dir():
        print(f"peddler: no such directory: {args.dir}", file=sys.stderr)
        return 1

    if not check_playwright():
        print(
            "peddler: Playwright browser binaries not found. "
            "Run `uv run playwright install chromium` and try again.",
            file=sys.stderr,
        )
        return 1

    try:
        register_mcp(args.dir, args.credentials, args.applog)
    except McpRegistrationError as exc:
        print(f"peddler: failed to register MCP server: {exc}", file=sys.stderr)
        return 1

    claude_path = which("claude")
    if claude_path is None:
        print("peddler: 'claude' not found on PATH", file=sys.stderr)
        return 1

    chdir(args.dir)
    exec_fn(claude_path, [claude_path, *claude_args])
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
