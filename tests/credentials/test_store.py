from pathlib import Path

import pytest

from peddler.credentials.store import (
    DEFAULT_CREDENTIALS_PATH,
    CredentialEntry,
    CredentialStore,
    CredentialStoreCorruptError,
)


def _store(tmp_path: Path) -> CredentialStore:
    return CredentialStore(tmp_path / "credentials.json")


def test_default_credentials_path_is_under_peddler_home_dir():
    assert DEFAULT_CREDENTIALS_PATH == Path.home() / ".peddler" / "credentials.json"


def test_get_on_missing_store_returns_none(tmp_path):
    store = _store(tmp_path)

    assert store.get("acme.example.com") is None


def test_put_creates_file_and_parent_directory(tmp_path):
    path = tmp_path / "nested" / "credentials.json"
    store = CredentialStore(path)

    store.put("acme.example.com", "alice", "s3cr3t")

    assert path.exists()


def test_put_then_get_returns_stored_credentials_exactly(tmp_path):
    store = _store(tmp_path)

    store.put("acme.example.com", "alice", "s3cr3t")

    entry = store.get("acme.example.com")

    assert entry == CredentialEntry(username="alice", password="s3cr3t")


@pytest.mark.parametrize(
    "stored_site,lookup_site",
    [
        ("acme.example.com", "https://acme.example.com/apply"),
        ("acme.example.com", "ACME.example.com"),
        ("acme.example.com", "https://ACME.EXAMPLE.COM/careers/apply/1234"),
        ("https://acme.example.com/apply", "acme.example.com"),
    ],
)
def test_get_normalizes_scheme_case_and_path(tmp_path, stored_site, lookup_site):
    store = _store(tmp_path)

    store.put(stored_site, "alice", "s3cr3t")

    assert store.get(lookup_site) == CredentialEntry(username="alice", password="s3cr3t")


def test_put_twice_same_hostname_overwrites_with_latest(tmp_path):
    store = _store(tmp_path)

    store.put("acme.example.com", "alice", "first-pass")
    store.put("acme.example.com", "alice2", "second-pass")

    assert store.get("acme.example.com") == CredentialEntry(username="alice2", password="second-pass")


def test_get_missing_site_in_nonempty_store_returns_none(tmp_path):
    store = _store(tmp_path)
    store.put("acme.example.com", "alice", "s3cr3t")

    assert store.get("other.example.com") is None


def test_get_raises_on_invalid_json(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text("{not valid json")
    store = CredentialStore(path)

    with pytest.raises(CredentialStoreCorruptError):
        store.get("acme.example.com")


def test_get_raises_on_empty_file(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text("")
    store = CredentialStore(path)

    with pytest.raises(CredentialStoreCorruptError):
        store.get("acme.example.com")


def test_put_raises_on_corrupt_existing_file(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text("{not valid json")
    store = CredentialStore(path)

    with pytest.raises(CredentialStoreCorruptError):
        store.put("acme.example.com", "alice", "s3cr3t")
