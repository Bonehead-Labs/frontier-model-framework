"""Connectors package.

Includes base protocol/types and factories to create connectors from config.
"""

from ..core.interfaces import ConnectorSelectors, ConnectorSpec
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

        selectors = ConnectorSelectors(
            include=list(_cfg_get(cfg, "include") or ["**/*"]),
            exclude=list(_cfg_get(cfg, "exclude") or []),
        )
        spec = ConnectorSpec(
            name=name,
            type="local",
            selectors=selectors,
            options={"root": _cfg_get(cfg, "root")},
        )
        return LocalConnector(spec=spec)
    if ctype == "s3":
        from .s3 import S3Connector
        selectors = ConnectorSelectors(
            include=list(_cfg_get(cfg, "include") or ["**/*"]),
            exclude=list(_cfg_get(cfg, "exclude") or []),
        )
        spec = ConnectorSpec(
            name=name,
            type="s3",
            selectors=selectors,
            options={
                "bucket": _cfg_get(cfg, "bucket"),
                "prefix": _cfg_get(cfg, "prefix"),
                "region": _cfg_get(cfg, "region"),
                "kms_required": _cfg_get(cfg, "kms_required"),
            },
        )
        return S3Connector(spec=spec)
    if ctype == "sharepoint":
        from .sharepoint import SharePointConnector
        selectors = ConnectorSelectors(
            include=list(_cfg_get(cfg, "include") or ["**/*"]),
            exclude=list(_cfg_get(cfg, "exclude") or []),
        )
        spec = ConnectorSpec(
            name=name,
            type="sharepoint",
            selectors=selectors,
            options={
                "site_url": _cfg_get(cfg, "site_url"),
                "drive": _cfg_get(cfg, "drive"),
                "root_path": _cfg_get(cfg, "root_path"),
                "auth_profile": _cfg_get(cfg, "auth_profile"),
            },
        )
        return SharePointConnector(spec=spec)
    raise ValueError(f"Unsupported connector type: {ctype!r}")


__all__ = [
    "DataConnector",
    "ResourceInfo",
    "ResourceRef",
    "ConnectorError",
    "build_connector",
]
