from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from pydantic import BaseModel, Field

from ...inference.base_client import Completion
from .models import ChatMessageModel, ModelSpec, RunContext


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

    def stream(
        self,
        request: CompletionRequest,
        on_token: Callable[[str], None],
    ) -> CompletionResponse:  # pragma: no cover - default fallback
        """Optional streaming handler; falls back to non-streaming invocation."""

        response = self.complete(request)
        if response.text:
            on_token(response.text)
        return response

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:  # pragma: no cover - optional override
        raise NotImplementedError("Provider does not implement embeddings")

    def supports_streaming(self) -> bool:
        return bool(self.spec.streaming.enabled)

    def supports_embeddings(self) -> bool:
        return "embeddings" in {cap.lower() for cap in self.spec.capabilities}


__all__ = [
    "BaseProvider",
    "CompletionRequest",
    "CompletionResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
]
