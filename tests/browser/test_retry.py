import pytest

from peddler.browser.retry import retry_with_backoff


class _TransientError(Exception):
    pass


class _OtherError(Exception):
    pass


def _fake_sleep(delays):
    def sleep(seconds):
        delays.append(seconds)

    return sleep


def test_succeeds_on_first_attempt_no_delay():
    calls = []
    delays = []

    def operation():
        calls.append(1)
        return "ok"

    result = retry_with_backoff(operation, (_TransientError,), sleep=_fake_sleep(delays))

    assert result == "ok"
    assert len(calls) == 1
    assert delays == []


def test_fails_twice_then_succeeds_calls_three_times():
    calls = []
    delays = []

    def operation():
        calls.append(1)
        if len(calls) < 3:
            raise _TransientError("transient")
        return "ok"

    result = retry_with_backoff(operation, (_TransientError,), sleep=_fake_sleep(delays))

    assert result == "ok"
    assert len(calls) == 3
    assert len(delays) == 2


def test_fails_all_attempts_reraises_same_exception_type():
    calls = []
    delays = []

    def operation():
        calls.append(1)
        raise _TransientError("still failing")

    with pytest.raises(_TransientError):
        retry_with_backoff(operation, (_TransientError,), sleep=_fake_sleep(delays))

    assert len(calls) == 3
    assert len(delays) == 2


def test_non_transient_exception_propagates_immediately_no_delay():
    calls = []
    delays = []

    def operation():
        calls.append(1)
        raise _OtherError("not transient")

    with pytest.raises(_OtherError):
        retry_with_backoff(operation, (_TransientError,), sleep=_fake_sleep(delays))

    assert len(calls) == 1
    assert delays == []


def test_attempts_is_configurable():
    calls = []
    delays = []

    def operation():
        calls.append(1)
        raise _TransientError("always fails")

    with pytest.raises(_TransientError):
        retry_with_backoff(operation, (_TransientError,), attempts=5, sleep=_fake_sleep(delays))

    assert len(calls) == 5
    assert len(delays) == 4
