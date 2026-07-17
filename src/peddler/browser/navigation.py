"""The advance_page tool: submits the current page, retrying transient failures."""

import time
from typing import Any, Callable

import peddler.browser.session as session
from peddler.browser.retry import retry_with_backoff
from peddler.browser.session import NavigationError


def advance_page(sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """Submit/advance the current session's page.

    The submit action is retried with backoff (see
    :func:`peddler.browser.retry.retry_with_backoff`) up to 3 attempts
    if it fails transiently.

    :param sleep: The delay function used between retry attempts.
    :type sleep: Callable[[float], None]
    :returns: ``{"status": "advanced", "content": ...}`` on a successful
        transition; ``{"status": "error", "field_errors": {...}}`` if
        the page stayed put with validation errors;
        ``{"status": "error", "reason": "no session open"}`` if no
        session is open; ``{"status": "error", "reason": ...}`` if the
        transition fails after all retries.
    :rtype: dict[str, Any]
    """
    page = session._session
    if page is None:
        return {"status": "error", "reason": "no session open"}

    try:
        return retry_with_backoff(page.submit, (NavigationError,), sleep=sleep)
    except NavigationError as exc:
        return {"status": "error", "reason": f"navigation failed: {exc}"}
