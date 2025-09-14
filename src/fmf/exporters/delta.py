from __future__ import annotations

from typing import Any, Dict, Iterable
from .base import ExportError, ExportResult


class DeltaExporter:
    def __init__(self, *, name: str, storage: str, path: str, mode: str = "append") -> None:
        self.name = name
        self.storage = storage
        self.path = path
        self.mode = mode

    def write(
        self,
        records: Iterable[Dict[str, Any]] | bytes | str,
        *,
        schema: dict[str, Any] | None = None,
        mode: str = "append",
        key_fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExportResult:
        raise ExportError("Delta exporter not implemented in this environment")

    def finalize(self) -> None:
        return None


__all__ = ["DeltaExporter"]

