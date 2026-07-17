import inspect

import pytest

from peddler.credentials import passwords
from peddler.credentials.passwords import generate_password


def test_generated_password_has_requested_length():
    assert len(generate_password(20)) == 20
    assert len(generate_password(12)) == 12


def test_generated_password_contains_upper_lower_and_digit():
    password = generate_password(20)

    assert any(c.isupper() for c in password)
    assert any(c.islower() for c in password)
    assert any(c.isdigit() for c in password)


def test_consecutive_calls_produce_different_passwords():
    assert generate_password(20) != generate_password(20)


def test_length_below_eight_raises_value_error():
    with pytest.raises(ValueError):
        generate_password(7)


def test_default_length_is_twenty():
    assert len(generate_password()) == 20


def test_source_never_uses_random_module():
    source = inspect.getsource(passwords)

    assert "import random" not in source
    assert "from random" not in source
