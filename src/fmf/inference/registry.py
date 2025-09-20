from __future__ import annotations

from typing import Any, Callable, Dict

ProviderFactory = Callable[[Any], Any]

_REGISTRY: Dict[str, ProviderFactory] = {}


def register_provider(name: str) -> Callable[[ProviderFactory], ProviderFactory]:
    name = name.lower()

    def decorator(func: ProviderFactory) -> ProviderFactory:
        _REGISTRY[name] = func
        return func

    return decorator


def build_provider(name: str, cfg: Any) -> Any:
    try:
        factory = _REGISTRY[name.lower()]
    except KeyError as exc:
        raise ValueError(f"Provider '{name}' is not registered") from exc
    return factory(cfg)


def available_providers() -> list[str]:
    return sorted(_REGISTRY.keys())


__all__ = ["register_provider", "build_provider", "available_providers"]
