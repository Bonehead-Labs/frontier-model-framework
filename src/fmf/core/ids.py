from __future__ import annotations

import hashlib
import os
import unicodedata
from datetime import datetime, timezone
from typing import Optional


def _hash_algo() -> str:
    return os.getenv("FMF_HASH_ALGO", "blake2b").lower()

def normalize_text(text: str) -> bytes:
    """Normalize textual content for hashing.

    - Canonicalises Unicode to NFC
    - Strips UTF-8 BOM if present
    - Converts Windows/Mac newlines to ``\n``
    - Returns UTF-8 encoded bytes
    """

    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    normalised = unicodedata.normalize("NFC", text)
    normalised = normalised.replace("\r\n", "\n").replace("\r", "\n")
    return normalised.encode("utf-8")


def hash_bytes(data: bytes, *, namespace: str = "", algo: str | None = None) -> str:
    algo = (algo or _hash_algo())
    if algo == "xxh64":  # optional fast hash
        try:
            import xxhash  # type: ignore

            h = xxhash.xxh64()
            if namespace:
                h.update(namespace.encode("utf-8"))
            h.update(data)
            return h.hexdigest()
        except Exception:
            algo = "blake2b"
    h = hashlib.blake2b(digest_size=16)
    if namespace:
        h.update(namespace.encode("utf-8"))
    h.update(data)
    return h.hexdigest()


def document_id(
    *,
    source_uri: str,
    payload: bytes,
    modified_at: Optional[str] = None,
    content_type: Optional[str] = None,
    content_length: Optional[int] = None,
) -> str:
    namespace = source_uri
    if modified_at:
        try:
            dt_value = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
        except ValueError:
            dt_value = datetime.now(timezone.utc)
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        namespace = f"{namespace}|{dt_value.astimezone(timezone.utc).isoformat()}"
    if content_type:
        namespace = f"{namespace}|mime={content_type}"
    if content_length is not None:
        namespace = f"{namespace}|len={content_length}"
    digest = hash_bytes(payload, namespace=namespace)
    return f"doc_{digest}"


def chunk_id(*, document_id: str, index: int, payload: str) -> str:
    namespace = f"{document_id}|{index}|len={len(payload)}"
    digest = hash_bytes(payload.encode("utf-8"), namespace=namespace)
    return f"{document_id}_ch_{digest[:12]}"


def blob_id(*, document_id: str, media_type: str, payload: bytes) -> str:
    namespace = f"{document_id}|{media_type}|len={len(payload)}"
    digest = hash_bytes(payload, namespace=namespace)
    return f"blob_{digest[:12]}"


def utc_now_iso() -> str:
    tz = os.getenv("FMF_LOG_TZ", "UTC").upper()
    zone = timezone.utc if tz in {"UTC", "Z"} else timezone.utc
    return datetime.now(zone).isoformat().replace("+00:00", "Z")


__all__ = [
    "hash_bytes",
    "normalize_text",
    "document_id",
    "chunk_id",
    "blob_id",
    "utc_now_iso",
]
