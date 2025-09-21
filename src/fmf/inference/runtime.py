from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal, Tuple

from .base_client import Completion, LLMClient, Message
from ..core.errors import InferenceError, ProviderError

InferenceMode = Literal["auto", "regular", "stream"]
DEFAULT_MODE: InferenceMode = "auto"


@dataclass
class InferenceTelemetry:
    streaming: bool
    selected_mode: InferenceMode
    fallback_reason: str | None
    time_to_first_byte_ms: int
    latency_ms: int
    chunk_count: int
    tokens_out: int | None
    retries: int


class _StreamRecorder:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.chunks: list[str] = []
        self.first_token_time: float | None = None

    def callback(self, token: str) -> None:
        now = time.perf_counter()
        if self.first_token_time is None:
            self.first_token_time = now
        self.chunks.append(token)


def normalize_mode(value: str | None) -> InferenceMode:
    if not value:
        return DEFAULT_MODE
    lower = value.strip().lower()
    if lower in {"auto", "default"}:
        return "auto"
    if lower in {"regular", "sync", "standard"}:
        return "regular"
    if lower in {"stream", "streaming"}:
        return "stream"
    raise ValueError(f"Unsupported inference mode: {value!r}")


def _supports_streaming(client: Any) -> bool:
    attr = getattr(client, "supports_streaming", None)
    if callable(attr):
        try:
            return bool(attr())
        except Exception:
            return False
    return False


def invoke_with_mode(
    client: LLMClient,
    messages: list[Message],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    mode: InferenceMode = DEFAULT_MODE,
    provider_name: str | None = None,
) -> Tuple[Completion, InferenceTelemetry]:
    requested_mode = normalize_mode(mode)
    supports_stream = _supports_streaming(client)

    resolved_mode: InferenceMode = requested_mode
    fallback_reason: str | None = None
    use_stream = False

    if requested_mode == "stream":
        if not supports_stream:
            raise ProviderError(
                f"Streaming is not supported by provider {provider_name or ''}".strip(),
                status_code=None,
            )
        use_stream = True
    elif requested_mode == "auto":
        if supports_stream:
            use_stream = True
        else:
            resolved_mode = "regular"
            fallback_reason = "streaming_unsupported"
    else:
        resolved_mode = "regular"

    start = time.perf_counter()
    recorder = _StreamRecorder()

    def _call_stream() -> Completion:
        recorder.reset()
        return client.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            on_token=recorder.callback,
        )

    def _call_regular() -> Completion:
        return client.complete(messages, temperature=temperature, max_tokens=max_tokens, stream=False)

    completion: Completion | None = None
    ttfb = 0.0
    latency = 0.0
    chunk_count = 0
    total_retries = 0

    if use_stream:
        try:
            completion = _call_stream()
            total_retries += int(getattr(client, "_last_retries", 0))
        except InferenceError as err:
            if requested_mode == "auto":
                # Fallback gracefully to regular mode
                fallback_reason = f"stream_error:{getattr(err, 'status_code', 'unknown')}"
                resolved_mode = "regular"
                use_stream = False
                completion = None
                total_retries += int(getattr(client, "_last_retries", 0))
            else:
                raise ProviderError(
                    f"Streaming request failed: {err}",
                    status_code=getattr(err, "status_code", None),
                ) from err

    if completion is None:
        completion = _call_regular()
        total_retries += int(getattr(client, "_last_retries", 0))
        use_stream = False

    end = time.perf_counter()
    latency = end - start
    first_token_time = recorder.first_token_time if use_stream else None
    if first_token_time is None:
        first_token_time = end
    ttfb = first_token_time - start
    chunk_count = len(recorder.chunks) if use_stream else (1 if completion.text else 0)

    tokens_out = getattr(completion, "completion_tokens", None)
    telemetry = InferenceTelemetry(
        streaming=use_stream,
        selected_mode=resolved_mode,
        fallback_reason=fallback_reason,
        time_to_first_byte_ms=int(max(ttfb, 0) * 1000),
        latency_ms=int(max(latency, 0) * 1000),
        chunk_count=chunk_count,
        tokens_out=tokens_out if isinstance(tokens_out, (int, float)) else None,
        retries=total_retries,
    )
    return completion, telemetry


__all__ = [
    "InferenceMode",
    "InferenceTelemetry",
    "DEFAULT_MODE",
    "normalize_mode",
    "invoke_with_mode",
]
