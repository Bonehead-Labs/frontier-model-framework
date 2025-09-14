from __future__ import annotations

from typing import Dict


_COUNTERS: Dict[str, float] = {}


def inc(name: str, value: float = 1.0) -> None:
    _COUNTERS[name] = _COUNTERS.get(name, 0.0) + value


def set_value(name: str, value: float) -> None:
    _COUNTERS[name] = float(value)


def get_all() -> Dict[str, float]:
    return dict(_COUNTERS)


def clear() -> None:
    _COUNTERS.clear()


__all__ = ["inc", "set_value", "get_all", "clear"]

