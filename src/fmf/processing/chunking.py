from __future__ import annotations

import re
from typing import List

from ..core.ids import chunk_id as compute_chunk_id
from ..types import Chunk


def _split_sentences(text: str) -> List[str]:
    # Naive sentence splitter on punctuation followed by space/newline
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    # keep non-empty parts
    return [p.strip() for p in parts if p.strip()]


def _split_paragraphs(text: str) -> List[str]:
    parts = re.split(r"\n\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def estimate_tokens(text: str) -> int:
    # Rough estimate: number of word-like tokens
    return max(1, len(re.findall(r"\w+", text)))


def chunk_text(
    *,
    doc_id: str,
    text: str,
    max_tokens: int = 800,
    overlap: int = 150,
    splitter: str = "by_sentence",
) -> List[Chunk]:
    if splitter == "by_paragraph":
        units = _split_paragraphs(text)
    elif splitter == "none":
        units = [text]
    else:
        units = _split_sentences(text)

    chunks: List[Chunk] = []
    cur_parts: List[str] = []
    cur_tokens = 0
    cid = 0
    for u in units:
        u_tokens = estimate_tokens(u)
        if cur_tokens + u_tokens > max_tokens and cur_parts:
            chunk_text_val = " ".join(cur_parts).strip()
            chunk_identifier = compute_chunk_id(document_id=doc_id, index=cid, payload=chunk_text_val)
            chunks.append(
                Chunk(
                    id=chunk_identifier,
                    doc_id=doc_id,
                    text=chunk_text_val,
                    tokens_estimate=estimate_tokens(chunk_text_val),
                    provenance={"index": cid, "splitter": splitter, "length_chars": len(chunk_text_val)},
                )
            )
            cid += 1
            # start new chunk with overlap from end of previous
            if overlap > 0 and chunks[-1].text:
                prev_words = re.findall(r"\S+", chunks[-1].text)
                carry = " ".join(prev_words[-overlap:]) if prev_words else ""
                cur_parts = [carry] if carry else []
                cur_tokens = estimate_tokens(" ".join(cur_parts)) if cur_parts else 0
            else:
                cur_parts = []
                cur_tokens = 0

        cur_parts.append(u)
        cur_tokens += u_tokens

    if cur_parts:
        chunk_text_val = " ".join(cur_parts).strip()
        chunk_identifier = compute_chunk_id(document_id=doc_id, index=cid, payload=chunk_text_val)
        chunks.append(
            Chunk(
                id=chunk_identifier,
                doc_id=doc_id,
                text=chunk_text_val,
                tokens_estimate=estimate_tokens(chunk_text_val),
                provenance={"index": cid, "splitter": splitter, "length_chars": len(chunk_text_val)},
            )
        )

    return chunks


__all__ = ["chunk_text", "estimate_tokens"]
