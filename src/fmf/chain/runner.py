from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

from ..connectors import build_connector
from ..processing.loaders import load_document_from_bytes
from ..processing.chunking import chunk_text
from ..processing.persist import persist_artefacts, ensure_dir
from ..inference.unified import build_llm_client
from ..inference.base_client import Message, Completion
from ..config.loader import load_config
from ..exporters import build_exporter
from ..observability import metrics as _metrics
from ..observability.tracing import trace_span
from ..prompts.registry import build_prompt_registry
from .loader import ChainConfig, ChainStep, load_chain


def _render_template(template: str, variables: Dict[str, Any]) -> str:
    out = template
    for k, v in variables.items():
        if isinstance(v, (dict, list)):
            continue
        out = out.replace("${" + k + "}", str(v))
    # support ${all.*} flattened lists
    if "${all." in out:
        # Replace occurrences by joined string
        for key, val in variables.items():
            pass
    return out


def _interp(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        path = value[2:-1]
        # Support dotted paths e.g., chunk.text or all.prev_output
        cur: Any = context
        for part in path.split("."):
            if part == "*":
                # special: join all lists into single string
                if isinstance(cur, list):
                    return "\n".join(map(str, cur))
                return cur
            cur = cur.get(part) if isinstance(cur, dict) else getattr(cur, part, None)
        return cur
    return value


def _load_prompt_text(ref: str, *, registry) -> Tuple[str, Dict[str, str]]:
    # ref can be 'inline: ...' or 'path#version'
    if ref.startswith("inline:"):
        text = ref[len("inline:") :].lstrip()
        import hashlib as _hash
        ch = _hash.sha256(text.encode("utf-8")).hexdigest()
        return text, {"id": "inline", "version": "v0", "content_hash": ch}
    # If not inline, try registry via path#version or id#version
    if os.path.exists(ref.split("#", 1)[0]):
        # Register file reference to ensure index awareness
        pv = registry.register(ref)
    else:
        pv = registry.get(ref)
    return pv.template, {"id": pv.id, "version": pv.version, "content_hash": pv.content_hash}


def run_chain(chain_path: str, *, fmf_config_path: str = "fmf.yaml") -> Dict[str, Any]:
    chain = load_chain(chain_path)
    cfg = load_config(fmf_config_path)
    inference_cfg = getattr(cfg, "inference", None) if not isinstance(cfg, dict) else cfg.get("inference")
    processing_cfg = getattr(cfg, "processing", None) if not isinstance(cfg, dict) else cfg.get("processing")
    artefacts_dir = getattr(cfg, "artefacts_dir", None) if not isinstance(cfg, dict) else cfg.get("artefacts_dir") or "artefacts"

    # Resolve connector and select
    conn_name = chain.inputs.get("connector")
    selector = chain.inputs.get("select")
    connectors = getattr(cfg, "connectors", None) if not isinstance(cfg, dict) else cfg.get("connectors")
    if not connectors:
        raise RuntimeError("No connectors configured")
    target = None
    for c in connectors:
        nm = getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
        if nm == conn_name:
            target = c
            break
    if not target:
        raise RuntimeError(f"Connector {conn_name!r} not found")
    conn = build_connector(target)

    # Prepare registry and LLM client
    preg_cfg = getattr(cfg, "prompt_registry", None) if not isinstance(cfg, dict) else cfg.get("prompt_registry")
    registry = build_prompt_registry(preg_cfg)
    client = build_llm_client(inference_cfg)

    # Process inputs to chunks
    documents = []
    chunks = []
    with trace_span("chain.inputs"):
        for ref in conn.list(selector=selector):
            with conn.open(ref, mode="rb") as f:
                data = f.read()
            doc = load_document_from_bytes(source_uri=ref.uri, filename=ref.name, data=data, processing_cfg=processing_cfg)
            documents.append(doc)
            if doc.text:
                text_cfg = getattr(processing_cfg, "text", None) if not isinstance(processing_cfg, dict) else (processing_cfg or {}).get("text")
                ch_cfg = getattr(text_cfg, "chunking", None) if text_cfg and not isinstance(text_cfg, dict) else (text_cfg or {}).get("chunking") if text_cfg else None
                max_tokens = getattr(ch_cfg, "max_tokens", 800) if ch_cfg and not isinstance(ch_cfg, dict) else (ch_cfg or {}).get("max_tokens", 800) if ch_cfg else 800
                overlap = getattr(ch_cfg, "overlap", 150) if ch_cfg and not isinstance(ch_cfg, dict) else (ch_cfg or {}).get("overlap", 150) if ch_cfg else 150
                splitter = getattr(ch_cfg, "splitter", "by_sentence") if ch_cfg and not isinstance(ch_cfg, dict) else (ch_cfg or {}).get("splitter", "by_sentence") if ch_cfg else "by_sentence"
                chunks.extend(chunk_text(doc_id=doc.id, text=doc.text, max_tokens=max_tokens, overlap=overlap, splitter=splitter))

    # Execute steps
    context_all: Dict[str, List[Any]] = {}
    prompts_used: List[Dict[str, str]] = []
    metrics = {"tokens_prompt": 0, "tokens_completion": 0}

    for step in chain.steps:
        tmpl, pmeta = _load_prompt_text(step.prompt, registry=registry)
        prompts_used.append(pmeta)

        def run_one(ck):
            vars_ctx = {
                "chunk": {"text": ck.text, "source_uri": next((d.source_uri for d in documents if d.id == ck.doc_id), "")},
                "all": {k: v for k, v in context_all.items()},
            }
            # Interpolate inputs into a dict for template context
            inputs = {k: _interp(v, {**vars_ctx}) for k, v in (step.inputs or {}).items()}
            # Merge into template: allow {{ var }} style via simple replace of ${var}
            # Build a user message combining template and rendered inputs
            body = tmpl
            for k, v in inputs.items():
                body = body.replace("{{ " + k + " }}", str(v))
                body = body.replace("${" + k + "}", str(v))
            messages = [Message(role="system", content="You are a helpful assistant."), Message(role="user", content=body)]
            params = step.params or {}
            with trace_span(f"step.{step.id}"):
                comp: Completion = client.complete(
                    messages,
                    temperature=params.get("temperature"),
                    max_tokens=params.get("max_tokens"),
                )
            return comp

        results: List[str] = []
        errors = 0
        with ThreadPoolExecutor(max_workers=max(1, int(chain.concurrency))) as ex:
            futs = {ex.submit(run_one, ck): ck for ck in chunks}
            for fut in as_completed(futs):
                try:
                    comp = fut.result()
                    metrics["tokens_prompt"] += comp.prompt_tokens or 0
                    metrics["tokens_completion"] += comp.completion_tokens or 0
                    results.append(comp.text)
                except Exception:
                    errors += 1
                    if not chain.continue_on_error:
                        raise
        context_all[step.output] = results

    # Persist artefacts and write run.yaml
    run_id = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    paths = persist_artefacts(artefacts_dir=artefacts_dir or "artefacts", run_id=run_id, documents=documents, chunks=chunks)
    run_dir = os.path.dirname(paths["docs"])
    # write outputs.jsonl for the last step by default
    outputs_file = os.path.join(run_dir, "outputs.jsonl")
    if context_all:
        last_key = list(context_all.keys())[-1]
        with open(outputs_file, "w", encoding="utf-8") as f:
            for i, txt in enumerate(context_all[last_key]):
                rec = {
                    "run_id": run_id,
                    "step_id": last_key,
                    "record_id": i,
                    "output": txt,
                }
                f.write(json.dumps(rec) + "\n")

    # Helpers for output serialization
    def _serialize_jsonl(values: List[Any]) -> bytes:
        buf = []
        for i, v in enumerate(values):
            rec = {"run_id": run_id, "record_id": i, "output": v}
            buf.append(json.dumps(rec))
        return ("\n".join(buf) + ("\n" if buf else "")).encode("utf-8")

    def _serialize(values: List[Any], as_fmt: str | None) -> bytes:
        fmt = (as_fmt or "jsonl").lower()
        if fmt == "jsonl":
            return _serialize_jsonl(values)
        # CSV/Parquet handled in later milestone tasks; default to JSONL for now
        return _serialize_jsonl(values)

    # Process 'save' outputs before composing run.yaml
    saved_paths: list[str] = []
    if chain.outputs:
        for out in chain.outputs:
            if not isinstance(out, dict):
                continue
            save_to = out.get("save")
            if not save_to:
                continue
            from_key = out.get("from") or (list(context_all.keys())[-1] if context_all else None)
            if not from_key or from_key not in context_all:
                if not chain.continue_on_error:
                    raise RuntimeError(f"outputs.from references unknown key: {from_key!r}")
                else:
                    continue
            values = context_all[from_key]
            path = save_to.replace("${run_id}", run_id)
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                payload = _serialize(values, out.get("as"))
                with open(path, "wb") as f:
                    f.write(payload)
                saved_paths.append(path)
            except Exception:
                if not chain.continue_on_error:
                    raise

    # metrics
    _metrics.set_value("docs", len(documents))
    _metrics.set_value("chunks", len(chunks))
    cost = None
    try:
        import os as _os

        c_in = float(_os.getenv("FMF_COST_PROMPT_PER_1K", "0") or 0)
        c_out = float(_os.getenv("FMF_COST_COMPLETION_PER_1K", "0") or 0)
        cost = (metrics["tokens_prompt"] / 1000.0) * c_in + (metrics["tokens_completion"] / 1000.0) * c_out
    except Exception:
        cost = None

    run_yaml = {
        "run_id": run_id,
        "profile": getattr(cfg, "run_profile", None) if not isinstance(cfg, dict) else cfg.get("run_profile"),
        "inputs": chain.inputs,
        "prompts_used": prompts_used,
        "provider": {
            "name": getattr(inference_cfg, "provider", None) if not isinstance(inference_cfg, dict) else inference_cfg.get("provider"),
        },
        "metrics": {**metrics, **_metrics.get_all(), "cost_estimate_usd": cost},
        "artefacts": [paths["docs"], paths["chunks"], outputs_file, *saved_paths],
    }
    run_yaml_path = os.path.join(run_dir, "run.yaml")
    with open(run_yaml_path, "w", encoding="utf-8") as f:
        import yaml

        yaml.safe_dump(run_yaml, f)

    # Optional exports configured in chain outputs
    export_cfg = getattr(cfg, "export", None) if not isinstance(cfg, dict) else cfg.get("export")
    sinks = getattr(export_cfg, "sinks", None) if not isinstance(export_cfg, dict) else (export_cfg or {}).get("sinks")

    if chain.outputs and sinks:
        for out in chain.outputs:
            if not isinstance(out, dict):
                continue
            sink_name = out.get("export")
            if not sink_name:
                continue
            # Pick the source step outputs; default to last step
            from_key = out.get("from") or (list(context_all.keys())[-1] if context_all else None)
            if not from_key or from_key not in context_all:
                if not chain.continue_on_error:
                    raise RuntimeError(f"outputs.from references unknown key: {from_key!r}")
                else:
                    continue
            values = context_all[from_key]
            payload = _serialize(values, out.get("as"))
            sink_cfg = next((s for s in sinks if (getattr(s, "name", None) if not isinstance(s, dict) else s.get("name")) == sink_name), None)
            if not sink_cfg:
                continue
            exporter = build_exporter(sink_cfg)
            try:
                exporter.write(payload, context={"run_id": run_id})
                exporter.finalize()
            except Exception:
                if not chain.continue_on_error:
                    raise
    
    # Update artefact index and apply retention
    try:
        from ..processing.persist import update_index, apply_retention

        update_index(artefacts_dir or "artefacts", {
            "run_id": run_id,
            "run_dir": run_dir,
            "run_yaml": run_yaml_path,
        })
        # retention config (env var or cfg field)
        retain = None
        if isinstance(cfg, dict):
            retain = cfg.get("artefacts_retain_last")
        else:
            retain = getattr(cfg, "artefacts_retain_last", None)
        import os as _os

        retain = int(_os.getenv("FMF_ARTEFACTS__RETAIN_LAST", retain or 0) or 0)
        if retain and retain > 0:
            apply_retention(artefacts_dir or "artefacts", retain)
    except Exception:
        pass

    return {"run_id": run_id, "artefacts": paths, "run_dir": run_dir, "metrics": {**metrics, **_metrics.get_all()}}


__all__ = ["run_chain", "load_chain"]
