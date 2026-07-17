import re

import pytest

import peddler.browser.session as session
from peddler.browser.fields import FieldNotFoundError, fill_credential_field, fill_field
from peddler.credentials.store import CredentialEntry, CredentialStoreCorruptError


class _FakeField:
    def __init__(self, kind="text", value="", pattern=None):
        self.kind = kind
        self.value = value
        self.pattern = pattern
        self.checked = False


class _FakePage:
    def __init__(self, fields):
        self._fields = fields

    def fill(self, field_id, value):
        field = self._fields.get(field_id)
        if field is None:
            raise FieldNotFoundError(field_id)
        if field.pattern is not None and not field.pattern.match(value):
            return {"status": "error", "reason": f"invalid value for {field_id}"}
        if field.kind == "checkbox":
            field.checked = value.lower() in ("true", "1", "yes")
        else:
            field.value = value
        return {"status": "ok"}

    def is_checked(self, field_id):
        return self._fields[field_id].checked


class _FakeStore:
    def __init__(self, entries=None, raise_corrupt=False):
        self._entries = entries or {}
        self._raise_corrupt = raise_corrupt

    def get(self, site):
        if self._raise_corrupt:
            raise CredentialStoreCorruptError("corrupt")
        return self._entries.get(site)


@pytest.fixture(autouse=True)
def _reset_session_state():
    session._session = None
    yield
    session._session = None


def test_fill_text_field_returns_ok_and_value_reflected():
    field = _FakeField(kind="text")
    session._session = _FakePage({"full_name": field})

    result = fill_field("full_name", "Ada Lovelace")

    assert result == {"status": "ok"}
    assert field.value == "Ada Lovelace"


def test_fill_field_with_validation_error_returns_status_error_with_reason():
    phone = _FakeField(kind="text", pattern=re.compile(r"^\d{3}-\d{3}-\d{4}$"))
    session._session = _FakePage({"phone": phone})

    result = fill_field("phone", "not-a-phone-number")

    assert result["status"] == "error"
    assert result["field"] == "phone"
    assert isinstance(result["reason"], str) and result["reason"]


def test_fill_field_with_no_open_session_returns_no_session_open_error():
    result = fill_field("full_name", "Ada Lovelace")

    assert result == {"status": "error", "reason": "no session open"}


def test_fill_field_not_present_returns_field_not_found_error():
    session._session = _FakePage({})

    result = fill_field("missing_field", "value")

    assert result == {"status": "error", "field": "missing_field", "reason": "field not found"}


def test_fill_checkbox_field_checks_it():
    checkbox = _FakeField(kind="checkbox")
    session._session = _FakePage({"agree_to_terms": checkbox})

    result = fill_field("agree_to_terms", "true")

    assert result == {"status": "ok"}
    assert checkbox.checked is True


def test_fill_credential_field_applies_stored_password_verified_from_page():
    field = _FakeField(kind="text")
    session._session = _FakePage({"password": field})
    store = _FakeStore({"acme.example.com": CredentialEntry(username="alice", password="s3cr3t")})

    result = fill_credential_field("password", "acme.example.com", store=store)

    assert result == {"status": "ok"}
    assert field.value == "s3cr3t"


def test_fill_credential_field_result_never_contains_password():
    field = _FakeField(kind="text")
    session._session = _FakePage({"password": field})
    store = _FakeStore({"acme.example.com": CredentialEntry(username="alice", password="s3cr3t")})

    result = fill_credential_field("password", "acme.example.com", store=store)

    assert "password" not in result
    assert "value" not in result
    assert "s3cr3t" not in str(result)


def test_fill_credential_field_no_stored_credentials_returns_error():
    session._session = _FakePage({"password": _FakeField()})
    store = _FakeStore({})

    result = fill_credential_field("password", "unknown.example.com", store=store)

    assert result == {"status": "error", "reason": "no credentials for site"}


def test_fill_credential_field_no_open_session_returns_error():
    store = _FakeStore({"acme.example.com": CredentialEntry(username="alice", password="s3cr3t")})

    result = fill_credential_field("password", "acme.example.com", store=store)

    assert result == {"status": "error", "reason": "no session open"}


def test_fill_credential_field_not_found_returns_error():
    session._session = _FakePage({})
    store = _FakeStore({"acme.example.com": CredentialEntry(username="alice", password="s3cr3t")})

    result = fill_credential_field("missing", "acme.example.com", store=store)

    assert result == {"status": "error", "field": "missing", "reason": "field not found"}


def test_fill_credential_field_corrupt_store_returns_structured_error():
    session._session = _FakePage({"password": _FakeField()})
    store = _FakeStore(raise_corrupt=True)

    result = fill_credential_field("password", "acme.example.com", store=store)

    assert result["status"] == "error"
    assert "reason" in result
