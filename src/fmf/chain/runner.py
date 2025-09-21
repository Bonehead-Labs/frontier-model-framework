from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from ..connectors import build_connector
from ..processing.loaders import load_document_from_bytes
from ..processing.table_rows import iter_table_rows
from ..processing.chunking import chunk_text, estimate_tokens
from ..types import Chunk, Document
from ..processing.persist import persist_artefacts, ensure_dir
from ..inference.unified import build_llm_client
from ..inference.base_client import Message, Completion
from ..config.loader import load_config
from ..exporters import build_exporter
from ..observability import metrics as _metrics
from ..observability.tracing import trace_span
from ..prompts.registry import build_prompt_registry
from ..rag import build_rag_pipelines
from ..core.ids import chunk_id as compute_chunk_id
from .loader import ChainConfig, ChainStep, load_chain


def _limit_joined(text: str) -> str:
    try:
        import os as _os

        max_chars = int(_os.getenv("FMF_JOIN_MAX_CHARS", "0") or 0)
        if max_chars and max_chars > 0 and len(text) > max_chars:
            return text[:max_chars] + "\n… [truncated]"
    except Exception:
        pass
    return text


def _join_values(values: List[Any], sep: str = "\n") -> str:
    # Optional sampling to avoid extreme sizes
    try:
        import os as _os

        max_items = int(_os.getenv("FMF_JOIN_MAX_ITEMS", "0") or 0)
    except Exception:
        max_items = 0
    if max_items and max_items > 0 and len(values) > max_items:
        values = values[:max_items] + [f"… [+{len(values) - max_items} more]"]
    out = sep.join(map(str, values))
    return _limit_joined(out)


def _interp(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        expr = value[2:-1].strip()
        # Function: join(expr, "sep")
        if expr.startswith("join(") and expr.endswith(")"):
            inner = expr[len("join(") : -1]
            # split on last comma to allow commas in sep strings
            if "," in inner:
                arg_expr, sep_raw = inner.rsplit(",", 1)
                sep = sep_raw.strip()
                # remove surrounding single or double quotes
                if (sep.startswith('"') and sep.endswith('"')) or (sep.startswith("'") and sep.endswith("'")):
                    sep = sep[1:-1]
            else:
                arg_expr, sep = inner, "\n"
            # Evaluate the inner expression as ${...}
            inner_val = _interp("${" + arg_expr.strip() + "}", context)
            if isinstance(inner_val, list):
                return _join_values(inner_val, sep)
            if isinstance(inner_val, str) and ("\n" in inner_val or "\r" in inner_val):
                return _join_values(inner_val.splitlines(), sep)
            return str(inner_val)

        path = expr
        # Support dotted paths e.g., chunk.text or all.prev_output
        cur: Any = context
        for part in path.split("."):
            if part == "*":
                # special: join all lists into single string
                if isinstance(cur, list):
                    return _join_values(cur)
                return cur
            cur = cur.get(part) if isinstance(cur, dict) else getattr(cur, part, None)
        # If result is a list (e.g., all.output), join with newlines by default
        if isinstance(cur, list):
            return _join_values(cur)
        return cur
    return value


def _default_rag_query(ctx: Dict[str, Any]) -> str:
    chunk = ctx.get("chunk")
    if isinstance(chunk, dict):
        for key in ("text", "source_uri"):
            val = chunk.get(key)
            if isinstance(val, str) and val.strip():
                return val
    row = ctx.get("row")
    if isinstance(row, dict):
        if isinstance(row.get("text"), str) and row["text"].strip():
            return row["text"]
        joined = " ".join(str(v) for v in row.values() if isinstance(v, str))
        if joined.strip():
            return joined
    group = ctx.get("group")
    if isinstance(group, dict):
        names = group.get("source_uris")
        if isinstance(names, list) and names:
            return " ".join(map(str, names))
    return ""


def _prepare_rag_context(
    rag_cfg: Dict[str, Any] | None,
    *,
    pipelines: Dict[str, Any],
    records: Dict[str, list[dict]],
    ctx: Dict[str, Any],
) -> tuple[Dict[str, Any], str, list[dict]]:
    if not rag_cfg:
        return {}, "", []
    pipeline_name = rag_cfg.get("pipeline")
    if not pipeline_name:
        return {}, "", []
    pipeline = pipelines.get(pipeline_name)
    if pipeline is None:
        raise RuntimeError(f"RAG pipeline {pipeline_name!r} is not configured")

    query_expr = rag_cfg.get("query")
    if query_expr:
        query_raw = _interp(query_expr, ctx)
    else:
        query_raw = _default_rag_query(ctx)
    if query_raw is None:
        return {}, "", []
    query_text = str(query_raw).strip()
    if not query_text:
        return {}, "", []

    top_k_text = int(rag_cfg.get("top_k_text", 3) or 0)
    top_k_images = int(rag_cfg.get("top_k_images", 0) or 0)
    result = pipeline.retrieve(query_text, top_k_text=top_k_text, top_k_images=top_k_images)

    record = result.to_record()
    record["pipeline"] = pipeline_name
    records.setdefault(pipeline_name, []).append(record)

    extra_inputs: Dict[str, Any] = {}
    text_block = ""
    if result.texts:
        formatted = pipeline.format_text_block(result.texts)
        text_var = rag_cfg.get("text_var", "rag_text")
        if text_var:
            extra_inputs[text_var] = formatted
        if rag_cfg.get("inject_prompt", True):
            text_block = "\n\nRetrieved context:\n" + formatted

    images_payload: list[dict] = []
    if result.images:
        urls = pipeline.image_data_urls(result.images)
        for item, url in zip(result.images, urls):
            images_payload.append(
                {
                    "data_url": url,
                    "source_uri": item.source_uri,
                    "media_type": item.media_type,
                    "metadata": item.metadata,
                }
            )
        image_var = rag_cfg.get("image_var", "rag_images")
        if image_var:
            extra_inputs[image_var] = images_payload

    return extra_inputs, text_block, images_payload


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


def _try_parse_json(text: str) -> Tuple[Any | None, str | None]:
    try:
        return json.loads(text), None
    except Exception as e:
        return None, str(e)


def _repair_json(text: str) -> str:
    # Remove common code fences and prefixes
    t = text.strip()
    if t.startswith("```"):
        # drop first line fence and possible language tag
        t = "\n".join(t.splitlines()[1:])
        if t.endswith("```"):
            t = "\n".join(t.splitlines()[:-1])
    # Extract substring between first '{' and last '}'
    if "{" in t and "}" in t:
        start = t.find("{")
        end = t.rfind("}")
        if start >= 0 and end > start:
            return t[start : end + 1]
    return t


def _validate_min_schema(obj: Any, schema: Dict[str, Any] | None) -> Tuple[bool, str | None]:
    if not schema:
        return True, None
    # Minimal validation: support type: object and required: [...]
    if schema.get("type") == "object" and not isinstance(obj, dict):
        return False, "schema.type=object but got non-object"
    req = schema.get("required")
    if isinstance(req, list) and isinstance(obj, dict):
        missing = [k for k in req if k not in obj]
        if missing:
            return False, f"missing required keys: {', '.join(missing)}"
    return True, None


@dataclass
class RuntimeContext:
    cfg: Any
    chain: ChainConfig
    connector: Any
    registry: Any
    client: Any
    processing_cfg: Any
    inference_cfg: Any
    rag_pipelines: Dict[str, Any]
    rag_records: Dict[str, List[dict]]
    artefacts_dir: str
    run_id: str
    connectors_cfg: Any


@dataclass
class InputCollections:
    documents: List[Document] = field(default_factory=list)
    doc_lookup: Dict[str, Document] = field(default_factory=dict)
    chunks: List[Chunk] = field(default_factory=list)
    rows: List[dict] = field(default_factory=list)
    image_groups: List[List[Document]] = field(default_factory=list)
    input_mode: str | None = None


@dataclass
class ExecutionResult:
    context_all: Dict[str, List[Any]]
    metrics: Dict[str, Any]
    prompts_used: List[Dict[str, str]]


def _prepare_environment(
    chain: ChainConfig,
    *,
    fmf_config_path: str,
    set_overrides: list[str] | None,
) -> RuntimeContext:
    cfg = load_config(fmf_config_path, set_overrides=set_overrides)
    try:
        _metrics.clear()
    except Exception:
        pass

    inference_cfg = getattr(cfg, "inference", None) if not isinstance(cfg, dict) else cfg.get("inference")
    processing_cfg = getattr(cfg, "processing", None) if not isinstance(cfg, dict) else cfg.get("processing")
    artefacts_dir = (
        getattr(cfg, "artefacts_dir", None) if not isinstance(cfg, dict) else cfg.get("artefacts_dir")
    ) or "artefacts"

    connectors_cfg = getattr(cfg, "connectors", None) if not isinstance(cfg, dict) else cfg.get("connectors")
    if not connectors_cfg:
        raise RuntimeError("No connectors configured")

    conn_name = chain.inputs.get("connector")
    target = None
    for c in connectors_cfg:
        nm = getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
        if nm == conn_name:
            target = c
            break
    if not target:
        raise RuntimeError(f"Connector {conn_name!r} not found")
    connector = build_connector(target)

    preg_cfg = getattr(cfg, "prompt_registry", None) if not isinstance(cfg, dict) else cfg.get("prompt_registry")
    registry = build_prompt_registry(preg_cfg)
    client = build_llm_client(inference_cfg)

    rag_cfg = getattr(cfg, "rag", None) if not isinstance(cfg, dict) else cfg.get("rag")
    rag_pipelines = build_rag_pipelines(rag_cfg, connectors=connectors_cfg, processing_cfg=processing_cfg)
    rag_records: Dict[str, List[dict]] = {name: [] for name in rag_pipelines}

    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    return RuntimeContext(
        cfg=cfg,
        chain=chain,
        connector=connector,
        registry=registry,
        client=client,
        processing_cfg=processing_cfg,
        inference_cfg=inference_cfg,
        rag_pipelines=rag_pipelines,
        rag_records=rag_records,
        artefacts_dir=artefacts_dir,
        run_id=run_id,
        connectors_cfg=connectors_cfg,
    )


def _collect_inputs(ctx: RuntimeContext) -> InputCollections:
    chain = ctx.chain
    connector = ctx.connector
    processing_cfg = ctx.processing_cfg

    collections = InputCollections(input_mode=(chain.inputs or {}).get("mode") if isinstance(chain.inputs, dict) else None)

    selector = chain.inputs.get("select")

    with trace_span("chain.inputs", connector=chain.inputs.get("connector"), run_id=ctx.run_id):
        image_docs: list[Document] = []
        for ref in connector.list(selector=selector):
            with connector.open(ref, mode="rb") as fh:
                data = fh.read()
            doc = load_document_from_bytes(
                source_uri=ref.uri,
                filename=ref.name,
                data=data,
                processing_cfg=processing_cfg,
            )
            collections.documents.append(doc)
            collections.doc_lookup[doc.id] = doc

            if collections.input_mode == "table_rows":
                table_cfg = (chain.inputs or {}).get("table", {}) if isinstance(chain.inputs, dict) else {}
                text_col = table_cfg.get("text_column")
                pass_through = table_cfg.get("pass_through")
                header_row = 1
                if processing_cfg is not None:
                    tables_cfg = (
                        getattr(processing_cfg, "tables", None)
                        if not isinstance(processing_cfg, dict)
                        else processing_cfg.get("tables")
                    )
                    if tables_cfg is not None:
                        header_row = (
                            getattr(tables_cfg, "header_row", header_row)
                            if not isinstance(tables_cfg, dict)
                            else tables_cfg.get("header_row", header_row)
                        )
                table_rows = list(
                    iter_table_rows(
                        filename=ref.name,
                        data=data,
                        text_column=text_col,
                        pass_through=pass_through,
                        header_row=header_row or 1,
                    )
                )
                for index, row in enumerate(table_rows):
                    collections.rows.append({
                        "__doc_id": doc.id,
                        "__source_uri": ref.uri,
                        "__row_index": index,
                        **row,
                    })
            elif collections.input_mode == "images_group":
                if doc.blobs:
                    image_docs.append(doc)
            else:
                if doc.text:
                    text_cfg = (
                        getattr(processing_cfg, "text", None)
                        if processing_cfg and not isinstance(processing_cfg, dict)
                        else (processing_cfg or {}).get("text") if processing_cfg else None
                    )
                    chunk_cfg = (
                        getattr(text_cfg, "chunking", None)
                        if text_cfg and not isinstance(text_cfg, dict)
                        else (text_cfg or {}).get("chunking") if text_cfg else None
                    )
                    max_tokens = (
                        getattr(chunk_cfg, "max_tokens", 800)
                        if chunk_cfg and not isinstance(chunk_cfg, dict)
                        else (chunk_cfg or {}).get("max_tokens", 800)
                        if chunk_cfg
                        else 800
                    )
                    overlap = (
                        getattr(chunk_cfg, "overlap", 150)
                        if chunk_cfg and not isinstance(chunk_cfg, dict)
                        else (chunk_cfg or {}).get("overlap", 150)
                        if chunk_cfg
                        else 150
                    )
                    splitter = (
                        getattr(chunk_cfg, "splitter", "by_sentence")
                        if chunk_cfg and not isinstance(chunk_cfg, dict)
                        else (chunk_cfg or {}).get("splitter", "by_sentence")
                        if chunk_cfg
                        else "by_sentence"
                    )
                    collections.chunks.extend(
                        chunk_text(
                            doc_id=doc.id,
                            text=doc.text,
                            max_tokens=max_tokens,
                            overlap=overlap,
                            splitter=splitter,
                        )
                    )
                elif doc.blobs:
                    chunk_identifier = compute_chunk_id(document_id=doc.id, index=0, payload="")
                    collections.chunks.append(
                        Chunk(
                            id=chunk_identifier,
                            doc_id=doc.id,
                            text="",
                            tokens_estimate=estimate_tokens(""),
                            provenance={"index": 0, "splitter": "auto", "length_chars": 0},
                        )
                    )

        if collections.input_mode == "images_group" and image_docs:
            imgs_cfg = (chain.inputs or {}).get("images", {}) if isinstance(chain.inputs, dict) else {}
            group_size = int(imgs_cfg.get("group_size", 4) or 4)
            current: list[Document] = []
            for doc in image_docs:
                current.append(doc)
                if len(current) >= group_size:
                    collections.image_groups.append(current)
                    current = []
            if current:
                collections.image_groups.append(current)

    return collections


def _execute_chain_steps(ctx: RuntimeContext, inputs: InputCollections) -> ExecutionResult:
    chain = ctx.chain
    registry = ctx.registry
    client = ctx.client
    rag_pipelines = ctx.rag_pipelines
    rag_records = ctx.rag_records

    context_all: Dict[str, List[Any]] = {}
    prompts_used: List[Dict[str, str]] = []
    metrics = {"tokens_prompt": 0, "tokens_completion": 0}

    # Local helper reused across modes
    def _decorate_body(body: str, rag_images: list[dict], *, multimodal: bool) -> Tuple[List[dict] | None, str]:
        if multimodal:
            parts = [{"type": "text", "text": body}]
            return parts, body
        if rag_images:
            refs = "\n".join(f"[{idx}] {img.get('source_uri', '')}" for idx, img in enumerate(rag_images, start=1))
            if refs:
                body = body + "\n\nRetrieved images:\n" + refs
        return None, body

    for step in chain.steps:
        tmpl, pmeta = _load_prompt_text(step.prompt, registry=registry)
        prompts_used.append(pmeta)

        if inputs.input_mode == "table_rows":

            def run_one_row(row_data: dict):
                doc = None
                doc_id = row_data.get("__doc_id")
                if isinstance(doc_id, str):
                    doc = inputs.doc_lookup.get(doc_id)
                vars_ctx = {
                    "row": {k: v for k, v in row_data.items() if not k.startswith("__")},
                    "all": {k: v for k, v in context_all.items()},
                }
                if doc is not None:
                    vars_ctx["document"] = doc
                inputs_rendered = {k: _interp(v, {**vars_ctx}) for k, v in (step.inputs or {}).items()}
                ctx_dict = {**vars_ctx, "inputs": inputs_rendered}
                extra_inputs, rag_text_block, rag_images = _prepare_rag_context(
                    step.rag,
                    pipelines=rag_pipelines,
                    records=rag_records,
                    ctx=ctx_dict,
                )
                inputs_rendered.update(extra_inputs)
                body = tmpl
                for k, v in inputs_rendered.items():
                    body = body.replace("{{ " + k + " }}", str(v))
                    body = body.replace("${" + k + "}", str(v))
                if rag_text_block:
                    body += rag_text_block
                multimodal = (step.mode or "").lower() == "multimodal"
                parts, body = _decorate_body(body, rag_images, multimodal=multimodal)
                if multimodal:
                    import base64 as _b64

                    if doc and doc.blobs:
                        for blob in doc.blobs:
                            if blob.data is None:
                                continue
                            url = f"data:{blob.media_type};base64,{_b64.b64encode(blob.data).decode('ascii')}"
                            parts.append({"type": "image_url", "url": url})
                    for img in rag_images:
                        url = img.get("data_url")
                        if url:
                            parts.append({"type": "image_url", "url": url})
                    messages = [
                        Message(role="system", content="You are a helpful assistant."),
                        Message(role="user", content=parts),
                    ]
                else:
                    messages = [
                        Message(role="system", content="You are a helpful assistant."),
                        Message(role="user", content=body),
                    ]
                params = step.params or {}
                with trace_span(f"step.{step.id}", step_id=step.id, run_id=ctx.run_id):
                    completion: Completion = client.complete(
                        messages,
                        temperature=params.get("temperature"),
                        max_tokens=params.get("max_tokens"),
                    )
                return completion

            results: List[Any] = []
            errors = 0
            with ThreadPoolExecutor(max_workers=max(1, int(chain.concurrency))) as ex:
                futures = {ex.submit(run_one_row, row): row for row in inputs.rows}
                for fut in as_completed(futures):
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
            continue

        if inputs.input_mode == "images_group":

            def run_one_group(group_docs: list[Document]):
                vars_ctx = {
                    "group": {"size": len(group_docs), "source_uris": [d.source_uri for d in group_docs]},
                    "all": {k: v for k, v in context_all.items()},
                }
                inputs_rendered = {k: _interp(v, {**vars_ctx}) for k, v in (step.inputs or {}).items()}
                ctx_dict = {**vars_ctx, "inputs": inputs_rendered}
                extra_inputs, rag_text_block, rag_images = _prepare_rag_context(
                    step.rag,
                    pipelines=rag_pipelines,
                    records=rag_records,
                    ctx=ctx_dict,
                )
                inputs_rendered.update(extra_inputs)
                body = tmpl
                for k, v in inputs_rendered.items():
                    body = body.replace("{{ " + k + " }}", str(v))
                    body = body.replace("${" + k + "}", str(v))
                if rag_text_block:
                    body += rag_text_block
                parts = [{"type": "text", "text": body}]
                import base64 as _b64

                for document in group_docs:
                    for blob in document.blobs or []:
                        if blob.data is None:
                            continue
                        url = f"data:{blob.media_type};base64,{_b64.b64encode(blob.data).decode('ascii')}"
                        parts.append({"type": "image_url", "url": url})
                for img in rag_images:
                    url = img.get("data_url")
                    if url:
                        parts.append({"type": "image_url", "url": url})
                messages = [
                    Message(role="system", content="You are a helpful assistant."),
                    Message(role="user", content=parts),
                ]
                params = step.params or {}
                with trace_span(f"step.{step.id}", step_id=step.id, run_id=ctx.run_id):
                    return client.complete(
                        messages,
                        temperature=params.get("temperature"),
                        max_tokens=params.get("max_tokens"),
                    )

            results: List[Any] = []
            errors = 0
            with ThreadPoolExecutor(max_workers=max(1, int(chain.concurrency))) as ex:
                futures = {ex.submit(run_one_group, group): group for group in inputs.image_groups}
                for fut in as_completed(futures):
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
            continue

        def run_one_chunk(chunk: Chunk):
            doc = inputs.doc_lookup.get(chunk.doc_id)
            vars_ctx = {
                "chunk": {"text": chunk.text, "source_uri": doc.source_uri if doc else ""},
                "all": {k: v for k, v in context_all.items()},
            }
            if doc is not None:
                vars_ctx["document"] = doc.to_serializable()
            inputs_rendered = {k: _interp(v, {**vars_ctx}) for k, v in (step.inputs or {}).items()}
            ctx_dict = {**vars_ctx, "inputs": inputs_rendered}
            extra_inputs, rag_text_block, rag_images = _prepare_rag_context(
                step.rag,
                pipelines=rag_pipelines,
                records=rag_records,
                ctx=ctx_dict,
            )
            inputs_rendered.update(extra_inputs)
            body = tmpl
            for k, v in inputs_rendered.items():
                body = body.replace("{{ " + k + " }}", str(v))
                body = body.replace("${" + k + "}", str(v))
            if rag_text_block:
                body += rag_text_block
            multimodal = (step.mode or "").lower() == "multimodal"
            parts, body = _decorate_body(body, rag_images, multimodal=multimodal)
            if multimodal:
                import base64 as _b64

                if doc and doc.blobs:
                    for blob in doc.blobs:
                        if blob.data is None:
                            continue
                        url = f"data:{blob.media_type};base64,{_b64.b64encode(blob.data).decode('ascii')}"
                        parts.append({"type": "image_url", "url": url})
                for img in rag_images:
                    url = img.get("data_url")
                    if url:
                        parts.append({"type": "image_url", "url": url})
                messages = [
                    Message(role="system", content="You are a helpful assistant."),
                    Message(role="user", content=parts),
                ]
            else:
                messages = [
                    Message(role="system", content="You are a helpful assistant."),
                    Message(role="user", content=body),
                ]
            params = step.params or {}
            with trace_span(f"step.{step.id}", step_id=step.id, run_id=ctx.run_id):
                completion: Completion = client.complete(
                    messages,
                    temperature=params.get("temperature"),
                    max_tokens=params.get("max_tokens"),
                )
            if (step.output_expects or "").lower() == "json":
                retries = max(0, int(step.output_parse_retries or 0))
                parsed, err = _try_parse_json(completion.text)
                attempts = 0
                while parsed is None and attempts < retries:
                    repaired = _repair_json(completion.text)
                    parsed, err = _try_parse_json(repaired)
                    attempts += 1
                if parsed is None:
                    try:
                        _metrics.inc("json_parse_failures", 1)
                        _metrics.inc(f"json_parse_failures.{step.id}", 1)
                    except Exception:
                        pass
                    return type("C", (), {
                        "text": {"parse_error": True, "raw_text": completion.text},
                        "prompt_tokens": completion.prompt_tokens,
                        "completion_tokens": completion.completion_tokens,
                    })()
                ok, schema_err = _validate_min_schema(parsed, step.output_schema)
                if not ok:
                    try:
                        _metrics.inc("json_parse_failures", 1)
                        _metrics.inc(f"json_parse_failures.{step.id}", 1)
                    except Exception:
                        pass
                    return type("C", (), {
                        "text": {
                            "parse_error": True,
                            "raw_text": completion.text,
                            "schema_error": schema_err,
                        },
                        "prompt_tokens": completion.prompt_tokens,
                        "completion_tokens": completion.completion_tokens,
                    })()
                return type("C", (), {
                    "text": parsed,
                    "prompt_tokens": completion.prompt_tokens,
                    "completion_tokens": completion.completion_tokens,
                })()
            return completion

        results: List[Any] = []
        errors = 0
        with ThreadPoolExecutor(max_workers=max(1, int(chain.concurrency))) as ex:
            futures = {ex.submit(run_one_chunk, chunk): chunk for chunk in inputs.chunks}
            for fut in as_completed(futures):
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

    return ExecutionResult(context_all=context_all, metrics=metrics, prompts_used=prompts_used)


def _serialize_jsonl(values: List[Any], *, run_id: str) -> bytes:
    buffer = []
    for idx, value in enumerate(values):
        record = {"run_id": run_id, "record_id": idx, "output": value}
        buffer.append(json.dumps(record))
    return ("\n".join(buffer) + ("\n" if buffer else "")).encode("utf-8")


def _serialize_outputs(values: List[Any], *, as_fmt: str | None, run_id: str) -> bytes:
    fmt = (as_fmt or "jsonl").lower()
    if fmt == "jsonl":
        return _serialize_jsonl(values, run_id=run_id)
    if fmt == "csv":
        import csv as _csv
        import io as _io

        buf = _io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(["output"])
        for value in values:
            writer.writerow([str(value)])
        return buf.getvalue().encode("utf-8")
    if fmt == "parquet":
        try:
            import io as _io
            import pyarrow as pa  # type: ignore
            import pyarrow.parquet as pq  # type: ignore

            arr = pa.array([str(v) for v in values])
            table = pa.table({"output": arr})
            bio = _io.BytesIO()
            pq.write_table(table, bio)
            return bio.getvalue()
        except Exception as exc:
            raise RuntimeError("Parquet serialization requires optional dependency 'pyarrow'.") from exc
    return _serialize_jsonl(values, run_id=run_id)


def _finalize_run(
    ctx: RuntimeContext,
    inputs: InputCollections,
    exec_result: ExecutionResult,
) -> Dict[str, Any]:
    artefact_paths = persist_artefacts(
        artefacts_dir=ctx.artefacts_dir,
        run_id=ctx.run_id,
        documents=inputs.documents,
        chunks=inputs.chunks,
    )
    run_dir = os.path.dirname(artefact_paths["docs"])
    outputs_file = os.path.join(run_dir, "outputs.jsonl")

    if exec_result.context_all:
        last_key = list(exec_result.context_all.keys())[-1]
        with open(outputs_file, "w", encoding="utf-8") as handle:
            for idx, txt in enumerate(exec_result.context_all[last_key]):
                record = {
                    "run_id": ctx.run_id,
                    "step_id": last_key,
                    "record_id": idx,
                    "output": txt,
                }
                handle.write(json.dumps(record) + "\n")

    rows_file = None
    if inputs.input_mode == "table_rows":
        rows_file = os.path.join(run_dir, "rows.jsonl")
        with open(rows_file, "w", encoding="utf-8") as handle:
            for row in inputs.rows:
                entry = {
                    "doc_id": row.get("__doc_id"),
                    "source_uri": row.get("__source_uri"),
                    "row_index": row.get("__row_index"),
                    "row": {k: v for k, v in row.items() if not k.startswith("__")},
                }
                handle.write(json.dumps(entry) + "\n")

    saved_paths: list[str] = []
    if ctx.chain.outputs:
        for out in ctx.chain.outputs:
            if not isinstance(out, dict):
                continue
            save_to = out.get("save")
            if not save_to:
                continue
            from_key = out.get("from") or (list(exec_result.context_all.keys())[-1] if exec_result.context_all else None)
            if not from_key or from_key not in exec_result.context_all:
                if not ctx.chain.continue_on_error:
                    raise RuntimeError(f"outputs.from references unknown key: {from_key!r}")
                continue
            values = exec_result.context_all[from_key]
            path = save_to.replace("${run_id}", ctx.run_id)
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                payload = _serialize_outputs(values, as_fmt=out.get("as"), run_id=ctx.run_id)
                with open(path, "wb") as handle:
                    handle.write(payload)
                saved_paths.append(path)
            except Exception:
                if not ctx.chain.continue_on_error:
                    raise

    rag_paths: list[str] = []
    if ctx.rag_records:
        rag_dir = os.path.join(run_dir, "rag")
        ensure_dir(rag_dir)
        for pipeline, entries in ctx.rag_records.items():
            if not entries:
                continue
            path = os.path.join(rag_dir, f"{pipeline}.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                for record in entries:
                    handle.write(json.dumps(record) + "\n")
            rag_paths.append(path)

    _metrics.set_value("docs", len(inputs.documents))
    _metrics.set_value("chunks", len(inputs.chunks))

    cost = None
    try:
        import os as _os

        prompt_cost = float(_os.getenv("FMF_COST_PROMPT_PER_1K", "0") or 0)
        completion_cost = float(_os.getenv("FMF_COST_COMPLETION_PER_1K", "0") or 0)
        cost = (
            (exec_result.metrics["tokens_prompt"] / 1000.0) * prompt_cost
            + (exec_result.metrics["tokens_completion"] / 1000.0) * completion_cost
        )
    except Exception:
        cost = None

    artefacts_list = [artefact_paths["docs"], artefact_paths["chunks"], outputs_file]
    if rows_file:
        artefacts_list.append(rows_file)
    artefacts_list.extend(saved_paths)
    artefacts_list.extend(rag_paths)

    run_yaml = {
        "run_id": ctx.run_id,
        "profile": getattr(ctx.cfg, "run_profile", None) if not isinstance(ctx.cfg, dict) else ctx.cfg.get("run_profile"),
        "inputs": ctx.chain.inputs,
        "prompts_used": exec_result.prompts_used,
        "provider": {
            "name": getattr(ctx.inference_cfg, "provider", None)
            if not isinstance(ctx.inference_cfg, dict)
            else ctx.inference_cfg.get("provider"),
        },
        "metrics": {**exec_result.metrics, **_metrics.get_all(), "cost_estimate_usd": cost},
        "artefacts": artefacts_list,
    }

    run_yaml_path = os.path.join(run_dir, "run.yaml")
    with open(run_yaml_path, "w", encoding="utf-8") as handle:
        import yaml

        yaml.safe_dump(run_yaml, handle)

    export_cfg = getattr(ctx.cfg, "export", None) if not isinstance(ctx.cfg, dict) else ctx.cfg.get("export")
    sinks = (
        getattr(export_cfg, "sinks", None)
        if not isinstance(export_cfg, dict)
        else (export_cfg or {}).get("sinks")
    )

    if ctx.chain.outputs and sinks:
        for out in ctx.chain.outputs:
            if not isinstance(out, dict):
                continue
            sink_name = out.get("export")
            if not sink_name:
                continue
            from_key = out.get("from") or (list(exec_result.context_all.keys())[-1] if exec_result.context_all else None)
            if not from_key or from_key not in exec_result.context_all:
                if not ctx.chain.continue_on_error:
                    raise RuntimeError(f"outputs.from references unknown key: {from_key!r}")
                continue
            values = exec_result.context_all[from_key]
            payload = _serialize_outputs(values, as_fmt=out.get("as"), run_id=ctx.run_id)
            sink_cfg = next(
                (
                    s
                    for s in sinks
                    if (getattr(s, "name", None) if not isinstance(s, dict) else s.get("name")) == sink_name
                ),
                None,
            )
            if not sink_cfg:
                continue
            exporter = build_exporter(sink_cfg)
            try:
                exporter.write(payload, context={"run_id": ctx.run_id})
                exporter.finalize()
            except Exception:
                if not ctx.chain.continue_on_error:
                    raise

    try:
        from ..processing.persist import update_index, apply_retention

        update_index(
            ctx.artefacts_dir,
            {
                "run_id": ctx.run_id,
                "run_dir": run_dir,
                "run_yaml": run_yaml_path,
            },
        )
        retain = None
        if isinstance(ctx.cfg, dict):
            retain = ctx.cfg.get("artefacts_retain_last")
        else:
            retain = getattr(ctx.cfg, "artefacts_retain_last", None)
        import os as _os

        retain = int(_os.getenv("FMF_ARTEFACTS__RETAIN_LAST", retain or 0) or 0)
        if retain and retain > 0:
            apply_retention(ctx.artefacts_dir, retain)
    except Exception:
        pass

    return {
        "run_id": ctx.run_id,
        "artefacts": artefact_paths,
        "run_dir": run_dir,
        "metrics": {**exec_result.metrics, **_metrics.get_all()},
    }


def run_chain(
    chain_path: str,
    *,
    fmf_config_path: str = "fmf.yaml",
    set_overrides: list[str] | None = None,
) -> Dict[str, Any]:
    chain = load_chain(chain_path)
    # Delegate to the core execution with a loaded ChainConfig
    return _run_chain_loaded(
        chain,
        fmf_config_path=fmf_config_path,
        set_overrides=set_overrides,
    )


def run_chain_config(
    conf: ChainConfig | Dict[str, Any],
    *,
    fmf_config_path: str = "fmf.yaml",
    set_overrides: list[str] | None = None,
) -> Dict[str, Any]:
    """Programmatic runner that accepts a ChainConfig or a plain dict.

    For compatibility and to avoid duplicating run logic, this function
    serializes the chain to a temporary YAML file and reuses run_chain.
    """
    import tempfile as _tmp
    import yaml as _yaml

    # Convert ChainConfig to a dict similar to on-disk YAML
    if isinstance(conf, ChainConfig):
        data: Dict[str, Any] = {
            "name": conf.name,
            "inputs": conf.inputs,
            "steps": [],
            "outputs": conf.outputs,
            "concurrency": conf.concurrency,
            "continue_on_error": conf.continue_on_error,
        }
        for s in conf.steps:
            out_val: Any = s.output
            if s.output_expects or s.output_schema or s.output_parse_retries:
                out_val = {
                    "name": s.output,
                    "expects": s.output_expects,
                    "schema": s.output_schema,
                    "parse_retries": s.output_parse_retries,
                }
            data["steps"].append({
                "id": s.id,
                "prompt": s.prompt,
                "inputs": s.inputs,
                "output": out_val,
                "params": s.params,
                "mode": s.mode,
            })
    else:
        data = conf  # assume dict

    with _tmp.TemporaryDirectory() as tdir:
        path = os.path.join(tdir, "chain.yaml")
        with open(path, "w", encoding="utf-8") as f:
            _yaml.safe_dump(data, f, sort_keys=False)
        return run_chain(path, fmf_config_path=fmf_config_path, set_overrides=set_overrides)
def _run_chain_loaded(
    chain: ChainConfig,
    *,
    fmf_config_path: str,
    set_overrides: list[str] | None = None,
) -> Dict[str, Any]:
    ctx = _prepare_environment(
        chain,
        fmf_config_path=fmf_config_path,
        set_overrides=set_overrides,
    )
    inputs = _collect_inputs(ctx)
    exec_result = _execute_chain_steps(ctx, inputs)
    return _finalize_run(ctx, inputs, exec_result)



__all__ = ["run_chain", "run_chain_config", "load_chain"]
