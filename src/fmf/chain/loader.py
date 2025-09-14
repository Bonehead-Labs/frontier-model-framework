from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ChainStep:
    id: str
    prompt: str  # path#version or inline text when startswith 'inline:'
    inputs: Dict[str, Any]
    output: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class ChainConfig:
    name: str
    inputs: Dict[str, Any]
    steps: List[ChainStep]
    outputs: Optional[List[Dict[str, Any]]] = None
    concurrency: int = 4
    continue_on_error: bool = True


def load_chain(path: str) -> ChainConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    name = data.get("name") or "chain"
    inputs = data.get("inputs") or {}
    steps_data = data.get("steps") or []
    steps: List[ChainStep] = []
    for s in steps_data:
        steps.append(
            ChainStep(
                id=s["id"],
                prompt=s.get("prompt") or s.get("prompt_text", ""),
                inputs=s.get("inputs", {}),
                output=s.get("output", s["id"]),
                params=s.get("params"),
            )
        )
    outputs = data.get("outputs")
    concurrency = int(data.get("concurrency", 4))
    continue_on_error = bool(data.get("continue_on_error", True))
    return ChainConfig(
        name=name,
        inputs=inputs,
        steps=steps,
        outputs=outputs,
        concurrency=concurrency,
        continue_on_error=continue_on_error,
    )


__all__ = ["ChainConfig", "ChainStep", "load_chain"]
