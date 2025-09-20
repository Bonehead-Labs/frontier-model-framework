from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ...exporters.base import ExportError, ExportResult
from .models import ExportSpec, RunContext


class BaseExporter(ABC):
    """Abstract exporter with a shared spec + context contract."""

    spec: ExportSpec

    def __init__(self, spec: ExportSpec) -> None:
        self.spec = spec

    @abstractmethod
    def write(
        self,
        payload: Iterable[dict[str, object]] | bytes | str,
        *,
        context: RunContext | None = None,
    ) -> ExportResult:
        """Persist records or a serialised payload."""

    def finalize(self) -> None:  # pragma: no cover - optional override
        """Flush buffers or close connections."""

    def raise_error(self, message: str) -> None:
        raise ExportError(f"{self.spec.name}: {message}")


__all__ = ["BaseExporter"]
