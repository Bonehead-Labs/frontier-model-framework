"""Connectors package.

Includes base protocol/types and factories to create connectors from config.
"""

from .base import DataConnector, ResourceInfo, ResourceRef, ConnectorError


def _cfg_get(cfg: object | None, key: str, default=None):
    if cfg is None:
        return default
    if isinstance(cfg, dict):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


def build_connector(cfg: object) -> DataConnector:
    """Build a connector instance from a config model or dict with a 'type' field."""
    ctype = _cfg_get(cfg, "type")
    name = _cfg_get(cfg, "name") or ctype
    if ctype == "local":
        from .local import LocalConnector

        return LocalConnector(name=name, root=_cfg_get(cfg, "root"), include=_cfg_get(cfg, "include"), exclude=_cfg_get(cfg, "exclude"))
    if ctype == "s3":
        from .s3 import S3Connector

        return S3Connector(
            name=name,
            bucket=_cfg_get(cfg, "bucket"),
            prefix=_cfg_get(cfg, "prefix"),
            region=_cfg_get(cfg, "region"),
            kms_required=_cfg_get(cfg, "kms_required"),
        )
    if ctype == "sharepoint":
        from .sharepoint import SharePointConnector

        return SharePointConnector(
            name=name,
            site_url=_cfg_get(cfg, "site_url"),
            drive=_cfg_get(cfg, "drive"),
            root_path=_cfg_get(cfg, "root_path"),
            auth_profile=_cfg_get(cfg, "auth_profile"),
        )
    raise ValueError(f"Unsupported connector type: {ctype!r}")


__all__ = [
    "DataConnector",
    "ResourceInfo",
    "ResourceRef",
    "ConnectorError",
    "build_connector",
]
