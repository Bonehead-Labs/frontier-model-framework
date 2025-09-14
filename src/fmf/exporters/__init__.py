from __future__ import annotations

from typing import Any

from .base import Exporter, ExportError, ExportResult


def _cfg_get(cfg: object | None, key: str, default=None):
    if cfg is None:
        return default
    if isinstance(cfg, dict):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


def build_exporter(cfg: Any) -> Exporter:
    etype = _cfg_get(cfg, "type")
    name = _cfg_get(cfg, "name", etype)
    if etype == "s3":
        from .s3 import S3Exporter

        return S3Exporter(
            name=name,
            bucket=_cfg_get(cfg, "bucket"),
            prefix=_cfg_get(cfg, "prefix"),
            format=_cfg_get(cfg, "format"),
            compression=_cfg_get(cfg, "compression"),
            partition_by=_cfg_get(cfg, "partition_by"),
            sse=_cfg_get(cfg, "sse"),
            kms_key_id=_cfg_get(cfg, "kms_key_id"),
        )
    if etype == "dynamodb":
        from .dynamodb import DynamoDBExporter

        return DynamoDBExporter(
            name=name,
            table=_cfg_get(cfg, "table"),
            region=_cfg_get(cfg, "region"),
            key_fields=_cfg_get(cfg, "key_fields"),
        )
    if etype == "sharepoint_excel":
        from .sharepoint_excel import SharePointExcelExporter

        return SharePointExcelExporter(
            name=name,
            site_url=_cfg_get(cfg, "site_url"),
            drive=_cfg_get(cfg, "drive"),
            file_path=_cfg_get(cfg, "file_path"),
            sheet=_cfg_get(cfg, "sheet"),
            mode=_cfg_get(cfg, "mode"),
            key_fields=_cfg_get(cfg, "key_fields"),
        )
    if etype == "redshift":
        from .redshift import RedshiftExporter

        return RedshiftExporter(
            name=name,
            cluster_id=_cfg_get(cfg, "cluster_id"),
            database=_cfg_get(cfg, "database"),
            schema=_cfg_get(cfg, "schema"),
            table=_cfg_get(cfg, "table"),
            unload_staging_s3=_cfg_get(cfg, "unload_staging_s3"),
        )
    if etype == "delta":
        from .delta import DeltaExporter

        return DeltaExporter(name=name, storage=_cfg_get(cfg, "storage"), path=_cfg_get(cfg, "path"), mode=_cfg_get(cfg, "mode", "append"))
    if etype == "fabric_delta":
        from .fabric_delta import FabricDeltaExporter

        return FabricDeltaExporter(
            name=name,
            workspace=_cfg_get(cfg, "workspace"),
            lakehouse=_cfg_get(cfg, "lakehouse"),
            table=_cfg_get(cfg, "table"),
            mode=_cfg_get(cfg, "mode", "upsert"),
        )
    raise ValueError(f"Unsupported exporter type: {etype}")


__all__ = ["Exporter", "ExportError", "ExportResult", "build_exporter"]

