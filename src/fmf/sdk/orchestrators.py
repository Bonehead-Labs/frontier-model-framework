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
    streaming: bool | None = None
    mode: str | None = None
    time_to_first_byte_ms: int | None = None
    latency_ms: int | None = None
    tokens_out: int | None = None
    retries: int | None = None
    fallback_reason: str | None = None


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
    streaming: bool | None = None
    mode: str | None = None
    time_to_first_byte_ms: int | None = None
    latency_ms: int | None = None
    tokens_out: int | None = None
    retries: int | None = None
    fallback_reason: str | None = None
    if run_dir:
        run_yaml_path = run_dir / "run.yaml"
        if run_yaml_path.exists():
            import yaml

            try:
                run_data = yaml.safe_load(run_yaml_path.read_text(encoding="utf-8")) or {}
            except Exception:
                run_data = {}
            metrics = run_data.get("metrics") or {}
            step_stats = run_data.get("step_telemetry") or {}
            streaming = bool(metrics.get("streaming_used", False))
            tt_first = metrics.get("time_to_first_byte_ms_avg")
            if isinstance(tt_first, (int, float)):
                time_to_first_byte_ms = int(tt_first)
            lat_avg = metrics.get("latency_ms_avg")
            if isinstance(lat_avg, (int, float)):
                latency_ms = int(lat_avg)
            tokens_val = metrics.get("tokens_out_sum")
            if tokens_val is None:
                tokens_val = metrics.get("tokens_completion")
            if isinstance(tokens_val, (int, float)):
                tokens_out = int(tokens_val)
            retries_val = metrics.get("retries_total")
            if isinstance(retries_val, (int, float)):
                retries = int(retries_val)
            if isinstance(step_stats, dict) and step_stats:
                step_items = list(step_stats.items())
                last_step_id, last_stats = step_items[-1]
                if isinstance(last_stats, dict):
                    mode_candidate = last_stats.get("selected_mode")
                    if isinstance(mode_candidate, str):
                        mode = mode_candidate
                    if not fallback_reason and last_stats.get("fallback_reason"):
                        fallback_reason = last_stats.get("fallback_reason")
                if fallback_reason is None:
                    for _step_id, stats in step_items:
                        if isinstance(stats, dict) and stats.get("fallback_reason"):
                            fallback_reason = stats.get("fallback_reason")
                            break
                if streaming is False:
                    streaming = any(
                        bool(stats.get("streaming"))
                        for stats in step_stats.values()
                        if isinstance(stats, dict)
                    )
            if mode is None and isinstance(kwargs, dict):
                mode = kwargs.get("mode")

    if mode is None and isinstance(kwargs, dict):
        mode = kwargs.get("mode")

    return RunSummary(
        ok=True,
        run_id=run_id,
        inputs=_count_outputs(run_dir),
        outputs_path=_infer_outputs_path(run_dir),
        notes="See recipe-defined outputs for details.",
        streaming=streaming,
        mode=mode,
        time_to_first_byte_ms=time_to_first_byte_ms,
        latency_ms=latency_ms,
        tokens_out=tokens_out,
        retries=retries,
        fallback_reason=fallback_reason,
    )
