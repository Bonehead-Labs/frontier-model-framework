from __future__ import annotations

import random
import time
from typing import Any, Callable, Optional


RetryPredicate = Callable[[BaseException], bool]


def _call_label(func: Callable[..., Any]) -> str:
    name = getattr(func, "__name__", "")
    if name:
        return name
    cls = getattr(func, "__class__", None)
    if cls and getattr(cls, "__name__", None):
        return cls.__name__
    return "call"


def _record_retry_metric(suffix: str, func_label: str, *, value: float = 1.0) -> None:
    metric_name = f"retry.{suffix}"
    try:
        from ..observability import metrics as _metrics

        _metrics.inc(metric_name, value)
        if func_label:
            _metrics.inc(f"{metric_name}.{func_label}", value)
    except Exception:
        # Metrics MUST NOT affect control flow; swallow all errors.
        pass


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
    func_label = _call_label(func)
    while attempts < max_attempts:
        try:
            result = func(*args, **(kwargs or {}))
            _record_retry_metric("success", func_label)
            if attempts:
                _record_retry_metric("success.after_retry", func_label)
            return result
        except BaseException as exc:  # pragma: no cover - fully exercised in tests
            last_exc = exc
            attempts += 1
            _record_retry_metric("attempts", func_label)
            if not predicate(exc):
                _record_retry_metric("failures", func_label)
                raise
            elapsed = now() - start
            if attempts >= max_attempts or elapsed >= max_elapsed:
                _record_retry_metric("failures", func_label)
                raise
            max_window = max(base_delay, delay * 3)
            delay = min(max_delay, random.uniform(base_delay, max_window))
            if elapsed + delay > max_elapsed:
                _record_retry_metric("failures", func_label)
                raise
            _record_retry_metric("sleep_seconds", func_label, value=delay)
            sleep(delay)
    if last_exc is not None:
        _record_retry_metric("failures", func_label)
        raise last_exc
    return func(*args, **(kwargs or {}))


__all__ = ["retry_call", "default_predicate"]
