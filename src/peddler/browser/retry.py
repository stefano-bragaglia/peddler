"""Generic retry-with-backoff wrapper for transient, crash-prone operations."""

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry_with_backoff(
    operation: Callable[[], T],
    transient_exceptions: tuple[type[Exception], ...],
    attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``operation``, retrying with exponential backoff on transient failures.

    :param operation: The zero-arg callable to attempt.
    :type operation: Callable[[], T]
    :param transient_exceptions: Exception types that should trigger a
        retry. Any other exception propagates immediately, with no
        retry and no delay.
    :type transient_exceptions: tuple[type[Exception], ...]
    :param attempts: The maximum number of attempts.
    :type attempts: int
    :param sleep: The delay function called between attempts (injectable
        so tests don't incur real delays).
    :type sleep: Callable[[float], None]
    :returns: The operation's return value, from whichever attempt
        succeeded first.
    :rtype: T
    :raises Exception: The original exception, unchanged, if every
        attempt raises a transient exception.
    """
    delay = 0.5
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except transient_exceptions:
            if attempt == attempts:
                raise
            sleep(delay)
            delay *= 2
