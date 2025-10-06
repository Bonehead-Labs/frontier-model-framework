from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _gen_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class Blob:
    id: str
    media_type: str
    data: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def with_id(self, new_id: str) -> "Blob":
        self.id = new_id
        return self

    def to_serializable(self) -> Dict[str, Any]:
        d = dict(id=self.id, media_type=self.media_type, metadata=self.metadata)
        if self.data is not None:
            d["size_bytes"] = len(self.data)
            # omit raw data from JSON; include a content hash for reproducibility
            d["sha256"] = hashlib.sha256(self.data).hexdigest()
        return d


@dataclass
class Document:
    id: str
    source_uri: str
    text: Optional[str] = None
    blobs: Optional[List[Blob]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def clear_content(self) -> None:
        """Clear heavy content (text and blobs) to free memory while preserving metadata."""
        self.text = None
        self.blobs = None

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_uri": self.source_uri,
            "text": self.text,
            "blobs": [b.to_serializable() for b in (self.blobs or [])],
            "metadata": self.metadata,
            "provenance": self.provenance,
        }


@dataclass
class Chunk:
    id: str
    doc_id: str
    text: str
    tokens_estimate: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "text": self.text,
            "tokens_estimate": self.tokens_estimate,
            "metadata": self.metadata,
            "provenance": self.provenance,
        }


__all__ = ["Blob", "Document", "Chunk"]
