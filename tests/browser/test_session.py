import pytest

import peddler.browser.session as session
from peddler.browser.session import NavigationError, close_session, open_session


class _FakePage:
    def __init__(self, content="<html>form</html>", fail_times=0, exc=NavigationError):
        self.content_value = content
        self.fail_times = fail_times
        self.goto_calls = []
        self.closed = False
        self._exc = exc

    def goto(self, url):
        self.goto_calls.append(url)
        if len(self.goto_calls) <= self.fail_times:
            raise self._exc("navigation failed")

    def content(self):
        return self.content_value

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _reset_session_state():
    session._session = None
    yield
    session._session = None


def test_open_session_returns_opened_status_and_page_content():
    page = _FakePage(content="<html>hi</html>")

    result = open_session("https://acme.example.com", browser_factory=lambda: page, sleep=lambda s: None)

    assert result == {"status": "opened", "content": "<html>hi</html>"}


def test_open_session_twice_returns_already_open_error_no_second_browser():
    page = _FakePage()
    factory_calls = []

    def factory():
        factory_calls.append(1)
        return page

    open_session("https://acme.example.com", browser_factory=factory, sleep=lambda s: None)
    result = open_session("https://other.example.com", browser_factory=factory, sleep=lambda s: None)

    assert result == {"status": "error", "reason": "session already open"}
    assert len(factory_calls) == 1


def test_close_session_after_open_returns_closed_then_no_session():
    page = _FakePage()
    open_session("https://acme.example.com", browser_factory=lambda: page, sleep=lambda s: None)

    first = close_session()
    second = close_session()

    assert first == {"status": "closed"}
    assert second == {"status": "no_session"}
    assert page.closed is True


def test_close_session_with_no_open_session_returns_no_session():
    result = close_session()

    assert result == {"status": "no_session"}


def test_open_session_navigation_exhausts_three_retries_then_error():
    page = _FakePage(fail_times=3)
    delays = []

    result = open_session(
        "https://unreachable.example.com",
        browser_factory=lambda: page,
        sleep=lambda s: delays.append(s),
    )

    assert result == {"status": "error", "reason": "navigation failed: navigation failed"}
    assert len(page.goto_calls) == 3
    assert len(delays) == 2


def test_open_session_after_exhausted_retries_can_open_again():
    failing_page = _FakePage(fail_times=3)
    open_session("https://unreachable.example.com", browser_factory=lambda: failing_page, sleep=lambda s: None)

    working_page = _FakePage(content="<html>ok</html>")
    result = open_session("https://acme.example.com", browser_factory=lambda: working_page, sleep=lambda s: None)

    assert result == {"status": "opened", "content": "<html>ok</html>"}
