"""Common interface definitions for the Frontier Model Framework core layers.

These interfaces provide a lightweight contract for new connectors, processors,
providers, and exporters. Existing concrete implementations can progressively
adopt them without breaking backwards compatibility.
"""

from .models import (
    ConnectorSpec,
    ConnectorSelectors,
    DocumentModel,
    ChunkModel,
    ModelSpec,
    ExportSpec,
    RunContext,
)
from .connectors_base import BaseConnector
from .processors_base import BaseProcessor, ProcessorRequest, ProcessorResult
from .providers_base import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from .exporters_base import BaseExporter

__all__ = [
    "BaseConnector",
    "BaseProcessor",
    "ProcessorRequest",
    "ProcessorResult",
    "BaseProvider",
    "CompletionRequest",
    "CompletionResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "BaseExporter",
    "ConnectorSpec",
    "ConnectorSelectors",
    "DocumentModel",
    "ChunkModel",
    "ModelSpec",
    "ExportSpec",
    "RunContext",
]
