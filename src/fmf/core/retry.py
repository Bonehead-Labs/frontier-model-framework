from __future__ import annotations

import random
import time
from typing import Any, Callable, Optional


RetryPredicate = Callable[[BaseException], bool]


def default_predicate(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            status = response.get("status_code") or response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return status in {429} or (isinstance(status, int) and 500 <= status < 600)


def retry_call(
    func: Callable[..., Any],
    *,
    args: tuple[Any, ...] = (),
    kwargs: Optional[dict[str, Any]] = None,
    should_retry: Optional[RetryPredicate] = None,
    max_attempts: int = 5,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
    max_elapsed: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> Any:
    """Retry ``func`` with decorrelated jitter until success or limits exceeded."""

    predicate = should_retry or default_predicate
    attempts = 0
    start = now()
    delay = base_delay
    last_exc: Optional[BaseException] = None
    while attempts < max_attempts:
        try:
            return func(*args, **(kwargs or {}))
        except BaseException as exc:  # pragma: no cover - fully exercised in tests
            last_exc = exc
            attempts += 1
            if not predicate(exc):
                raise
            elapsed = now() - start
            if attempts >= max_attempts or elapsed >= max_elapsed:
                raise
            max_window = max(base_delay, delay * 3)
            delay = min(max_delay, random.uniform(base_delay, max_window))
            if elapsed + delay > max_elapsed:
                raise
            sleep(delay)
    if last_exc is not None:
        raise last_exc
    return func(*args, **(kwargs or {}))


__all__ = ["retry_call", "default_predicate"]
