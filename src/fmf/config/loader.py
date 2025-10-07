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
    """Set a nested value in a dict using a path, supporting list indices.

    Path segments that are numeric (e.g., "0") are treated as list indices for
    the next container. This allows env overrides like FMF_CONNECTORS__0__NAME
    to correctly create a list under "connectors" instead of a dict with a
    string key "0".
    """
    cur: Any = data
    for i, key in enumerate(path[:-1]):
        next_key = path[i + 1] if i + 1 < len(path) else None
        next_is_index = isinstance(next_key, str) and next_key.isdigit()

        # If current container is a list, interpret key as list index
        if isinstance(cur, list):
            if not key.isdigit():
                # Invalid structure; convert list to dict to proceed safely
                # (should not typically happen for our env overrides)
                tmp = {}
                for idx, item in enumerate(cur):
                    tmp[str(idx)] = item
                cur.clear()
                cur = tmp
            else:
                idx = int(key)
                while len(cur) <= idx:
                    cur.append({})
                if cur[idx] is None:
                    cur[idx] = {}
                cur = cur[idx]
                continue

        # Current is a dict; decide whether to create a list or dict at key
        if key not in cur:
            cur[key] = [] if next_is_index else {}
        else:
            # Coerce to list/dict based on next segment type
            if next_is_index and not isinstance(cur[key], list):
                cur[key] = []
            if not next_is_index and not isinstance(cur[key], dict):
                cur[key] = {}
        cur = cur[key]

    # Set the leaf value
    leaf = path[-1]
    if isinstance(cur, list) and isinstance(leaf, str) and leaf.isdigit():
        idx = int(leaf)
        while len(cur) <= idx:
            cur.append(None)
        cur[idx] = value
    elif isinstance(cur, dict):
        cur[leaf] = value
    else:
        # Fallback: if structure is unexpected, convert to dict
        # and set the value
        tmp = {str(leaf): value}
        cur = tmp


def _apply_env_overrides(cfg: dict, env: Mapping[str, str]) -> None:
    prefix = "FMF_"
    for k, v in env.items():
        if not k.startswith(prefix):
            continue
        keypath = k[len(prefix) :].lower().split("__")
        if not keypath:
            continue
        _set_by_path(cfg, keypath, _parse_scalar(v))


def _parse_set_item(item: str) -> tuple[list[str], Any]:
    """Parse a single --set "key.path=value" string.

    - Uses first '=' as separator.
    - Key path split by '.' into a list.
    - Value parsed via YAML safe_load for rich types; falls back to scalar parsing.
    """
    if "=" not in item:
        raise ValueError(f"Invalid --set override (missing '='): {item!r}")
    key, raw = item.split("=", 1)
    path = [p for p in key.strip().split(".") if p]
    if not path:
        raise ValueError(f"Invalid --set override (empty key path): {item!r}")
    try:
        value = yaml.safe_load(raw)
    except Exception:
        value = _parse_scalar(raw)
    return path, value


def parse_set_overrides(sets: list[str] | None) -> dict[str, Any]:
    """Convert a list of --set items into a nested dict suitable for deep merging."""
    result: dict[str, Any] = {}
    if not sets:
        return result
    for item in sets:
        path, value = _parse_set_item(item)
        _set_by_path(result, path, value)
    return result


def _deep_merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def _apply_profile(cfg: dict, env: Mapping[str, str]) -> None:
    """Apply profile overlays if configured.

    Resolution order for active profile:
    1) cfg["profiles"]["active"] if present
    2) env["FMF_PROFILE"] if set
    3) cfg.get("run_profile") as a fallback legacy key
    If a profile name is found and exists under cfg["profiles"], merge its mapping into cfg.
    """
    profiles = cfg.get("profiles")
    if not isinstance(profiles, dict):
        return
    active = profiles.get("active")
    if not active:
        active = env.get("FMF_PROFILE")
    if not active:
        active = cfg.get("run_profile")
    if not active:
        return
    overlay = profiles.get(active)
    if isinstance(overlay, dict):
        _deep_merge(cfg, overlay)


def _apply_runtime_toggles(cfg: FmfConfig) -> None:
    if getattr(cfg, "experimental", None):
        exp = cfg.experimental
        if exp and exp.observability_otel and not os.getenv("FMF_OBSERVABILITY_OTEL"):
            os.environ["FMF_OBSERVABILITY_OTEL"] = "1"
    if getattr(cfg, "processing", None) and cfg.processing and cfg.processing.hash_algo:
        os.environ.setdefault("FMF_HASH_ALGO", cfg.processing.hash_algo)
    if getattr(cfg, "retries", None) and cfg.retries and cfg.retries.max_elapsed_s is not None:
        os.environ.setdefault("FMF_RETRY_MAX_ELAPSED", str(cfg.retries.max_elapsed_s))


def load_config(
    path: str,
    *,
    env: Mapping[str, str] | None = None,
    overrides: dict[str, Any] | None = None,
    set_overrides: list[str] | None = None,
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

    # Highest precedence: explicit --set overrides
    if set_overrides:
        _deep_merge(data, parse_set_overrides(set_overrides))

    # Apply profile overlays (after env and overrides, and aware of --set profiles.active)
    _apply_profile(data, env)

    # Attempt to validate with Pydantic if available
    try:
        model = FmfConfig.model_validate(data)  # type: ignore[attr-defined]
        _apply_runtime_toggles(model)
        return model
    except Exception:
        # Fallback to raw dict when validation not available
        return data

__all__ = [
    "load_config",
    "parse_set_overrides",
]
