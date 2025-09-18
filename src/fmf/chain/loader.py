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
    mode: Optional[str] = None  # e.g., 'multimodal'
    # Post-processing expectations
    output_expects: Optional[str] = None  # 'json' | None
    output_schema: Optional[Dict[str, Any]] = None
    output_parse_retries: int = 0
    rag: Optional[Dict[str, Any]] = None


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
        output_name: str
        output_expects: Optional[str] = None
        output_schema: Optional[Dict[str, Any]] = None
        output_parse_retries: int = 0

        out_val = s.get("output", s.get("id"))
        if isinstance(out_val, dict):
            output_name = out_val.get("name") or s.get("id")
            output_expects = out_val.get("expects")
            output_schema = out_val.get("schema")
            output_parse_retries = int(out_val.get("parse_retries", 0) or 0)
        else:
            output_name = out_val

        steps.append(
            ChainStep(
                id=s["id"],
                prompt=s.get("prompt") or s.get("prompt_text", ""),
                inputs=s.get("inputs", {}),
                output=output_name,
                params=s.get("params"),
                mode=s.get("mode"),
                output_expects=output_expects,
                output_schema=output_schema,
                output_parse_retries=output_parse_retries,
                rag=s.get("rag"),
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
