"""Deterministic email-address extraction from CV markdown text."""

import re

_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_email(cv_text: str) -> str | None:
    """Find the first well-formed email address in CV text.

    Plain regex matching only — obfuscated forms (e.g. ``name (at)
    domain (dot) com``) are out of scope.

    :param cv_text: The full CV markdown content.
    :type cv_text: str
    :returns: The first email address found in reading order, or
        ``None`` if none is present.
    :rtype: str | None
    """
    match = _EMAIL_PATTERN.search(cv_text)
    return match.group(0) if match else None
