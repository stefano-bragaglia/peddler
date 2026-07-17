from peddler.email import extract_email


def test_extracts_standard_email_address():
    cv_text = "# CV\n\nContact: Ada Lovelace, ada@example.com, +1 555-0100\n"

    assert extract_email(cv_text) == "ada@example.com"


def test_returns_none_when_no_email_present():
    cv_text = "# CV\n\nContact: Ada Lovelace, +1 555-0100\n"

    assert extract_email(cv_text) is None


def test_returns_first_email_when_multiple_present():
    cv_text = "# CV\n\nContact: ada@example.com\n\nReferences: charles@example.com, grace@example.com\n"

    assert extract_email(cv_text) == "ada@example.com"


def test_does_not_match_near_miss_strings():
    cv_text = "# CV\n\nContact: not-an-email@, name (at) domain (dot) com\n"

    assert extract_email(cv_text) is None
