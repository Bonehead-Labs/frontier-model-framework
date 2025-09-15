from __future__ import annotations

import argparse
import sys
from typing import List

from .config.loader import load_config
from .auth import build_provider, AuthError
from .observability.logging import setup_logging
from .connectors import build_connector
from .processing.loaders import load_document_from_bytes
from .processing.chunking import chunk_text
from .processing.persist import persist_artefacts
import datetime as _dt
import os as _os
import uuid as _uuid
from .inference.unified import build_llm_client
from .inference.base_client import Message
from .chain.runner import run_chain
from .exporters import build_exporter
from .sdk import FMF


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fmf",
        description="Frontier Model Framework CLI",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="{keys,connect,process,prompt,run,infer,export}")
    # Extend metavar to include sdk wrappers
    subparsers.metavar = "{keys,connect,process,prompt,run,infer,export,csv,text,images}"

    # keys subcommands
    keys = subparsers.add_parser("keys", help="Manage/test secret resolution")
    keys_sub = keys.add_subparsers(dest="keys_cmd")
    keys_test = keys_sub.add_parser("test", help="Verify secret resolution for given names")
    keys_test.add_argument("names", nargs="*", help="Logical secret names to resolve (e.g., OPENAI_API_KEY)")
    keys_test.add_argument(
        "-c", "--config", default="fmf.yaml", help="Path to config YAML (default: fmf.yaml)"
    )
    keys_test.add_argument(
        "--set",
        dest="set_overrides",
        action="append",
        default=[],
        help="Override config values: key.path=value (repeatable)",
    )
    # connect subcommands
    connect = subparsers.add_parser("connect", help="List and interact with data connectors")
    connect_sub = connect.add_subparsers(dest="connect_cmd")
    connect_ls = connect_sub.add_parser("ls", help="List resources for a configured connector")
    connect_ls.add_argument("name", help="Connector name from config")
    connect_ls.add_argument(
        "--select",
        dest="selector",
        action="append",
        default=[],
        help="Glob selector(s) relative to connector root (repeatable)",
    )
    connect_ls.add_argument("-c", "--config", default="fmf.yaml", help="Path to config YAML")
    connect_ls.add_argument(
        "--set",
        dest="set_overrides",
        action="append",
        default=[],
        help="Override config values: key.path=value (repeatable)",
    )

    # process subcommand
    process = subparsers.add_parser("process", help="Process and chunk input data to artefacts")
    process.add_argument("--connector", required=True, help="Connector name to read inputs from")
    process.add_argument(
        "--select",
        dest="selector",
        action="append",
        default=[],
        help="Glob selector(s) for inputs (repeatable)",
    )

    # run chain
    run_cmd = subparsers.add_parser("run", help="Execute a chain from YAML")
    run_cmd.add_argument("--chain", required=True, help="Path to chain YAML")
    run_cmd.add_argument("-c", "--config", default="fmf.yaml", help="Path to config YAML")
    process.add_argument("-c", "--config", default="fmf.yaml", help="Path to config YAML")
    process.add_argument(
        "--set",
        dest="set_overrides",
        action="append",
        default=[],
        help="Override config values: key.path=value (repeatable)",
    )
    # prompt
    prompt = subparsers.add_parser("prompt", help="Prompt registry operations")
    prompt_sub = prompt.add_subparsers(dest="prompt_cmd")
    prompt_reg = prompt_sub.add_parser("register", help="Register a prompt file#version in the registry")
    prompt_reg.add_argument("ref", help="Prompt reference: path#version or id#version")
    prompt_reg.add_argument("-c", "--config", default="fmf.yaml", help="Path to config YAML")
    # infer
    infer = subparsers.add_parser("infer", help="Single-shot inference using a prompt version")
    infer.add_argument("--input", required=True, help="Path to input text file")
    infer.add_argument("-c", "--config", default="fmf.yaml", help="Path to config YAML")
    infer.add_argument(
        "--set",
        dest="set_overrides",
        action="append",
        default=[],
        help="Override config values: key.path=value (repeatable)",
    )
    infer.add_argument("--system", default="You are a helpful assistant.", help="Optional system prompt")
    export = subparsers.add_parser("export", help="Export artefacts/results to configured sinks")
    export.add_argument("--sink", required=True, help="Sink name as defined in config export.sinks")
    export.add_argument("--input", required=True, help="Path to input file (e.g., artefacts/<run_id>/outputs.jsonl)")
    export.add_argument("-c", "--config", default="fmf.yaml", help="Path to config YAML")

    # doctor command
    doctor = subparsers.add_parser("doctor", help="Diagnostics: print inferred provider and connectors")
    doctor.add_argument("-c", "--config", default="fmf.yaml", help="Path to config YAML")

    # SDK wrappers: csv analyse
    csv_cmd = subparsers.add_parser("csv", help="CSV workflows (SDK)")
    csv_sub = csv_cmd.add_subparsers(dest="csv_cmd")
    csv_an = csv_sub.add_parser("analyse", help="Analyse CSV comments per-row and save outputs")
    csv_an.add_argument("--input", required=True, help="Path to CSV file")
    csv_an.add_argument("--text-col", default="Comment")
    csv_an.add_argument("--id-col", default="ID")
    csv_an.add_argument("--prompt", required=True)
    csv_an.add_argument("--save-csv", default=None)
    csv_an.add_argument("--save-jsonl", default=None)
    csv_an.add_argument("-c", "--config", default="fmf.yaml")

    # SDK wrappers: text and images
    text_cmd = subparsers.add_parser("text", help="Text file workflows (SDK)")
    text_sub = text_cmd.add_subparsers(dest="text_cmd")
    text_inf = text_sub.add_parser("infer", help="Infer over text files and save outputs")
    text_inf.add_argument("--select", action="append", default=None)
    text_inf.add_argument("--prompt", required=True)
    text_inf.add_argument("--save-jsonl", default=None)
    text_inf.add_argument("-c", "--config", default="fmf.yaml")

    img_cmd = subparsers.add_parser("images", help="Image workflows (SDK)")
    img_sub = img_cmd.add_subparsers(dest="images_cmd")
    img_an = img_sub.add_parser("analyse", help="Analyse images and save outputs")
    img_an.add_argument("--select", action="append", default=None)
    img_an.add_argument("--prompt", required=True)
    img_an.add_argument("--save-jsonl", default=None)
    img_an.add_argument("-c", "--config", default="fmf.yaml")

    # Recipe runner
    recipe_cmd = subparsers.add_parser("recipe", help="Run high-level recipes (SDK)")
    recipe_sub = recipe_cmd.add_subparsers(dest="recipe_cmd")
    recipe_run = recipe_sub.add_parser("run", help="Run a recipe YAML file")
    recipe_run.add_argument("--file", required=True, help="Path to recipe YAML")
    recipe_run.add_argument("-c", "--config", default="fmf.yaml")
    export.add_argument(
        "--input-format",
        choices=["auto", "jsonl", "csv", "parquet"],
        default="auto",
        help="Input format when exporting (default: auto by extension)",
    )

    return parser


def _cmd_keys_test(args: argparse.Namespace) -> int:
    setup_logging()
    cfg = load_config(args.config, set_overrides=args.set_overrides)
    auth_cfg = getattr(cfg, "auth", None)
    if auth_cfg is None and isinstance(cfg, dict):  # compatibility if validation not applied
        auth_cfg = cfg.get("auth")
    if not auth_cfg:
        print("No 'auth' configuration found in config file.")
        return 2

    names: List[str] = list(getattr(args, "names", []) or [])
    if not names:
        # Try to derive from secret_mapping when present
        prov = getattr(auth_cfg, "provider", None)
        mapping_cfg = None
        if prov == "azure_key_vault":
            mapping_cfg = getattr(auth_cfg, "azure_key_vault", None)
        elif prov == "aws_secrets":
            mapping_cfg = getattr(auth_cfg, "aws_secrets", None)
        if mapping_cfg is not None:
            mapping_dict = getattr(mapping_cfg, "secret_mapping", None) or {}
            names = list(mapping_dict.keys())

    if not names:
        print("No secret names provided and none derivable from config. Provide names after 'keys test'.")
        return 2

    try:
        provider = build_provider(auth_cfg)
        resolved = provider.resolve(names)
    except AuthError as e:
        print(f"Secret resolution failed: {e}")
        return 1

    for n in names:
        status = "OK" if n in resolved else "MISSING"
        print(f"{n}=**** {status}")

    return 0


def _cmd_connect_ls(args: argparse.Namespace) -> int:
    setup_logging()
    cfg = load_config(args.config, set_overrides=args.set_overrides)
    connectors = getattr(cfg, "connectors", None)
    if connectors is None and isinstance(cfg, dict):
        connectors = cfg.get("connectors")
    if not connectors:
        print("No connectors configured.")
        return 2

    target = None
    for c in connectors:
        name = getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
        if name == args.name:
            target = c
            break
    if target is None:
        print(f"Connector '{args.name}' not found in config.")
        return 2

    conn = build_connector(target)
    selector = args.selector or None
    for ref in conn.list(selector=selector):
        print(f"{ref.id}\t{ref.uri}")
    return 0


def _gen_run_id() -> str:
    ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    rand = _uuid.uuid4().hex[:6]
    return f"{ts}-{rand}"


def _cmd_process(args: argparse.Namespace) -> int:
    setup_logging()
    cfg = load_config(args.config, set_overrides=args.set_overrides)
    connectors = getattr(cfg, "connectors", None)
    processing_cfg = getattr(cfg, "processing", None)
    artefacts_dir = getattr(cfg, "artefacts_dir", None)
    if isinstance(cfg, dict):
        connectors = connectors or cfg.get("connectors")
        processing_cfg = processing_cfg or cfg.get("processing")
        artefacts_dir = artefacts_dir or cfg.get("artefacts_dir")
    if not connectors:
        print("No connectors configured.")
        return 2

    target = None
    for c in connectors:
        name = getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
        if name == args.connector:
            target = c
            break
    if target is None:
        print(f"Connector '{args.connector}' not found in config.")
        return 2

    conn = build_connector(target)
    selector = args.selector or None
    documents = []
    chunks = []
    for ref in conn.list(selector=selector):
        with conn.open(ref, mode="rb") as f:
            data = f.read()
        doc = load_document_from_bytes(source_uri=ref.uri, filename=ref.name, data=data, processing_cfg=processing_cfg)
        documents.append(doc)
        # chunking for text content
        text_cfg = getattr(processing_cfg, "text", None) if not isinstance(processing_cfg, dict) else (processing_cfg or {}).get("text")
        ch_cfg = getattr(text_cfg, "chunking", None) if text_cfg and not isinstance(text_cfg, dict) else (text_cfg or {}).get("chunking") if text_cfg else None
        max_tokens = getattr(ch_cfg, "max_tokens", 800) if ch_cfg and not isinstance(ch_cfg, dict) else (ch_cfg or {}).get("max_tokens", 800) if ch_cfg else 800
        overlap = getattr(ch_cfg, "overlap", 150) if ch_cfg and not isinstance(ch_cfg, dict) else (ch_cfg or {}).get("overlap", 150) if ch_cfg else 150
        splitter = getattr(ch_cfg, "splitter", "by_sentence") if ch_cfg and not isinstance(ch_cfg, dict) else (ch_cfg or {}).get("splitter", "by_sentence") if ch_cfg else "by_sentence"
        if doc.text:
            chunks.extend(chunk_text(doc_id=doc.id, text=doc.text, max_tokens=max_tokens, overlap=overlap, splitter=splitter))

    run_id = _gen_run_id()
    out = persist_artefacts(artefacts_dir=artefacts_dir or "artefacts", run_id=run_id, documents=documents, chunks=chunks)
    print(f"run_id={run_id}")
    print(f"docs={out['docs']}")
    print(f"chunks={out['chunks']}")
    return 0


def _cmd_infer(args: argparse.Namespace) -> int:
    setup_logging()
    cfg = load_config(args.config, set_overrides=args.set_overrides)
    inference_cfg = getattr(cfg, "inference", None)
    if inference_cfg is None and isinstance(cfg, dict):
        inference_cfg = cfg.get("inference")
    if not inference_cfg:
        print("No inference config in YAML.")
        return 2
    client = build_llm_client(inference_cfg)
    with open(args.input, "r", encoding="utf-8") as f:
        user_text = f.read()
    messages = [Message(role="system", content=args.system), Message(role="user", content=user_text)]
    comp = client.complete(messages, temperature=None, max_tokens=None)
    print(comp.text)
    return 0


def _extract_run_id_from_path(path: str) -> str | None:
    # naive extraction: find 'artefacts/<run_id>/' pattern
    parts = path.split("/")
    for i, p in enumerate(parts):
        if p == "artefacts" and i + 1 < len(parts):
            return parts[i + 1]
    return None


def _cmd_export(args: argparse.Namespace) -> int:
    setup_logging()
    cfg = load_config(args.config)
    export_cfg = getattr(cfg, "export", None) if not isinstance(cfg, dict) else cfg.get("export")
    if not export_cfg:
        print("No export configuration in YAML.")
        return 2
    sinks = getattr(export_cfg, "sinks", None) if not isinstance(export_cfg, dict) else export_cfg.get("sinks")
    if not sinks:
        print("No sinks configured.")
        return 2
    target = None
    for s in sinks:
        name = getattr(s, "name", None) if not isinstance(s, dict) else s.get("name")
        if name == args.sink:
            target = s
            break
    if not target:
        print(f"Sink '{args.sink}' not found.")
        return 2
    exp = build_exporter(target)

    # Determine sink type from target config for ergonomics
    sink_type = getattr(target, "type", None) if not isinstance(target, dict) else target.get("type")

    def _detect_format(path: str, arg: str) -> str:
        if arg and arg != "auto":
            return arg
        lower = path.lower()
        if lower.endswith(".jsonl") or lower.endswith(".jsonl.gz"):
            return "jsonl"
        if lower.endswith(".csv") or lower.endswith(".csv.gz"):
            return "csv"
        if lower.endswith(".parquet"):
            return "parquet"
        # Default to jsonl
        return "jsonl"

    def _load_records(path: str, fmt: str) -> list[dict]:
        if fmt == "jsonl":
            import gzip as _gzip

            opener = open
            if path.lower().endswith(".gz"):
                opener = _gzip.open  # type: ignore[assignment]
            rows: list[dict] = []
            with opener(path, "rt", encoding="utf-8") as f:  # type: ignore[misc]
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        import json as _json

                        rows.append(_json.loads(s))
                    except Exception:
                        raise SystemExit(2)
            return rows
        if fmt == "csv":
            import csv as _csv
            rows: list[dict] = []
            with open(path, "r", encoding="utf-8") as f:
                r = _csv.DictReader(f)
                for rec in r:
                    rows.append({k: v for k, v in rec.items()})
            return rows
        if fmt == "parquet":
            try:
                import pyarrow.parquet as pq  # type: ignore
            except Exception:
                print("Parquet input requires optional dependency 'pyarrow'.", file=sys.stderr)
                raise SystemExit(2)
            table = pq.read_table(path)
            return table.to_pylist()  # list of dicts
        raise SystemExit(2)

    fmt = _detect_format(args.input, getattr(args, "input_format", "auto"))
    run_id = _extract_run_id_from_path(args.input)

    # Decide if sink requires records
    record_sinks = {"dynamodb", "sharepoint_excel", "redshift", "fabric_delta"}
    if sink_type in record_sinks:
        # load records and send as iterable of dicts
        records = _load_records(args.input, fmt)
        res = exp.write(records, context={"run_id": run_id})
    else:
        # pass raw bytes (S3, Delta)
        with open(args.input, "rb") as f:
            payload = f.read()
        res = exp.write(payload, context={"run_id": run_id})
    exp.finalize()
    for p in res.paths:
        print(p)
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        # Defer importing package to avoid side-effects at import time
        try:
            import importlib.metadata as importlib_metadata  # py3.8+
        except Exception:  # pragma: no cover - fallback unlikely needed on 3.12
            import importlib_metadata  # type: ignore

        try:
            version = importlib_metadata.version("frontier-model-framework")
        except importlib_metadata.PackageNotFoundError:
            version = "0.0.0+local"
        print(version)
        return 0

    # For now, show help when no subcommand is provided
    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    if args.command == "keys" and getattr(args, "keys_cmd", None) == "test":
        return _cmd_keys_test(args)
    if args.command == "connect" and getattr(args, "connect_cmd", None) == "ls":
        return _cmd_connect_ls(args)
    if args.command == "process":
        return _cmd_process(args)
    if args.command == "infer":
        return _cmd_infer(args)
    if args.command == "run":
        # Delegate directly to chain runner
        res = run_chain(args.chain, fmf_config_path=args.config)
        print(f"run_id={res['run_id']}")
        print(f"run_dir={res['run_dir']}")
        return 0
    if args.command == "export":
        return _cmd_export(args)
    # SDK wrappers
    if args.command == "csv" and getattr(args, "csv_cmd", None) == "analyse":
        f = FMF.from_env(args.config)
        f.csv_analyse(
            input=args.input,
            text_col=args.text_col,
            id_col=args.id_col,
            prompt=args.prompt,
            save_csv=args.save_csv,
            save_jsonl=args.save_jsonl,
        )
        return 0
    if args.command == "text" and getattr(args, "text_cmd", None) == "infer":
        f = FMF.from_env(args.config)
        f.text_files(prompt=args.prompt, select=args.select, save_jsonl=args.save_jsonl)
        return 0
    if args.command == "images" and getattr(args, "images_cmd", None) == "analyse":
        f = FMF.from_env(args.config)
        f.images_analyse(prompt=args.prompt, select=args.select, save_jsonl=args.save_jsonl)
        return 0
    if args.command == "recipe" and getattr(args, "recipe_cmd", None) == "run":
        f = FMF.from_env(args.config)
        f.run_recipe(args.file)
        return 0
    if args.command == "prompt" and getattr(args, "prompt_cmd", None) == "register":
        from .prompts.registry import build_prompt_registry
        cfg = load_config(args.config)
        preg_cfg = getattr(cfg, "prompt_registry", None) if not isinstance(cfg, dict) else cfg.get("prompt_registry")
        reg = build_prompt_registry(preg_cfg)
        pv = reg.register(args.ref)
        print(f"registered {pv.id}#{pv.version} hash={pv.content_hash}")
        return 0

    if args.command == "doctor":
        # Minimal diagnostics: report provider and first connector
        cfg = load_config(getattr(args, "config", "fmf.yaml"))
        prov = None
        inference_cfg = getattr(cfg, "inference", None) if not isinstance(cfg, dict) else cfg.get("inference")
        prov = getattr(inference_cfg, "provider", None) if not isinstance(inference_cfg, dict) else (inference_cfg or {}).get("provider")
        connectors = getattr(cfg, "connectors", None) if not isinstance(cfg, dict) else cfg.get("connectors")
        first_conn = None
        if connectors:
            c = connectors[0]
            first_conn = (getattr(c, "name", None) if not isinstance(c, dict) else c.get("name"))
        print(f"provider={prov}")
        print(f"connector={first_conn}")
        return 0

    # Stub handlers: print a friendly message for unimplemented commands
    print(f"Command '{args.command}' is not implemented yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
