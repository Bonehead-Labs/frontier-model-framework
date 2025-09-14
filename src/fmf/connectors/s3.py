from __future__ import annotations

import datetime as dt
from typing import IO, Iterable, List, Optional

from .base import DataConnector, ResourceInfo, ResourceRef, ConnectorError


class S3Connector:
    def __init__(
        self,
        *,
        name: str,
        bucket: str,
        prefix: Optional[str] = None,
        region: Optional[str] = None,
        kms_required: Optional[bool] = None,
    ) -> None:
        self.name = name
        self.bucket = bucket
        self.prefix = prefix or ""
        if self.prefix and not self.prefix.endswith("/"):
            # Normalize to directory-like prefix
            self.prefix += "/"
        self.region = region
        self.kms_required = bool(kms_required)
        self._client = None

    def _s3(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore
        except Exception as e:  # pragma: no cover - import failure
            raise ConnectorError("boto3 not installed. Install extras: pip install '.[aws]'") from e
        self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def _iter_keys(self) -> Iterable[dict]:
        client = self._s3()
        token = None
        while True:
            kwargs = {"Bucket": self.bucket, "Prefix": self.prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []) or []:
                yield obj
            if resp.get("IsTruncated"):
                token = resp.get("NextContinuationToken")
                if not token:
                    break
            else:
                break

    def list(self, selector: list[str] | None = None) -> Iterable[ResourceRef]:
        import fnmatch

        patterns = selector or ["**/*"]
        for obj in self._iter_keys():
            key = obj.get("Key")
            if key is None:
                continue
            rel = key[len(self.prefix) :] if self.prefix and key.startswith(self.prefix) else key
            # apply glob patterns relative to prefix
            if not any(
                fnmatch.fnmatchcase(rel, pat) or (pat.startswith("**/") and fnmatch.fnmatchcase(rel, pat[3:]))
                for pat in patterns
            ):
                continue
            uri = f"s3://{self.bucket}/{key}"
            yield ResourceRef(id=rel, uri=uri, name=rel.split("/")[-1])

    def open(self, ref: ResourceRef, mode: str = "rb") -> IO[bytes]:
        if "r" not in mode:
            raise ConnectorError("S3Connector only supports reading")
        key = self.prefix + ref.id if self.prefix else ref.id
        resp = self._s3().get_object(Bucket=self.bucket, Key=key)
        body = resp.get("Body")
        if body is None:
            raise ConnectorError("Empty response body")
        return body  # type: ignore[return-value]

    def info(self, ref: ResourceRef) -> ResourceInfo:
        key = self.prefix + ref.id if self.prefix else ref.id
        head = self._s3().head_object(Bucket=self.bucket, Key=key)
        size = head.get("ContentLength")
        last_modified = head.get("LastModified")
        if isinstance(last_modified, dt.datetime) and last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=dt.timezone.utc)
        etag = head.get("ETag")
        sse = head.get("ServerSideEncryption")
        kms_id = head.get("SSEKMSKeyId")
        if self.kms_required and sse != "aws:kms":
            raise ConnectorError("KMS encryption required but object not encrypted with KMS")
        return ResourceInfo(
            source_uri=f"s3://{self.bucket}/{key}",
            modified_at=last_modified,
            etag=etag,
            size=size,
            extra={"sse": sse, "kms_key_id": kms_id},
        )


__all__ = ["S3Connector"]

