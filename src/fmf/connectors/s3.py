from __future__ import annotations

import datetime as dt
from typing import IO, Iterable, Optional

from ..core.interfaces import ConnectorSpec, ConnectorSelectors, RunContext
from ..core.interfaces.connectors_base import BaseConnector
from ..core.retry import default_predicate, retry_call
from .base import ResourceInfo, ResourceRef, ConnectorError


class _ManagedBody:
    def __init__(self, body) -> None:
        self._body = body

    def read(self, *args, **kwargs):  # pragma: no cover - passthrough
        return self._body.read(*args, **kwargs)

    def close(self) -> None:
        close = getattr(self._body, "close", None)
        if callable(close):
            close()

    def __enter__(self):  # pragma: no cover - passthrough
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - passthrough
        self.close()


class S3Connector(BaseConnector):
    def __init__(
        self,
        *,
        spec: ConnectorSpec | None = None,
        name: str | None = None,
        bucket: str | None = None,
        prefix: Optional[str] = None,
        region: Optional[str] = None,
        kms_required: Optional[bool] = None,
    ) -> None:
        if spec is None:
            if name is None or bucket is None:
                raise ValueError("S3Connector requires either a spec or name/bucket parameters")
            selectors = ConnectorSelectors(include=["**/*"], exclude=[])
            spec = ConnectorSpec(
                name=name,
                type="s3",
                selectors=selectors,
                options={
                    "bucket": bucket,
                    "prefix": prefix or "",
                    "region": region,
                    "kms_required": bool(kms_required),
                },
            )
        super().__init__(spec)
        options = spec.options
        self.bucket = options.get("bucket", bucket)
        self.prefix = options.get("prefix", prefix or "") or ""
        if self.prefix and not self.prefix.endswith("/"):
            # Normalize to directory-like prefix
            self.prefix += "/"
        self.region = options.get("region", region)
        self.kms_required = bool(options.get("kms_required", kms_required))
        self._client = None
        self._include = list(spec.selectors.include or ["**/*"])
        self._exclude = list(spec.selectors.exclude or [])

    def _s3(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore
        except Exception as e:  # pragma: no cover - import failure
            raise ConnectorError("boto3 not installed. Install extras: pip install '.[aws]'") from e
        self._client = boto3.client("s3", region_name=self.region)
        return self._client

    @staticmethod
    def _should_retry(exc: Exception) -> bool:
        return default_predicate(exc)

    def _iter_keys(self) -> Iterable[dict]:
        client = self._s3()
        token = None
        while True:
            kwargs = {"Bucket": self.bucket, "Prefix": self.prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = retry_call(client.list_objects_v2, kwargs=kwargs, should_retry=self._should_retry)
            for obj in resp.get("Contents", []) or []:
                yield obj
            if resp.get("IsTruncated"):
                token = resp.get("NextContinuationToken")
                if not token:
                    break
            else:
                break

    def list(
        self,
        *,
        selector: list[str] | None = None,
        context: RunContext | None = None,
    ) -> Iterable[ResourceRef]:
        import fnmatch

        patterns = selector or self._include or ["**/*"]
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
            if self._exclude and any(fnmatch.fnmatchcase(rel, ex) for ex in self._exclude):
                continue
            uri = f"s3://{self.bucket}/{key}"
            yield ResourceRef(id=rel, uri=uri, name=rel.split("/")[-1])

    def open(
        self,
        ref: ResourceRef,
        *,
        mode: str = "rb",
        context: RunContext | None = None,
    ) -> IO[bytes]:
        if "r" not in mode:
            raise ConnectorError("S3Connector only supports reading")
        key = self.prefix + ref.id if self.prefix else ref.id
        resp = retry_call(self._s3().get_object, kwargs={"Bucket": self.bucket, "Key": key}, should_retry=self._should_retry)
        body = resp.get("Body")
        if body is None:
            raise ConnectorError("Empty response body")
        return _ManagedBody(body)

    def info(self, ref: ResourceRef, *, context: RunContext | None = None) -> ResourceInfo:
        key = self.prefix + ref.id if self.prefix else ref.id
        head = retry_call(self._s3().head_object, kwargs={"Bucket": self.bucket, "Key": key}, should_retry=self._should_retry)
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
