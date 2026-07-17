"""The fill_field tool: sets a form field's value on the open session's page."""

from typing import Any

import peddler.browser.session as session


class FieldNotFoundError(Exception):
    """Raised when a field id doesn't match any field on the current page."""


def fill_field(field_id: str, value: str) -> dict[str, Any]:
    """Set a field's value on the current session's page.

    :param field_id: The id of the field to fill.
    :type field_id: str
    :param value: The value to set. For checkbox-type fields, a truthy
        string (``"true"``, ``"1"``, ``"yes"``) checks it.
    :type value: str
    :returns: ``{"status": "ok"}`` on success; ``{"status": "error",
        "reason": "no session open"}`` if no session is open;
        ``{"status": "error", "field": field_id, "reason": ...}`` if the
        field isn't found, or the page rejects the value.
    :rtype: dict[str, Any]
    """
    page = session._session
    if page is None:
        return {"status": "error", "reason": "no session open"}

    try:
        result = page.fill(field_id, value)
    except FieldNotFoundError:
        return {"status": "error", "field": field_id, "reason": "field not found"}

    if result["status"] == "error":
        return {"status": "error", "field": field_id, "reason": result["reason"]}
    return {"status": "ok"}
