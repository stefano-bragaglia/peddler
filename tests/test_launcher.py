from pathlib import Path

from peddler.launcher import McpRegistrationError, _install_apply_command, main

_REAL_APPLY_MD = Path(__file__).parent.parent / "src" / "peddler" / "commands" / "apply.md"


def _noop_check_playwright():
    return True


def _noop_register_mcp(*args, **kwargs):
    return None


def _noop_install_command():
    return None


class _Recorder:
    def __init__(self, result=None, raises=None):
        self.calls = []
        self._result = result
        self._raises = raises

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self._raises is not None:
            raise self._raises
        return self._result


def test_execs_claude_in_resolved_dir_on_success(tmp_path):
    chdir = _Recorder()
    exec_fn = _Recorder()
    which = _Recorder(result="/usr/bin/claude")

    exit_code = main(
        argv=["--dir", str(tmp_path)],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=_noop_register_mcp,
        exec_fn=exec_fn,
        chdir=chdir,
        which=which,
    )

    assert exit_code == 0
    assert chdir.calls == [((str(tmp_path),), {})]
    assert exec_fn.calls == [(("/usr/bin/claude", ["/usr/bin/claude"]), {})]


def test_fails_fast_when_playwright_unavailable(tmp_path, capsys):
    exec_fn = _Recorder()
    register_mcp = _Recorder()

    exit_code = main(
        argv=["--dir", str(tmp_path)],
        install_command=_noop_install_command,
        check_playwright=lambda: False,
        register_mcp=register_mcp,
        exec_fn=exec_fn,
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    assert exit_code == 1
    assert "playwright install" in capsys.readouterr().err
    assert register_mcp.calls == []
    assert exec_fn.calls == []


def test_already_registered_is_treated_as_success(tmp_path):
    exec_fn = _Recorder()

    exit_code = main(
        argv=["--dir", str(tmp_path)],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=_noop_register_mcp,
        exec_fn=exec_fn,
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    assert exit_code == 0
    assert len(exec_fn.calls) == 1


def test_registration_failure_surfaces_error_and_does_not_exec(tmp_path, capsys):
    exec_fn = _Recorder()
    register_mcp = _Recorder(raises=McpRegistrationError("claude not found"))

    exit_code = main(
        argv=["--dir", str(tmp_path)],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=register_mcp,
        exec_fn=exec_fn,
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    assert exit_code == 1
    assert "claude not found" in capsys.readouterr().err
    assert exec_fn.calls == []


def test_defaults_used_when_credentials_and_applog_omitted(tmp_path):
    from peddler.applog.store import DEFAULT_APPLOG_PATH
    from peddler.credentials.store import DEFAULT_CREDENTIALS_PATH

    register_mcp = _Recorder()

    main(
        argv=["--dir", str(tmp_path)],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=register_mcp,
        exec_fn=_Recorder(),
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    ((call_args, _),) = register_mcp.calls
    assert call_args == (str(tmp_path), str(DEFAULT_CREDENTIALS_PATH), str(DEFAULT_APPLOG_PATH), False)


def test_explicit_credentials_and_applog_are_passed_through(tmp_path):
    register_mcp = _Recorder()
    creds = tmp_path / "creds.json"
    applog = tmp_path / "app.log"

    main(
        argv=["--dir", str(tmp_path), "--credentials", str(creds), "--applog", str(applog)],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=register_mcp,
        exec_fn=_Recorder(),
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    ((call_args, _),) = register_mcp.calls
    assert call_args == (str(tmp_path), str(creds), str(applog), False)


def test_headless_flag_is_passed_through_to_register_mcp(tmp_path):
    register_mcp = _Recorder()

    main(
        argv=["--dir", str(tmp_path), "--headless"],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=register_mcp,
        exec_fn=_Recorder(),
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    ((call_args, _),) = register_mcp.calls
    assert call_args[3] is True


def test_headless_defaults_to_false_ie_visible(tmp_path):
    register_mcp = _Recorder()

    main(
        argv=["--dir", str(tmp_path)],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=register_mcp,
        exec_fn=_Recorder(),
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    ((call_args, _),) = register_mcp.calls
    assert call_args[3] is False


def test_passthrough_args_after_double_dash_forwarded_to_claude(tmp_path):
    exec_fn = _Recorder()

    main(
        argv=["--dir", str(tmp_path), "--", "--model", "opus"],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=_noop_register_mcp,
        exec_fn=exec_fn,
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    ((call_args, _),) = exec_fn.calls
    assert call_args == ("/usr/bin/claude", ["/usr/bin/claude", "--model", "opus"])


def test_missing_dir_fails_before_any_other_step(capsys):
    register_mcp = _Recorder()
    exec_fn = _Recorder()

    exit_code = main(
        argv=["--dir", "/no/such/directory/at/all"],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=register_mcp,
        exec_fn=exec_fn,
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    assert exit_code == 1
    assert "/no/such/directory/at/all" in capsys.readouterr().err
    assert register_mcp.calls == []
    assert exec_fn.calls == []


def test_claude_not_on_path_fails_before_exec(tmp_path, capsys):
    exec_fn = _Recorder()

    exit_code = main(
        argv=["--dir", str(tmp_path)],
        install_command=_noop_install_command,
        check_playwright=_noop_check_playwright,
        register_mcp=_noop_register_mcp,
        exec_fn=exec_fn,
        chdir=_Recorder(),
        which=_Recorder(result=None),
    )

    assert exit_code == 1
    assert "claude" in capsys.readouterr().err.lower()
    assert exec_fn.calls == []


def test_install_creates_file_with_packaged_content_when_missing(tmp_path):
    target = tmp_path / "commands" / "apply.md"

    _install_apply_command(target)

    assert target.read_text() == _REAL_APPLY_MD.read_text()


def test_install_is_noop_when_content_already_matches(tmp_path, monkeypatch):
    target = tmp_path / "apply.md"
    target.write_text(_REAL_APPLY_MD.read_text())

    calls = []
    original_write_text = Path.write_text

    def spy_write_text(self, *args, **kwargs):
        calls.append(self)
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy_write_text)

    _install_apply_command(target)

    assert calls == []


def test_install_overwrites_when_content_differs(tmp_path):
    target = tmp_path / "apply.md"
    target.write_text("stale content")

    _install_apply_command(target)

    assert target.read_text() == _REAL_APPLY_MD.read_text()


def test_install_warns_but_does_not_raise_on_write_failure(tmp_path, capsys):
    target_dir = tmp_path / "readonly"
    target_dir.mkdir()
    target_dir.chmod(0o555)
    target = target_dir / "apply.md"

    try:
        _install_apply_command(target)
    finally:
        target_dir.chmod(0o755)

    assert "warning" in capsys.readouterr().err.lower()


def test_install_command_runs_before_playwright_check(tmp_path):
    order = []

    def install_command():
        order.append("install")

    def check_playwright():
        order.append("playwright")
        return True

    main(
        argv=["--dir", str(tmp_path)],
        install_command=install_command,
        check_playwright=check_playwright,
        register_mcp=_noop_register_mcp,
        exec_fn=_Recorder(),
        chdir=_Recorder(),
        which=_Recorder(result="/usr/bin/claude"),
    )

    assert order == ["install", "playwright"]
