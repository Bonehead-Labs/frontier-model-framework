from __future__ import annotations

from typing import Any, Dict, Iterable
from .base import ExportError, ExportResult


class RedshiftExporter:
    def __init__(self, *, name: str, cluster_id: str, database: str, schema: str, table: str, unload_staging_s3: str) -> None:
        self.name = name
        self.cluster_id = cluster_id
        self.database = database
        self.schema = schema
        self.table = table
        self.unload_staging_s3 = unload_staging_s3

    def write(
        self,
        records: Iterable[Dict[str, Any]] | bytes | str,
        *,
        schema: dict[str, Any] | None = None,
        mode: str = "upsert",
        key_fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExportResult:
        raise ExportError("Redshift exporter not implemented in this environment")

    def finalize(self) -> None:
        return None


__all__ = ["RedshiftExporter"]

