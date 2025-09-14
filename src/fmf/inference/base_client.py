from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable, Literal, Optional, Protocol


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class Completion:
    text: str
    model: Optional[str] = None
    stop_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class InferenceError(Exception):
    """Raised on provider errors; may wrap HTTP or SDK errors."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class LLMClient(Protocol):
    def complete(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool | None = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Completion:
        ...


def should_retry(exc: Exception) -> bool:
    code = getattr(exc, "status_code", None)
    if code is None:
        resp = getattr(exc, "response", None)
        if isinstance(resp, dict):
            code = resp.get("status_code")
    # Retry on 429/5xx
    return code == 429 or (isinstance(code, int) and 500 <= code < 600)


def with_retries(func: Callable[[], Completion], *, retries: int = 3, base_delay: float = 0.2) -> Completion:
    delay = base_delay
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return func()
        except Exception as e:  # pragma: no cover - timing dependent
            last_exc = e
            if not should_retry(e) or attempt == retries:
                if isinstance(e, InferenceError):
                    raise
                raise InferenceError(str(e), status_code=getattr(e, "status_code", None))
            time.sleep(delay)
            delay = min(delay * 2, 2.0)
    assert last_exc is not None
    raise InferenceError(str(last_exc))


class RateLimiter:
    def __init__(self, rate_per_sec: float = 5.0) -> None:
        self._interval = 1.0 / max(rate_per_sec, 0.001)
        self._last = 0.0

    def wait(self) -> None:
        now = time.time()
        wait_for = self._last + self._interval - now
        if wait_for > 0:
            time.sleep(wait_for)
        self._last = time.time()


__all__ = [
    "Message",
    "Completion",
    "InferenceError",
    "LLMClient",
    "with_retries",
    "RateLimiter",
]
