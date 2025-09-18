from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ..connectors import build_connector
from ..processing.chunking import chunk_text
from ..processing.loaders import load_document_from_bytes
from ..types import Chunk, Document


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> Counter[str]:
    words = _TOKEN_PATTERN.findall(text.lower())
    return Counter(words)


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a if k in b)
    if dot == 0:
        return 0.0
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class RagTextItem:
    id: str
    source_uri: str
    content: str
    tokens: Counter[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_uri": self.source_uri,
            "content": self.content,
            "metadata": self.metadata,
        }


@dataclass
class RagImageItem:
    id: str
    source_uri: str
    media_type: str
    data: bytes
    tokens: Counter[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_record(self, include_data: bool = False) -> Dict[str, Any]:
        rec = {
            "id": self.id,
            "source_uri": self.source_uri,
            "media_type": self.media_type,
            "metadata": self.metadata,
        }
        if include_data:
            rec["data_base64"] = self.data
        return rec


@dataclass
class RagResult:
    query: str
    texts: List[RagTextItem]
    images: List[RagImageItem]

    def to_record(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "texts": [t.to_record() for t in self.texts],
            "images": [i.to_record(include_data=False) for i in self.images],
        }


@dataclass
class RagPipeline:
    name: str
    text_items: List[RagTextItem] = field(default_factory=list)
    image_items: List[RagImageItem] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def retrieve(
        self,
        query: str,
        *,
        top_k_text: int = 3,
        top_k_images: int = 0,
    ) -> RagResult:
        q_tokens = _tokenize(query)
        text_hits: List[RagTextItem] = []
        if top_k_text > 0:
            scored = sorted(
                ((item, _cosine(q_tokens, item.tokens)) for item in self.text_items),
                key=lambda item_score: item_score[1],
                reverse=True,
            )
            text_hits = [item for item, score in scored[:top_k_text] if score > 0]
        image_hits: List[RagImageItem] = []
        if top_k_images > 0:
            scored_imgs = sorted(
                ((item, _cosine(q_tokens, item.tokens)) for item in self.image_items),
                key=lambda item_score: item_score[1],
                reverse=True,
            )
            image_hits = [item for item, score in scored_imgs[:top_k_images] if score > 0]
        result = RagResult(query=query, texts=text_hits, images=image_hits)
        self.history.append(result.to_record())
        return result

    def format_text_block(self, items: Iterable[RagTextItem]) -> str:
        lines = []
        for idx, item in enumerate(items, start=1):
            lines.append(f"[{idx}] {item.content}")
            src = item.metadata.get("source_uri") or item.source_uri
            if src:
                lines.append(f"    source: {src}")
        return os.linesep.join(lines)

    def image_data_urls(self, items: Iterable[RagImageItem]) -> List[str]:
        import base64

        urls: List[str] = []
        for item in items:
            b64 = base64.b64encode(item.data).decode("ascii")
            urls.append(f"data:{item.media_type};base64,{b64}")
        return urls


def _cfg_get(cfg: object | None, key: str, default=None):
    if cfg is None:
        return default
    if isinstance(cfg, dict):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


def build_rag_pipelines(
    rag_cfg: object | None,
    *,
    connectors: Iterable[object] | None,
    processing_cfg: object | None,
) -> Dict[str, RagPipeline]:
    pipelines: Dict[str, RagPipeline] = {}
    if rag_cfg is None:
        return pipelines
    entries = _cfg_get(rag_cfg, "pipelines", None) or []
    connector_list = list(connectors or [])
    by_name = {(_cfg_get(c, "name")): c for c in connector_list if _cfg_get(c, "name")}
    for entry in entries:
        name = _cfg_get(entry, "name")
        connector_name = _cfg_get(entry, "connector")
        if not name or not connector_name:
            continue
        connector_cfg = by_name.get(connector_name)
        if connector_cfg is None:
            raise ValueError(f"RAG pipeline {name!r} references unknown connector {connector_name!r}")
        pipeline = _build_single_pipeline(entry, connector_cfg, processing_cfg)
        pipelines[name] = pipeline
    return pipelines


def _build_single_pipeline(entry, connector_cfg, processing_cfg) -> RagPipeline:
    name = _cfg_get(entry, "name")
    modalities = _cfg_get(entry, "modalities", None) or ["text"]
    max_text_items = _cfg_get(entry, "max_text_items")
    max_image_items = _cfg_get(entry, "max_image_items")
    select = _cfg_get(entry, "select")

    connector = build_connector(connector_cfg)
    text_items: List[RagTextItem] = []
    image_items: List[RagImageItem] = []

    text_cfg = _cfg_get(processing_cfg, "text") if processing_cfg is not None else None
    chunk_cfg = _cfg_get(text_cfg, "chunking") if text_cfg is not None else None
    max_tokens = _cfg_get(chunk_cfg, "max_tokens", 800)
    overlap = _cfg_get(chunk_cfg, "overlap", 150)
    splitter = _cfg_get(chunk_cfg, "splitter", "by_sentence")

    include_text = "text" in modalities or "both" in modalities
    include_images = "image" in modalities or "both" in modalities

    count_text = 0
    count_images = 0
    for ref in connector.list(selector=select):
        with connector.open(ref, mode="rb") as fh:
            data = fh.read()
        doc = load_document_from_bytes(
            source_uri=ref.uri,
            filename=ref.name,
            data=data,
            processing_cfg=processing_cfg,
        )
        if include_text and doc.text:
            text_chunks = _doc_to_chunks(doc, max_tokens=max_tokens, overlap=overlap, splitter=splitter)
            for chunk in text_chunks:
                if max_text_items is not None and count_text >= max_text_items:
                    break
                tokens = _tokenize(chunk.text)
                metadata = {**doc.metadata, "doc_id": doc.id, "source_uri": doc.source_uri}
                text_items.append(
                    RagTextItem(
                        id=chunk.id,
                        source_uri=doc.source_uri,
                        content=chunk.text,
                        tokens=tokens,
                        metadata=metadata,
                    )
                )
                count_text += 1
        if include_images and doc.blobs:
            for blob in doc.blobs:
                if max_image_items is not None and count_images >= max_image_items:
                    break
                text_repr = doc.text or doc.metadata.get("filename") or blob.id
                tokens = _tokenize(text_repr)
                image_items.append(
                    RagImageItem(
                        id=f"{doc.id}:{blob.id}",
                        source_uri=doc.source_uri,
                        media_type=blob.media_type,
                        data=blob.data or b"",
                        tokens=tokens,
                        metadata={**doc.metadata, "doc_id": doc.id, "blob_id": blob.id},
                    )
                )
                count_images += 1
    return RagPipeline(name=name, text_items=text_items, image_items=image_items)


def _doc_to_chunks(
    doc: Document,
    *,
    max_tokens: int,
    overlap: int,
    splitter: str,
) -> List[Chunk]:
    if not doc.text:
        return []
    return chunk_text(doc_id=doc.id, text=doc.text, max_tokens=max_tokens, overlap=overlap, splitter=splitter)

