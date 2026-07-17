from pathlib import Path

APPLY_MD = Path(__file__).parent.parent.parent / "src" / "peddler" / "commands" / "apply.md"


def _content() -> str:
    return APPLY_MD.read_text()


def test_declares_trigger_and_documents_all_three_positional_arguments():
    content = _content()

    assert "/apply <cv.md> <jd.md> <url>" in content
    assert "cv.md" in content
    assert "jd.md" in content
    assert "url" in content


def test_references_every_tool_by_name():
    content = _content()

    for tool in (
        "open_session",
        "fill_field",
        "fill_credential_field",
        "advance_page",
        "close_session",
        "read_credentials",
        "write_credentials",
        "record_application",
    ):
        assert tool in content


def test_states_passwords_never_echoed_and_fill_credential_field_used_for_login():
    content = _content().lower()

    assert "never" in content
    assert "echo" in content
    assert "write_credentials" in content
    assert "fill_credential_field" in content


def test_states_stuck_handling_stays_headless_with_visible_fallback():
    content = _content().lower()

    assert "headless" in content
    assert "stuck" in content
    assert "visible" in content


def test_states_three_attempt_retry_policy_distinct_from_field_retries():
    content = _content().lower()

    assert "3 attempt" in content or "three attempt" in content
    assert "backoff" in content
    assert "crash" in content or "timeout" in content or "network" in content


def test_states_no_hard_cap_on_form_steps():
    content = _content().lower()

    assert "no hard cap" in content or "no cap" in content


def test_lists_all_three_outcome_values():
    content = _content()

    for outcome in ("success", "aborted", "stuck-unresolved"):
        assert outcome in content
