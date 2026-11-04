"""Generic retry decorator with explicit wait intervals."""

import functools
import logging
import time
from collections.abc import Callable, Sequence
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)

DEFAULT_DELAYS: tuple[float, ...] = (2.0, 6.0)


def retry(
    delays: Sequence[float] = DEFAULT_DELAYS,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry a function when it raises one of the given exceptions.

    The function is called once and, on failure, once more after each wait
    interval. With the default ``(2, 6)`` there are up to three attempts in
    total, waiting 2 and 6 seconds between them. When every attempt fails
    the last exception is re-raised.

    Args:
        delays: Seconds to wait before each retry, in order.
        exceptions: Exception types that trigger a retry. Any other exception
            propagates immediately.
        sleep: Function used to wait. Injectable so tests do not wait.

    Returns:
        A decorator that adds the retry behaviour to a function.

    Example:
        >>> @retry(delays=(1, 2), exceptions=(TimeoutError,))
        ... def call_service() -> str: ...
    """
    waits = tuple(delays)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            total_attempts = len(waits) + 1
            for attempt in range(1, total_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == total_attempts:
                        logger.warning(
                            "retry exhausted",
                            extra={"function": func.__qualname__, "attempts": attempt},
                        )
                        raise
                    wait = waits[attempt - 1]
                    logger.info(
                        "retrying after failure",
                        extra={
                            "function": func.__qualname__,
                            "attempt": attempt,
                            "wait_seconds": wait,
                            "error": str(exc),
                        },
                    )
                    sleep(wait)
            raise RuntimeError("unreachable")  # pragma: no cover

        return wrapper

    return decorator
