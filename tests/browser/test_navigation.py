import pytest

import peddler.browser.session as session
from peddler.browser.navigation import advance_page
from peddler.browser.session import NavigationError


class _FakePage:
    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.submit_calls = 0

    def submit(self):
        self.submit_calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, type) and issubclass(outcome, Exception):
            raise outcome("transition failed")
        return outcome


@pytest.fixture(autouse=True)
def _reset_session_state():
    session._session = None
    yield
    session._session = None


def test_advance_page_success_returns_advanced_and_content():
    session._session = _FakePage([{"status": "advanced", "content": "<html>step 2</html>"}])

    result = advance_page()

    assert result == {"status": "advanced", "content": "<html>step 2</html>"}


def test_advance_page_single_invalid_field_returns_field_errors():
    session._session = _FakePage(
        [{"status": "error", "field_errors": {"phone": "invalid phone number"}}]
    )

    result = advance_page()

    assert result == {"status": "error", "field_errors": {"phone": "invalid phone number"}}


def test_advance_page_two_invalid_fields_returns_both_field_errors():
    session._session = _FakePage(
        [
            {
                "status": "error",
                "field_errors": {
                    "phone": "invalid phone number",
                    "email": "invalid email address",
                },
            }
        ]
    )

    result = advance_page()

    assert result["status"] == "error"
    assert set(result["field_errors"].keys()) == {"phone", "email"}


def test_advance_page_with_no_open_session_returns_no_session_open_error():
    result = advance_page()

    assert result == {"status": "error", "reason": "no session open"}


def test_advance_page_transient_failure_retries_three_times_then_errors():
    page = _FakePage([NavigationError, NavigationError, NavigationError])
    session._session = page
    delays = []

    result = advance_page(sleep=lambda s: delays.append(s))

    assert result["status"] == "error"
    assert "reason" in result
    assert page.submit_calls == 3
    assert len(delays) == 2
