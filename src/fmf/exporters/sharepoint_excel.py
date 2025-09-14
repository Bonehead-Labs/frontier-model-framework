from __future__ import annotations

from .base import ExportError, ExportResult
from typing import Any, Dict, Iterable


class SharePointExcelExporter:
    def __init__(
        self,
        *,
        name: str,
        site_url: str,
        drive: str,
        file_path: str,
        sheet: str,
        mode: str = "upsert",
        key_fields: list[str] | None = None,
    ) -> None:
        self.name = name
        self.site_url = site_url
        self.drive = drive
        self.file_path = file_path
        self.sheet = sheet
        self.mode = mode
        self.key_fields = key_fields or []

    def write(
        self,
        records: Iterable[Dict[str, Any]] | bytes | str,
        *,
        schema: dict[str, Any] | None = None,
        mode: str = "upsert",
        key_fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExportResult:
        raise ExportError("SharePoint Excel exporter not implemented in this environment")

    def finalize(self) -> None:
        return None


__all__ = ["SharePointExcelExporter"]

