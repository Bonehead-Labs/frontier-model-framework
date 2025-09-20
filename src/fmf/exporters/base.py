from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Protocol

from ..core.errors import ExportError


@dataclass
class ExportResult:
    count: int
    paths: list[str]


class Exporter(Protocol):
    name: str

    def write(
        self,
        records: Iterable[dict[str, Any]] | bytes | str,
        *,
        schema: dict[str, Any] | None = None,
        mode: Literal["append", "upsert", "overwrite"] | None = None,
        key_fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExportResult:
        ...

    def finalize(self) -> None:
        ...


__all__ = ["Exporter", "ExportResult", "ExportError"]
