from __future__ import annotations

import datetime as dt
import gzip
import io
import json
import os
import uuid
from typing import Any, Iterable, List, Dict

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
        if self.format == "jsonl":
            ext = ".jsonl"
        elif self.format == "csv":
            ext = ".csv"
        elif self.format == "parquet":
            ext = ".parquet"
        else:
            ext = ".bin"
        if self.compression == "gzip":
            ext += ".gz"
        parts.append(f"part-{uuid.uuid4().hex}{ext}")
        return "/".join([p for p in parts if p])

    def _ensure_records(self, recs: Iterable[dict[str, Any]] | bytes | str) -> List[Dict[str, Any]]:
        if isinstance(recs, (bytes, str)):
            # Interpret as JSONL and parse
            text = recs.decode("utf-8") if isinstance(recs, (bytes, bytearray)) else recs
            rows: List[Dict[str, Any]] = []
            for line in text.splitlines():
                s = line.strip()
                if not s:
                    continue
                try:
                    rows.append(json.loads(s))
                except Exception:
                    # fallback: wrap as {output: raw}
                    rows.append({"output": s})
            return rows
        else:
            return list(recs)

    def _serialize(self, recs: Iterable[dict[str, Any]] | bytes | str) -> bytes:
        fmt = self.format
        if fmt == "csv":
            records = self._ensure_records(recs)
            # Collect headers from union of keys
            headers: List[str] = []
            seen: set[str] = set()
            for r in records:
                for k in r.keys():
                    if k not in seen:
                        seen.add(k)
                        headers.append(k)
            buf = io.StringIO()
            w = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")  # not used directly, keep to illustrate approach
            csvw = io.StringIO()
            import csv as _csv

            wtr = _csv.writer(buf)
            wtr.writerow(headers)
            for r in records:
                wtr.writerow(["" if r.get(h) is None else (json.dumps(r[h]) if isinstance(r[h], (dict, list)) else str(r[h])) for h in headers])
            data = buf.getvalue().encode("utf-8")
        elif fmt == "parquet":
            try:
                import pyarrow as pa  # type: ignore
                import pyarrow.parquet as pq  # type: ignore
            except Exception as e:
                raise ExportError("Parquet export requires optional dependency 'pyarrow'.") from e
            records = self._ensure_records(recs)
            # Normalize to columns; let pyarrow infer
            table = pa.Table.from_pylist(records)
            bio = io.BytesIO()
            # Note: parquet internal compression can be configured by environment or left default; external gzip may still apply below
            pq.write_table(table, bio)
            data = bio.getvalue()
        else:  # jsonl or unknown -> fallback to jsonl
            if isinstance(recs, bytes):
                data = recs
            elif isinstance(recs, str):
                data = recs.encode("utf-8")
            else:
                buf = io.StringIO()
                for r in recs:
                    buf.write(json.dumps(r, ensure_ascii=False) + "\n")
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
