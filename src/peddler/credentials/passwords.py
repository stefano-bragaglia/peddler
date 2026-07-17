"""Cryptographically secure password generation for new site sign-ups."""

import secrets
import string

_SYMBOLS = "!@#$%^&*-_=+"
_CLASSES = (string.ascii_uppercase, string.ascii_lowercase, string.digits)
_ALPHABET = "".join(_CLASSES) + _SYMBOLS


def generate_password(length: int = 20) -> str:
    """Generate a random password with a guaranteed mix of character classes.

    Uses :mod:`secrets` exclusively (never :mod:`random`) for every
    random choice.

    :param length: The desired password length. Must be at least 8, to
        leave room for the guaranteed upper/lower/digit character
        classes plus at least some additional random characters.
    :type length: int
    :returns: A random password of exactly ``length`` characters,
        containing at least one uppercase letter, one lowercase letter,
        and one digit.
    :rtype: str
    :raises ValueError: If ``length`` is less than 8.
    """
    if length < 8:
        raise ValueError("length must be at least 8")

    required = [secrets.choice(chars) for chars in _CLASSES]
    remaining = [secrets.choice(_ALPHABET) for _ in range(length - len(required))]
    password = required + remaining
    secrets.SystemRandom().shuffle(password)
    return "".join(password)
