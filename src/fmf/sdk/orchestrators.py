from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .client import FMF


@dataclass
class RunSummary:
    ok: bool
    run_id: str | None = None
    inputs: int | None = None
    outputs_path: str | None = None
    notes: str | None = None


def _resolve_artefacts_dir(fmf_obj: FMF) -> Path:
    cfg = getattr(fmf_obj, "_cfg", None)
    if isinstance(cfg, dict):
        path = cfg.get("artefacts_dir") or "artefacts"
    else:
        path = getattr(cfg, "artefacts_dir", None) or "artefacts"
    return Path(path)


def _discover_latest_run(artefacts_dir: Path) -> tuple[str | None, Path | None]:
    if not artefacts_dir.exists():
        return None, None
    directories = [p for p in artefacts_dir.iterdir() if p.is_dir()]
    if not directories:
        return None, None
    latest = max(directories, key=lambda p: p.stat().st_mtime)
    return latest.name, latest


def _infer_outputs_path(run_dir: Path | None) -> str | None:
    if run_dir is None:
        return None
    candidates = ["outputs.jsonl", "analysis.jsonl", "analysis.csv", "text_outputs.jsonl", "image_outputs.jsonl"]
    for name in candidates:
        candidate = run_dir / name
        if candidate.exists():
            return str(candidate)
    return str(run_dir)


def _count_outputs(run_dir: Path | None) -> int | None:
    if run_dir is None:
        return None
    outputs = run_dir / "outputs.jsonl"
    if not outputs.exists():
        return None
    try:
        with outputs.open("r", encoding="utf-8") as fh:
            return sum(1 for _ in fh)
    except Exception:
        return None


def run_recipe_simple(config_path: str, recipe_path: str, **kwargs: Any) -> RunSummary:
    fmf = FMF.from_env(config_path)
    artefacts_dir = _resolve_artefacts_dir(fmf)
    artefacts_dir.mkdir(parents=True, exist_ok=True)
    try:
        fmf.run_recipe(recipe_path, **kwargs)
    except Exception as exc:  # pragma: no cover - bubbled up to caller
        notes = (
            f"Recipe failed: {exc}. If secrets are required, run "
            f"`python -m fmf keys test --json -c {config_path}` first."
        )
        return RunSummary(ok=False, notes=notes)

    run_id, run_dir = _discover_latest_run(artefacts_dir)
    return RunSummary(
        ok=True,
        run_id=run_id,
        inputs=_count_outputs(run_dir),
        outputs_path=_infer_outputs_path(run_dir),
        notes="See recipe-defined outputs for details.",
    )
