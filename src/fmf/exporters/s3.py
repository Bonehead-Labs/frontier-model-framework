from __future__ import annotations

import datetime as dt
import gzip
import io
import json
import os
import uuid
from typing import Any, Iterable

from .base import ExportError, ExportResult


def _now_date():
    return dt.datetime.utcnow().strftime("%Y-%m-%d")


class S3Exporter:
    def __init__(
        self,
        *,
        name: str,
        bucket: str,
        prefix: str | None = None,
        format: str | None = "jsonl",
        compression: str | None = None,
        partition_by: list[str] | None = None,
        sse: str | None = None,
        kms_key_id: str | None = None,
    ) -> None:
        self.name = name
        self.bucket = bucket
        self.prefix = prefix or ""
        self.format = (format or "jsonl").lower()
        self.compression = (compression or "none").lower()
        self.partition_by = partition_by or []
        self.sse = sse
        self.kms_key_id = kms_key_id
        self._client = None

    def _s3(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore
        except Exception as e:
            raise ExportError("boto3 not installed. Install extras: pip install '.[aws]'") from e
        self._client = boto3.client("s3")
        return self._client

    def _build_key(self, *, context: dict[str, Any] | None) -> str:
        run_id = (context or {}).get("run_id") or dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        prefix = (self.prefix or "").replace("${run_id}", run_id)
        parts = [prefix.rstrip("/")]
        if "date" in (self.partition_by or []):
            parts.append(f"date={_now_date()}")
        # unique object name for append semantics
        ext = ".jsonl" if self.format == "jsonl" else ".bin"
        if self.compression == "gzip":
            ext += ".gz"
        parts.append(f"part-{uuid.uuid4().hex}{ext}")
        return "/".join([p for p in parts if p])

    def _serialize(self, recs: Iterable[dict[str, Any]] | bytes | str) -> bytes:
        if isinstance(recs, bytes):
            data = recs
        elif isinstance(recs, str):
            data = recs.encode("utf-8")
        else:
            # assume iterable of dicts -> jsonl
            buf = io.StringIO()
            count = 0
            for r in recs:
                buf.write(json.dumps(r, ensure_ascii=False) + "\n")
                count += 1
            data = buf.getvalue().encode("utf-8")
        if self.compression == "gzip":
            return gzip.compress(data)
        return data

    def write(
        self,
        records: Iterable[dict[str, Any]] | bytes | str,
        *,
        schema: dict[str, Any] | None = None,
        mode: str = "append",
        key_fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExportResult:
        key = self._build_key(context=context)
        data = self._serialize(records)
        kwargs = {"Bucket": self.bucket, "Key": key, "Body": data}
        if self.sse == "kms":
            kwargs["ServerSideEncryption"] = "aws:kms"
            if self.kms_key_id:
                kwargs["SSEKMSKeyId"] = self.kms_key_id
        elif self.sse == "s3":
            kwargs["ServerSideEncryption"] = "AES256"
        self._s3().put_object(**kwargs)
        return ExportResult(count=-1, paths=[f"s3://{self.bucket}/{key}"])

    def finalize(self) -> None:
        return None


__all__ = ["S3Exporter"]

