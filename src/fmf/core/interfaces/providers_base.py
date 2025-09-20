from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from pydantic import BaseModel, Field

from ...inference.base_client import Completion
from .models import ChatMessageModel, ModelSpec, RunContext


@dataclass
class TokenChunk:
    """Represents a streamed chunk with optional metadata."""

    text: str
    metadata: dict[str, Any] | None = None


class CompletionRequest(BaseModel):
    """Request payload for a text or multimodal completion."""

    messages: list[ChatMessageModel]
    params: dict[str, Any] = Field(default_factory=dict)
    context: RunContext | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompletionResponse(BaseModel):
    """Normalised completion response."""

    text: str
    raw: Any | None = None
    stop_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    model: str | None = None

    @classmethod
    def from_completion(cls, completion: Completion, *, raw: Any | None = None) -> "CompletionResponse":
        return cls(
            text=completion.text,
            raw=raw or completion,
            stop_reason=completion.stop_reason,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            model=completion.model,
        )


class EmbeddingRequest(BaseModel):
    inputs: list[str]
    params: dict[str, Any] = Field(default_factory=dict)
    context: RunContext | None = None


class EmbeddingResponse(BaseModel):
    vectors: list[list[float]]
    model: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract provider facade used by the unified inference layer."""

    spec: ModelSpec

    def __init__(self, spec: ModelSpec) -> None:
        self.spec = spec

    @abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a non-streaming completion."""

    def iter_tokens(self, request: CompletionRequest) -> Iterator[str]:  # pragma: no cover - overridable
        """Yield streaming chunks and convey the final :class:`CompletionResponse` via ``StopIteration.value``.

        Providers overriding this generator should ``yield`` each token (or chunk) and finally
        ``raise StopIteration(completion)`` so that :meth:`stream` can return the full
        :class:`CompletionResponse`. The default implementation delegates to :meth:`complete` and
        emits the full text as a single chunk.
        """

        response = self.complete(request)
        if response.text:
            yield TokenChunk(response.text)
        return response  # type: ignore[misc]

    def stream(
        self,
        request: CompletionRequest,
        on_token: Callable[[str], None],
    ) -> CompletionResponse:
        """Stream tokens to ``on_token`` and return the final :class:`CompletionResponse`.

        The generator returned by :meth:`iter_tokens` is consumed until exhaustion. Providers
        are expected to raise ``StopIteration`` with the final :class:`CompletionResponse`
        attached to ``StopIteration.value`` (see :pep:`380`). A fallback empty response is
        returned when no completion is supplied.
        """

        iterator = self.iter_tokens(request)
        completion: CompletionResponse | None = None
        while True:
            try:
                token = next(iterator)
            except StopIteration as stop:
                completion = stop.value if isinstance(stop.value, CompletionResponse) else completion
                break
            else:
                if isinstance(token, TokenChunk):
                    on_token(token.text)
                else:
                    on_token(token)
        return completion or CompletionResponse(text="")

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:  # pragma: no cover - optional override
        raise NotImplementedError("Provider does not implement embeddings")

    def supports_streaming(self) -> bool:
        return bool(self.spec.streaming.enabled)

    def supports_embeddings(self) -> bool:
        return "embeddings" in {cap.lower() for cap in self.spec.capabilities}


__all__ = [
    "TokenChunk",
    "BaseProvider",
    "CompletionRequest",
    "CompletionResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
]
