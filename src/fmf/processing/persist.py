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


def update_index(artefacts_dir: str, entry: dict) -> None:
    """Append or merge an entry into artefacts/index.json listing runs."""
    import json

    index_path = os.path.join(artefacts_dir, "index.json")
    data = {"runs": []}
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f) or data
        except Exception:
            data = {"runs": []}
    # deduplicate by run_id
    runs = data.setdefault("runs", [])
    runs = [r for r in runs if r.get("run_id") != entry.get("run_id")]
    runs.append(entry)
    data["runs"] = runs
    ensure_dir(artefacts_dir)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def apply_retention(artefacts_dir: str, retain_last: int) -> None:
    """Keep only the latest N run directories; remove older ones.

    Determines order by directory mtime to avoid relying on naming.
    """
    if retain_last <= 0:
        return
    if not os.path.isdir(artefacts_dir):
        return
    entries = []
    for name in os.listdir(artefacts_dir):
        p = os.path.join(artefacts_dir, name)
        if os.path.isdir(p) and name not in {"index.json"}:
            try:
                st = os.stat(p)
                entries.append((st.st_mtime, p))
            except Exception:
                continue
    entries.sort(reverse=True)
    for _mtime, path in entries[retain_last:]:
        try:
            # remove directory recursively
            import shutil

            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            continue



__all__ = ["persist_artefacts"]
