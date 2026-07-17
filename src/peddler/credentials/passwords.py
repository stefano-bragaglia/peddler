import secrets
import string

_SYMBOLS = "!@#$%^&*-_=+"
_CLASSES = (string.ascii_uppercase, string.ascii_lowercase, string.digits)
_ALPHABET = "".join(_CLASSES) + _SYMBOLS


def generate_password(length: int = 20) -> str:
    if length < 8:
        raise ValueError("length must be at least 8")

    required = [secrets.choice(chars) for chars in _CLASSES]
    remaining = [secrets.choice(_ALPHABET) for _ in range(length - len(required))]
    password = required + remaining
    secrets.SystemRandom().shuffle(password)
    return "".join(password)
