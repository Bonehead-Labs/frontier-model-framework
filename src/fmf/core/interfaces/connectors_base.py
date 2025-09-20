from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, IO

from ...connectors.base import ConnectorError, ResourceInfo, ResourceRef
from .models import ConnectorSpec, RunContext


class BaseConnector(ABC):
    """Abstract base class for FMF connectors with a consistent contract.

    Concrete implementations SHOULD inherit from this class (or continue to use
    the legacy Protocol in ``fmf.connectors.base`` until migrated). The new
    interface adds optional run context plumbing so that connectors can respond
    to profile-specific overrides (e.g., auth, throttling).
    """

    spec: ConnectorSpec

    def __init__(self, spec: ConnectorSpec) -> None:
        self.spec = spec
        self.name = spec.name

    # Existing connectors can transition to this base class alongside ConnectorSpec adoption.

    @abstractmethod
    def list(
        self,
        *,
        selector: list[str] | None = None,
        context: RunContext | None = None,
    ) -> Iterable[ResourceRef]:
        """Yield resources that match the optional selector for the current connector."""

    @abstractmethod
    def open(
        self,
        ref: ResourceRef,
        *,
        mode: str = "rb",
        context: RunContext | None = None,
    ) -> IO[bytes]:
        """Open a streaming handle for the referenced resource."""

    @abstractmethod
    def info(self, ref: ResourceRef, *, context: RunContext | None = None) -> ResourceInfo:
        """Return metadata for the given resource."""

    def close(self) -> None:  # pragma: no cover - optional hook
        """Optional clean-up hook (filesystems may not need it)."""

    def raise_error(self, message: str) -> None:
        """Helper to raise connector-specific errors with consistent type."""

        raise ConnectorError(f"{self.name}: {message}")


__all__ = ["BaseConnector"]
