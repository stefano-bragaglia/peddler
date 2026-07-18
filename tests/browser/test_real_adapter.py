"""Tests the real Playwright adapter against local HTML fixtures -- not fakes.

Every other browser test injects a fake page/browser_factory (fast, no
real browser needed). This file is deliberately different: it drives
an actual (headless, forced via PEDDLER_HEADLESS) Chromium instance
against local fixture files, because the fake-based tests alone let
two real bugs ship undetected -- the real adapter was missing
fill/submit/is_checked entirely, and goto() never waited for
JS-rendered content.
"""

from pathlib import Path

import pytest

from peddler.browser.fields import FieldNotFoundError
from peddler.browser.session import _default_browser_factory

_FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def real_page(monkeypatch):
    monkeypatch.setenv("PEDDLER_HEADLESS", "1")
    page = _default_browser_factory()
    yield page
    page.close()


def test_goto_waits_for_late_rendered_content(real_page):
    real_page.goto(f"file://{_FIXTURES / 'late_render.html'}")

    assert "full_name" in real_page.content()


def test_fill_sets_text_field_value(real_page):
    real_page.goto(f"file://{_FIXTURES / 'application_form.html'}")

    result = real_page.fill("full_name", "Ada Lovelace")

    assert result == {"status": "ok"}


def test_fill_checks_checkbox(real_page):
    real_page.goto(f"file://{_FIXTURES / 'application_form.html'}")

    real_page.fill("agree_to_terms", "true")

    assert real_page.is_checked("agree_to_terms") is True


def test_fill_missing_field_raises_field_not_found(real_page):
    real_page.goto(f"file://{_FIXTURES / 'application_form.html'}")

    with pytest.raises(FieldNotFoundError):
        real_page.fill("does_not_exist", "value")


def test_submit_with_valid_data_advances_to_success_view(real_page):
    real_page.goto(f"file://{_FIXTURES / 'application_form.html'}")
    real_page.fill("full_name", "Ada Lovelace")
    real_page.fill("phone", "555-555-5555")

    result = real_page.submit()

    assert result["status"] == "advanced"
    assert "Thank you for applying" in result["content"]


def test_submit_with_invalid_phone_returns_field_error(real_page):
    real_page.goto(f"file://{_FIXTURES / 'application_form.html'}")
    real_page.fill("full_name", "Ada Lovelace")
    real_page.fill("phone", "not-a-phone")

    result = real_page.submit()

    assert result["status"] == "error"
    assert "phone" in result["field_errors"]
