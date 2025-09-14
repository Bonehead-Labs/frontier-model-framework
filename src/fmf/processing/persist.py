from __future__ import annotations

import json
import os
from typing import Iterable

from ..types import Document, Chunk


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_jsonl(path: str, records: Iterable[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def persist_artefacts(
    *, artefacts_dir: str, run_id: str, documents: list[Document], chunks: list[Chunk]
) -> dict[str, str]:
    run_dir = os.path.join(artefacts_dir, run_id)
    ensure_dir(run_dir)
    docs_path = os.path.join(run_dir, "docs.jsonl")
    chunks_path = os.path.join(run_dir, "chunks.jsonl")
    write_jsonl(docs_path, (d.to_serializable() for d in documents))
    write_jsonl(chunks_path, (c.to_serializable() for c in chunks))
    return {"docs": docs_path, "chunks": chunks_path}


__all__ = ["persist_artefacts"]

