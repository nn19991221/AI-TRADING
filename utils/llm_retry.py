from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import logging
from typing import Callable, TypeVar


T = TypeVar('T')

RETRY_ATTEMPTS = 3
TIMEOUT_SECONDS = 10


def execute_with_retry(
    task_fn: Callable[[], T],
    fallback_fn: Callable[[], T],
    *,
    retries: int = RETRY_ATTEMPTS,
    timeout_seconds: int = TIMEOUT_SECONDS,
) -> T:
    last_error: Exception | None = None
    attempts = max(1, int(retries))

    for attempt in range(1, attempts + 1):
        try:
            return _run_with_timeout(task_fn, timeout_seconds=timeout_seconds)
        except Exception as exc:
            last_error = exc
            logging.warning('LLM call attempt %s/%s failed: %s', attempt, attempts, exc)

    logging.error('LLM call failed after %s attempts. Using fallback. Last error: %s', attempts, last_error)
    return fallback_fn()


def _run_with_timeout(task_fn: Callable[[], T], timeout_seconds: int) -> T:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(task_fn)
        try:
            return future.result(timeout=max(1, int(timeout_seconds)))
        except FuturesTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f'LLM call timed out after {timeout_seconds} seconds') from exc

