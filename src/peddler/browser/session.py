"""Single-session browser lifecycle: the open_session/close_session tools."""

import time
from typing import Any, Callable

from peddler.browser.retry import retry_with_backoff

_session = None


class NavigationError(Exception):
    """Raised when navigating to a URL fails."""


def _default_browser_factory() -> Any:
    from playwright.sync_api import sync_playwright

    class _PlaywrightPage:
        """Adapts a real Playwright page to this module's page protocol."""

        def __init__(self) -> None:
            """Launch a headless Chromium browser and open a new page."""
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._page = self._browser.new_page()

        def goto(self, url: str) -> None:
            """Navigate this page to ``url``.

            :param url: The URL to navigate to.
            :type url: str
            """
            self._page.goto(url)

        def content(self) -> str:
            """Return the current page's content.

            :returns: The page's HTML content.
            :rtype: str
            """
            return self._page.content()

        def close(self) -> None:
            """Close the browser and stop the underlying Playwright process."""
            self._browser.close()
            self._playwright.stop()

    return _PlaywrightPage()


def open_session(
    url: str,
    browser_factory: Callable[[], Any] = _default_browser_factory,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Open the single global browser session and navigate to ``url``.

    Navigation is retried with backoff (see
    :func:`peddler.browser.retry.retry_with_backoff`) up to 3 attempts
    before giving up.

    :param url: The URL to open.
    :type url: str
    :param browser_factory: Creates the page-like object to navigate.
        Defaults to a real headless Playwright/Chromium page; tests
        inject a fake.
    :type browser_factory: Callable[[], Any]
    :param sleep: The delay function used between retry attempts.
    :type sleep: Callable[[float], None]
    :returns: ``{"status": "opened", "content": <page content>}`` on
        success; ``{"status": "error", "reason": ...}`` if a session is
        already open, or if navigation fails after all retries.
    :rtype: dict[str, Any]
    """
    global _session
    if _session is not None:
        return {"status": "error", "reason": "session already open"}

    page = browser_factory()
    try:
        retry_with_backoff(lambda: page.goto(url), (NavigationError,), sleep=sleep)
    except NavigationError as exc:
        page.close()
        return {"status": "error", "reason": f"navigation failed: {exc}"}

    _session = page
    return {"status": "opened", "content": page.content()}


def close_session() -> dict[str, Any]:
    """Close the single global browser session, if one is open.

    :returns: ``{"status": "closed"}`` if a session was open and is now
        closed; ``{"status": "no_session"}`` if none was open.
    :rtype: dict[str, Any]
    """
    global _session
    if _session is None:
        return {"status": "no_session"}
    _session.close()
    _session = None
    return {"status": "closed"}
