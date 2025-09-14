from __future__ import annotations

import os
from typing import Any, Mapping

import yaml

from .models import FmfConfig


def _parse_scalar(value: str) -> Any:
    v = value.strip()
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return value


def _set_by_path(data: dict, path: list[str], value: Any) -> None:
    cur = data
    for key in path[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[path[-1]] = value


def _apply_env_overrides(cfg: dict, env: Mapping[str, str]) -> None:
    prefix = "FMF_"
    for k, v in env.items():
        if not k.startswith(prefix):
            continue
        keypath = k[len(prefix) :].lower().split("__")
        if not keypath:
            continue
        _set_by_path(cfg, keypath, _parse_scalar(v))


def _deep_merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def load_config(
    path: str,
    *,
    env: Mapping[str, str] | None = None,
    overrides: dict[str, Any] | None = None,
):
    """Load config from YAML with optional env and dict overrides.

    Returns a Pydantic model if pydantic is installed; otherwise returns a plain dict.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if env is None:
        env = os.environ
    _apply_env_overrides(data, env)

    if overrides:
        _deep_merge(data, overrides)

    # Attempt to validate with Pydantic if available
    try:
        model = FmfConfig.model_validate(data)  # type: ignore[attr-defined]
        return model
    except Exception:
        # Fallback to raw dict when validation not available
        return data

