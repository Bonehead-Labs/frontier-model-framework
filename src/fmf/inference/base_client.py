from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Literal, Optional, Protocol

from ..core.errors import InferenceError


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    # content can be plain text or a list of multimodal parts
    # parts: {"type": "text", "text": str} | {"type": "image_url", "url": str} | {"type": "image_base64", "data": str, "media_type": str}
    content: Any


@dataclass
class Completion:
    text: str
    model: Optional[str] = None
    stop_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
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


def with_retries(
    func: Callable[[], Completion],
    *,
    retries: int = 3,
    base_delay: float = 0.2,
    record_attempts: dict[str, int] | None = None,
) -> Completion:
    delay = base_delay
    last_exc: Exception | None = None
    attempts_made = 0
    for attempt in range(retries + 1):
        try:
            result = func()
            if record_attempts is not None:
                record_attempts["retries"] = attempts_made
            return result
        except Exception as e:  # pragma: no cover - timing dependent
            last_exc = e
            if not should_retry(e) or attempt == retries:
                if record_attempts is not None:
                    record_attempts["retries"] = attempts_made
                if isinstance(e, InferenceError):
                    raise
                raise InferenceError(str(e), status_code=getattr(e, "status_code", None))
            try:
                # best-effort increment of retry metric
                from ..observability import metrics  # type: ignore

                metrics.inc("retries", 1)
            except Exception:
                pass
            attempts_made += 1
            time.sleep(delay)
            delay = min(delay * 2, 2.0)
    assert last_exc is not None
    if record_attempts is not None:
        record_attempts["retries"] = attempts_made
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
