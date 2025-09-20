from __future__ import annotations

from typing import Any

from ....core.interfaces import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelSpec,
)
from ....inference.base_client import Completion, with_retries


class TemplateProvider(BaseProvider):
    """Skeleton adapter showing the minimum hooks for a new provider."""

    def __init__(self, spec: ModelSpec, *, client: Any | None = None) -> None:
        super().__init__(spec)
        # Store any provider-specific SDK client for reuse by subclasses.
        self._client = client

    def _invoke_completion(self, request: CompletionRequest) -> Completion:
        """Translate the unified request into the provider SDK call.

        Replace the NotImplementedError with the provider-specific call. The
        method MUST return an ``fmf.inference.base_client.Completion`` instance.
        """

        raise NotImplementedError("TemplateProvider requires provider-specific implementation")

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        completion = with_retries(lambda: self._invoke_completion(request))
        return CompletionResponse.from_completion(completion)

    def stream(self, request: CompletionRequest, on_token) -> CompletionResponse:
        if not self.supports_streaming():
            return super().stream(request, on_token)
        completion = with_retries(lambda: self._invoke_completion(request))
        text = completion.text or ""
        for token in text.split():
            on_token(token)
        return CompletionResponse.from_completion(completion)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        raise NotImplementedError("TemplateProvider does not implement embeddings yet")

    def supports_streaming(self) -> bool:
        return bool(self.spec.streaming.enabled)
