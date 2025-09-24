from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


class RunContext(BaseModel):
    """Lightweight context passed between layers for observability and profiles."""

    run_id: str | None = None
    profile: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    config_hash: str | None = None


class BlobModel(BaseModel):
    """Binary artefact attached to a document (e.g. image bytes)."""

    id: str = Field(default_factory=lambda: f"blob_{uuid.uuid4().hex[:8]}")
    media_type: str
    data: bytes | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentModel(BaseModel):
    """Normalized document emitted by the processing layer."""

    id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    source_uri: str
    text: str | None = None
    blobs: list[BlobModel] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkModel(BaseModel):
    """Token-aware chunk derived from a document."""

    id: str = Field(default_factory=lambda: f"chunk_{uuid.uuid4().hex[:8]}")
    doc_id: str
    text: str
    tokens_estimate: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorSelectors(BaseModel):
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class ConnectorSpec(BaseModel):
    """Configuration required to construct a connector."""

    name: str
    type: str
    description: str | None = None
    selectors: ConnectorSelectors = Field(default_factory=ConnectorSelectors)
    options: dict[str, Any] = Field(default_factory=dict)
    auth_profile: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessingSpec(BaseModel):
    """Processing configuration captured for reproducibility."""

    name: str
    strategy: Literal["text", "table", "image", "audio", "custom"]
    options: dict[str, Any] = Field(default_factory=dict)


class ChatMessageModel(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Any


class StreamingConfig(BaseModel):
    enabled: bool = False
    chunk_size_tokens: int | None = None


class ModelPricing(BaseModel):
    unit: Literal["1K_tokens", "image", "request", "invocation", "custom"] = "1K_tokens"
    currency: Literal["USD", "credits", "custom"] = "USD"
    input_cost: float | None = None
    output_cost: float | None = None
    notes: str | None = None


class ModelSpec(BaseModel):
    """Provider-agnostic description of a model deployment."""

    provider: str
    model: str
    modality: Literal["text", "multimodal", "embedding", "audio", "vision"] = "text"
    tasks: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    default_params: dict[str, Any] = Field(default_factory=dict)
    streaming: StreamingConfig = Field(default_factory=StreamingConfig)
    pricing: ModelPricing | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ExportSpec(BaseModel):
    """Standardised exporter configuration."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: str
    destination: str | None = None
    format: Literal["jsonl", "csv", "parquet", "delta", "excel", "native", "custom"] = "jsonl"
    write_mode: Literal["append", "upsert", "overwrite"] = Field("append", alias="mode")
    key_fields: list[str] | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def mode(self) -> str:
        return self.write_mode


__all__ = [
    "BlobModel",
    "DocumentModel",
    "ChunkModel",
    "ConnectorSpec",
    "ProcessingSpec",
    "ChatMessageModel",
    "StreamingConfig",
    "ModelPricing",
    "ModelSpec",
    "ExportSpec",
    "RunContext",
]
