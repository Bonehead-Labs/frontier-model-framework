from __future__ import annotations

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
    """
    Run a high-level recipe YAML using the fluent API.

    Recipes are designed for CI/Ops workflows. For code, prefer the SDK/CLI directly.

    Precedence order (highest to lowest):
    1. Fluent overrides (passed via **kwargs)
    2. Recipe YAML configuration
    3. Base config file

    Args:
        config_path: Path to FMF config file
        recipe_path: Path to recipe YAML file
        **kwargs: Fluent API overrides (service, rag, response, source, mode, etc.)

    Returns:
        RunSummary with execution results and metrics
    """
    import yaml as _yaml

    # Load recipe YAML
    with open(recipe_path, "r", encoding="utf-8") as f:
        recipe_data = _yaml.safe_load(f) or {}

    # Create FMF instance with base config
    fmf = FMF.from_env(config_path)

    # Apply fluent overrides from kwargs (highest precedence)
    if "service" in kwargs:
        fmf = fmf.with_service(kwargs["service"])
    elif "inference_provider" in kwargs:  # Legacy support
        fmf = fmf.with_service(kwargs["inference_provider"])

    if "rag" in kwargs and kwargs["rag"]:
        pipeline = kwargs.get("rag_pipeline") or recipe_data.get("rag", {}).get("pipeline") or "default_rag"
        fmf = fmf.with_rag(enabled=True, pipeline=pipeline)
    elif "use_recipe_rag" in kwargs and kwargs["use_recipe_rag"]:
        pipeline = recipe_data.get("rag", {}).get("pipeline") or "default_rag"
        fmf = fmf.with_rag(enabled=True, pipeline=pipeline)
    elif recipe_data.get("rag", {}).get("pipeline"):
        pipeline = recipe_data["rag"]["pipeline"]
        fmf = fmf.with_rag(enabled=True, pipeline=pipeline)

    if "response" in kwargs:
        fmf = fmf.with_response(kwargs["response"])
    elif "output_format" in kwargs:  # Legacy support
        fmf = fmf.with_response(kwargs["output_format"])

    if "source" in kwargs:
        fmf = fmf.with_source(kwargs["source"])
    elif "connector" in kwargs:
        fmf = fmf.with_source(kwargs["connector"])
    elif recipe_data.get("connector"):
        fmf = fmf.with_source(recipe_data["connector"])

    # Determine inference method and parameters
    recipe_type = recipe_data.get("recipe", "").strip()
    if not recipe_type:
        raise ValueError("Recipe file must specify 'recipe' field (csv_analyse, text_files, images_analyse)")

    # Build method kwargs from recipe data and fluent overrides
    method_kwargs = {}

    if recipe_type == "csv_analyse":
        method_kwargs.update({
            "input": recipe_data["input"],
            "text_col": recipe_data.get("text_col", "Comment"),
            "id_col": recipe_data.get("id_col", "ID"),
            "prompt": recipe_data.get("prompt", "Summarise"),
            "save_csv": recipe_data.get("save", {}).get("csv"),
            "save_jsonl": recipe_data.get("save", {}).get("jsonl"),
            "expects_json": recipe_data.get("expects_json", True),
        })
    elif recipe_type == "text_files":
        method_kwargs.update({
            "prompt": recipe_data.get("prompt", "Summarise"),
            "select": recipe_data.get("select"),
            "save_jsonl": recipe_data.get("save", {}).get("jsonl"),
            "expects_json": recipe_data.get("expects_json", True),
        })
    elif recipe_type == "images_analyse":
        method_kwargs.update({
            "prompt": recipe_data.get("prompt", "Describe"),
            "select": recipe_data.get("select"),
            "save_jsonl": recipe_data.get("save", {}).get("jsonl"),
            "expects_json": recipe_data.get("expects_json", True),
            "group_size": recipe_data.get("group_size"),
        })
    else:
        raise ValueError(f"Unsupported recipe type: {recipe_type}")

    # Apply fluent overrides to method kwargs
    for key in ["input", "text_col", "id_col", "prompt", "select", "group_size", "expects_json"]:
        if key in kwargs:
            method_kwargs[key] = kwargs[key]

    # Handle RAG options
    rag_options = None
    if fmf._rag_override and fmf._rag_override.get("enabled"):
        rag_options = {
            "pipeline": fmf._rag_override.get("pipeline", "default_rag"),
            "top_k_text": kwargs.get("rag_top_k_text") or recipe_data.get("rag", {}).get("top_k_text", 2),
            "top_k_images": kwargs.get("rag_top_k_images") or recipe_data.get("rag", {}).get("top_k_images", 2),
        }

    # Add common options
    method_kwargs.update({
        "rag_options": rag_options,
        "mode": kwargs.get("mode") or recipe_data.get("mode"),
        "return_records": False,  # We don't need records for recipe execution
    })

    # Execute using fluent API with effective config
    fmf._get_effective_config()
    artefacts_dir = _resolve_artefacts_dir(fmf)
    artefacts_dir.mkdir(parents=True, exist_ok=True)

    try:
        if recipe_type == "csv_analyse":
            fmf.csv_analyse(**method_kwargs)
        elif recipe_type == "text_files":
            fmf.text_files(**method_kwargs)
        elif recipe_type == "images_analyse":
            fmf.images_analyse(**method_kwargs)
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


