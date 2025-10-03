from __future__ import annotations

import base64
import datetime as dt
import gzip
import hashlib
import io
import json
import uuid
from typing import Any, Iterable, List, Dict

from ..core.ids import utc_now_iso
from ..core.interfaces import ExportSpec
from .base import ExportError, ExportResult


def _now_date():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


class S3Exporter:
    """Write artefacts to Amazon S3.

    ``append`` mode emits a new object per invocation (no guarantees about ordering). ``overwrite``
    writes to a deterministic key via upload-to-temp + copy-to-final to achieve atomic swaps. Upsert
    is currently unsupported and raises :class:`ExportError`.
    """
    def __init__(
        self,
        *,
        spec: ExportSpec | None = None,
        name: str | None = None,
        bucket: str | None = None,
        prefix: str | None = None,
        format: str | None = None,
        compression: str | None = None,
        partition_by: list[str] | None = None,
        sse: str | None = None,
        kms_key_id: str | None = None,
        mode: str | None = None,
    ) -> None:
        if spec is None:
            if name is None:
                name = "s3"
            options = {
                "bucket": bucket,
                "prefix": prefix,
                "compression": compression,
                "partition_by": partition_by,
                "sse": sse,
                "kms_key_id": kms_key_id,
            }
            spec = ExportSpec(
                name=name,
                type="s3",
                format=format or "jsonl",
                write_mode=mode or "append",
                options=options,
            )
        self.spec = spec
        options = spec.options
        self.name = spec.name
        self.bucket = options.get("bucket") or bucket
        if not self.bucket:
            raise ExportError("S3 exporter requires a 'bucket' option")
        self.prefix = (options.get("prefix") or prefix or "").lstrip("/")
        self.format = (spec.format or format or "jsonl").lower()
        self.compression = (options.get("compression") or compression or "none").lower()
        self.partition_by = options.get("partition_by") or partition_by or []
        self.sse = options.get("sse") or sse
        self.kms_key_id = options.get("kms_key_id") or kms_key_id
        self.write_mode = (spec.write_mode or mode or "append").lower()
        self.key_fields = spec.key_fields or []
        self._client = None

    def _s3(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore
        except Exception as e:
            raise ExportError("boto3 not installed. Install extras: pip install '.[aws]'") from e
        # Prefer environment-overrides (.env via FMF auth) for credentials/region.
        # If AWS_REGION/AWS_DEFAULT_REGION is not set but bucket region is known via config,
        # boto3 will still detect region per-bucket, but we avoid surprises by passing region when available.
        region = None
        try:
            import os as _os
            region = _os.getenv("AWS_REGION") or _os.getenv("AWS_DEFAULT_REGION")
        except Exception:
            region = None
        if region:
            self._client = boto3.client("s3", region_name=region)
        else:
            self._client = boto3.client("s3")
        return self._client

    def _ext(self) -> str:
        mapping = {
            "jsonl": ".jsonl",
            "csv": ".csv",
            "parquet": ".parquet",
        }
        ext = mapping.get(self.format, ".bin")
        if self.compression == "gzip":
            ext += ".gz"
        return ext

    def _build_key(self, *, context: dict[str, Any] | None, final: bool = True) -> str:
        run_id = (context or {}).get("run_id") or utc_now_iso().replace(":", "").replace("-", "")
        prefix = (self.prefix or "").replace("${run_id}", run_id).strip("/")
        parts = [prefix] if prefix else []
        if "date" in (self.partition_by or []):
            parts.append(f"date={_now_date()}")
        base_name = context.get("filename") if isinstance(context, dict) else None  # type: ignore[arg-type]
        if not base_name:
            base_name = self.name or "export"
        if self.write_mode == "overwrite" and final:
            filename = f"{base_name}{self._ext()}"
        else:
            filename = f"part-{uuid.uuid4().hex}{self._ext()}"
        parts.append(filename)
        key = "/".join([p for p in parts if p])
        if not final:
            key = f"{key}.tmp-{uuid.uuid4().hex}"
        return key

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
            io.TextIOWrapper(io.BytesIO(), encoding="utf-8")  # not used directly, keep to illustrate approach
            io.StringIO()
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
        mode: str | None = None,
        key_fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExportResult:
        active_mode = (mode or self.write_mode or "append").lower()
        if active_mode == "upsert":  # TODO: implement S3 upsert semantics via merge manifest
            raise ExportError("S3 upsert mode is not supported yet")

        data = self._serialize(records)
        client = self._s3()
        md5_digest = hashlib.md5(data).digest()
        content_md5 = base64.b64encode(md5_digest).decode("ascii")
        sha256_hex = hashlib.sha256(data).hexdigest()
        metadata = {"fmf-sha256": sha256_hex, "fmf-bytes": str(len(data))}
        quoted_etag = f'"{md5_digest.hex()}"'

        if active_mode == "overwrite":
            final_key = self._build_key(context=context, final=True)
            temp_key = self._build_key(context=context, final=False)
            put_kwargs = {"Bucket": self.bucket, "Key": temp_key, "Body": data, "ContentMD5": content_md5, "Metadata": metadata}
            if self.sse == "kms":
                put_kwargs["ServerSideEncryption"] = "aws:kms"
                if self.kms_key_id:
                    put_kwargs["SSEKMSKeyId"] = self.kms_key_id
            elif self.sse == "s3":
                put_kwargs["ServerSideEncryption"] = "AES256"
            client.put_object(**put_kwargs)
            copy_source = {"Bucket": self.bucket, "Key": temp_key}
            copy_kwargs = {
                "Bucket": self.bucket,
                "Key": final_key,
                "CopySource": copy_source,
                "CopySourceIfMatch": quoted_etag,
                "MetadataDirective": "COPY",
            }
            if self.sse == "kms":
                copy_kwargs["ServerSideEncryption"] = "aws:kms"
                if self.kms_key_id:
                    copy_kwargs["SSEKMSKeyId"] = self.kms_key_id
            elif self.sse == "s3":
                copy_kwargs["ServerSideEncryption"] = "AES256"
            client.copy_object(**copy_kwargs)
            try:
                head = client.head_object(Bucket=self.bucket, Key=final_key)
                if head.get("ContentLength") != len(data):
                    raise ExportError("S3 overwrite verification failed: size mismatch")
                meta = head.get("Metadata", {}) or {}
                if meta.get("fmf-sha256") not in {sha256_hex, sha256_hex.lower()}:
                    raise ExportError("S3 overwrite verification failed: checksum mismatch")
            except Exception:  # pragma: no cover - best effort fallback
                raise
            client.delete_object(Bucket=self.bucket, Key=temp_key)
            return ExportResult(count=-1, paths=[f"s3://{self.bucket}/{final_key}"])

        key = self._build_key(context=context, final=True)
        put_kwargs = {"Bucket": self.bucket, "Key": key, "Body": data, "ContentMD5": content_md5, "Metadata": metadata}
        if self.sse == "kms":
            put_kwargs["ServerSideEncryption"] = "aws:kms"
            if self.kms_key_id:
                put_kwargs["SSEKMSKeyId"] = self.kms_key_id
        elif self.sse == "s3":
            put_kwargs["ServerSideEncryption"] = "AES256"
        client.put_object(**put_kwargs)
        return ExportResult(count=-1, paths=[f"s3://{self.bucket}/{key}"])

    def finalize(self) -> None:
        return None


__all__ = ["S3Exporter"]
