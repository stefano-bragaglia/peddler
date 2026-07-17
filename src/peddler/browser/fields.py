"""The fill_field/fill_credential_field tools: set a form field's value."""

from typing import Any

import peddler.browser.session as session
from peddler.credentials.store import CredentialStore, CredentialStoreCorruptError


class FieldNotFoundError(Exception):
    """Raised when a field id doesn't match any field on the current page."""


def _apply_fill(field_id: str, value: str) -> dict[str, Any] | None:
    """Fill a field on the current session's page, translating page errors.

    :param field_id: The id of the field to fill.
    :type field_id: str
    :param value: The value to set on the field.
    :type value: str
    :returns: ``None`` on success; a structured error dict if no session
        is open, the field isn't found, or the page rejects the value.
    :rtype: dict[str, Any] | None
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
    return None


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
    error = _apply_fill(field_id, value)
    return error if error is not None else {"status": "ok"}


def fill_credential_field(
    field_id: str, site: str, store: CredentialStore = CredentialStore()
) -> dict[str, Any]:
    """Fill a field with the password stored for ``site``, resolved server-side.

    The password is read directly from the credential store and applied
    to the page; it never appears in this function's return value.

    :param field_id: The id of the field to fill (typically a password
        field).
    :type field_id: str
    :param site: A hostname or URL identifying the site whose stored
        password should be applied.
    :type site: str
    :param store: The credential store to read the password from.
    :type store: CredentialStore
    :returns: ``{"status": "ok"}`` on success; ``{"status": "error",
        "reason": "no session open"}``; ``{"status": "error", "reason":
        "no credentials for site"}``; ``{"status": "error", "field":
        field_id, "reason": ...}`` if the field isn't found or the page
        rejects the value; or a structured error if the store is
        corrupt. Never contains the password itself.
    :rtype: dict[str, Any]
    """
    if session._session is None:
        return {"status": "error", "reason": "no session open"}

    try:
        entry = store.get(site)
    except CredentialStoreCorruptError as exc:
        return {"status": "error", "reason": str(exc)}
    if entry is None:
        return {"status": "error", "reason": "no credentials for site"}

    error = _apply_fill(field_id, entry.password)
    return error if error is not None else {"status": "ok"}
