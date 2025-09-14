from __future__ import annotations

import argparse
import sys
from typing import List

from .config.loader import load_config
from .auth import build_provider, AuthError
from .observability.logging import setup_logging
from .connectors import build_connector


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
    subparsers.add_parser("process", help="Process and chunk input data to artefacts")
    subparsers.add_parser("prompt", help="Prompt registry operations")
    subparsers.add_parser("run", help="Execute a chain from YAML")
    subparsers.add_parser("infer", help="Single-shot inference using a prompt version")
    subparsers.add_parser("export", help="Export artefacts/results to configured sinks")

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

    # Stub handlers: print a friendly message for unimplemented commands
    print(f"Command '{args.command}' is not implemented yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
