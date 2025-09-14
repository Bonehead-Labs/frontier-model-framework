from __future__ import annotations

from typing import Any, Dict, Iterable
from .base import ExportError, ExportResult


class FabricDeltaExporter:
    def __init__(self, *, name: str, workspace: str, lakehouse: str, table: str, mode: str = "upsert") -> None:
        self.name = name
        self.workspace = workspace
        self.lakehouse = lakehouse
        self.table = table
        self.mode = mode

    def write(
        self,
        records: Iterable[Dict[str, Any]] | bytes | str,
        *,
        schema: dict[str, Any] | None = None,
        mode: str = "upsert",
        key_fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExportResult:
        raise ExportError("Fabric Delta exporter not implemented in this environment")

    def finalize(self) -> None:
        return None


__all__ = ["FabricDeltaExporter"]

