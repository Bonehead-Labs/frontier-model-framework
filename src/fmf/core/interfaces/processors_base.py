from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from pydantic import BaseModel, Field

from .models import ChunkModel, DocumentModel, ProcessingSpec, RunContext


class ProcessorRequest(BaseModel):
    """Input contract for processors."""

    document: DocumentModel
    context: RunContext | None = None
    spec: ProcessingSpec | None = None


class ProcessorResult(BaseModel):
    """Output contract for processors."""

    document: DocumentModel
    chunks: list[ChunkModel] = Field(default_factory=list)
    artefacts: list[str] = Field(default_factory=list)


class BaseProcessor(ABC):
    """Abstract processor with a uniform entry point."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def process(self, request: ProcessorRequest) -> ProcessorResult:
        """Process an input document into zero or more chunks."""

    def expand_documents(self, request: ProcessorRequest) -> Iterable[DocumentModel]:  # pragma: no cover - optional override
        """Optional hook for processors that yield additional documents (e.g., tables)."""

        yield request.document


__all__ = ["BaseProcessor", "ProcessorRequest", "ProcessorResult"]
