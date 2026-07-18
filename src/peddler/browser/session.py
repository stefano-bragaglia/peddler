"""Single-session browser lifecycle: the open_session/close_session tools."""

import os
import time
from typing import Any, Callable

from peddler.browser.retry import retry_with_backoff

_session = None


class NavigationError(Exception):
    """Raised when navigating to a URL fails."""


class FieldNotFoundError(Exception):
    """Raised when a field id doesn't match any field on the current page."""


def _is_headless() -> bool:
    """Read the ``PEDDLER_HEADLESS`` env var; unset/empty means visible.

    :returns: ``True`` if the real browser should run headless.
    :rtype: bool
    """
    return os.environ.get("PEDDLER_HEADLESS", "").strip().lower() in ("1", "true", "yes")


def _default_browser_factory() -> Any:  # pragma: no cover
    # ponytail: real Playwright adapter, exercised by tests/browser/test_real_adapter.py
    # against local file:// fixtures (real Chromium, forced headless there via
    # PEDDLER_HEADLESS) -- every open_session/fill_field/advance_page unit test still
    # injects a fake page/browser_factory. See README.md -> Design rationale.
    from playwright.sync_api import sync_playwright

    class _PlaywrightPage:
        """Adapts a real Playwright page to this module's page protocol."""

        def __init__(self) -> None:
            """Launch a Chromium browser (visible unless PEDDLER_HEADLESS) and open a page."""
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=_is_headless())
            self._page = self._browser.new_page()

        def goto(self, url: str) -> None:
            """Navigate this page to ``url``, waiting for JS-rendered content to settle.

            :param url: The URL to navigate to.
            :type url: str
            :raises NavigationError: If navigation fails or times out.
            """
            try:
                self._page.goto(url, wait_until="networkidle")
            except Exception as exc:
                raise NavigationError(str(exc)) from exc

        def content(self) -> str:
            """Return the current page's content.

            :returns: The page's HTML content.
            :rtype: str
            """
            return self._page.content()

        def fill(self, field_id: str, value: str) -> dict[str, Any]:
            """Set a field's value by its ``id``.

            :param field_id: The ``id`` attribute of the field to fill.
            :type field_id: str
            :param value: The value to set. For a checkbox, a truthy
                string (``"true"``, ``"1"``, ``"yes"``) checks it.
            :type value: str
            :returns: ``{"status": "ok"}``.
            :rtype: dict[str, Any]
            :raises FieldNotFoundError: If no element has that ``id``.
            """
            locator = self._page.locator(f"#{field_id}")
            if locator.count() == 0:
                raise FieldNotFoundError(field_id)

            if locator.get_attribute("type") == "checkbox":
                if value.lower() in ("true", "1", "yes"):
                    locator.check()
                else:
                    locator.uncheck()
            else:
                locator.fill(value)
            return {"status": "ok"}

        def is_checked(self, field_id: str) -> bool:
            """Return whether the checkbox with ``id`` ``field_id`` is checked.

            :param field_id: The ``id`` attribute of the checkbox.
            :type field_id: str
            :returns: Whether it's checked.
            :rtype: bool
            """
            return self._page.locator(f"#{field_id}").is_checked()

        def submit(self) -> dict[str, Any]:
            """Click the current page's submit control and report the outcome.

            Field-level validation errors are detected via the best-effort
            ``aria-invalid``/``aria-describedby`` heuristic: any element left
            with ``aria-invalid="true"`` after the click is treated as a
            rejected field, with its message read from the element its
            ``aria-describedby`` points at, if any.

            :returns: ``{"status": "advanced", "content": <page content>}``
                if no field was left invalid; ``{"status": "error",
                "field_errors": {field_id: message, ...}}`` otherwise.
            :rtype: dict[str, Any]
            :raises NavigationError: If clicking submit or settling fails.
            """
            try:
                self._page.locator('button[type="submit"], input[type="submit"]').first.click()
                self._page.wait_for_load_state("networkidle")
            except Exception as exc:
                raise NavigationError(str(exc)) from exc

            invalid = self._page.locator('[aria-invalid="true"]')
            count = invalid.count()
            if count == 0:
                return {"status": "advanced", "content": self.content()}

            field_errors = {}
            for i in range(count):
                element = invalid.nth(i)
                field_id = element.get_attribute("id")
                described_by = element.get_attribute("aria-describedby")
                message = self._page.locator(f"#{described_by}").inner_text() if described_by else ""
                field_errors[field_id] = message
            return {"status": "error", "field_errors": field_errors}

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
