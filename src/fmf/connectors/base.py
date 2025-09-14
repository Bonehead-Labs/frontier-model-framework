from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import IO, Any, Iterable, Protocol


class ConnectorError(Exception):
    """Errors raised by DataConnector implementations."""


@dataclass(frozen=True)
class ResourceRef:
    """A reference to a resource in a connector namespace.

    - id: connector-scoped identifier (e.g., path or object key)
    - uri: stable URI for the resource (e.g., file:///path, s3://bucket/key)
    - name: display-friendly name (e.g., basename)
    """

    id: str
    uri: str
    name: str


@dataclass(frozen=True)
class ResourceInfo:
    """Metadata describing a resource.

    - source_uri: canonical URI
    - modified_at: last modified timestamp (UTC)
    - etag: entity tag or content hash if available
    - size: size in bytes if known
    - extra: optional provider-specific fields
    """

    source_uri: str
    modified_at: _dt.datetime | None
    etag: str | None
    size: int | None
    extra: dict[str, Any] | None = None


class DataConnector(Protocol):
    """Protocol for data connectors able to list and stream resources."""

    name: str

    def list(self, selector: list[str] | None = None) -> Iterable[ResourceRef]:
        """List resources matching optional glob patterns relative to the connector root."""

    def open(self, ref: ResourceRef, mode: str = "rb") -> IO[bytes]:  # pragma: no cover - implemented by connectors
        """Open a stream for the given resource reference."""

    def info(self, ref: ResourceRef) -> ResourceInfo:  # pragma: no cover - implemented by connectors
        """Return metadata for the given resource reference."""


__all__ = [
    "ConnectorError",
    "ResourceRef",
    "ResourceInfo",
    "DataConnector",
]

