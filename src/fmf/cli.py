from __future__ import annotations

import argparse
import sys


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

    # Define top-level subcommands (stubs for now)
    subparsers.add_parser("keys", help="Manage/test secret resolution")
    subparsers.add_parser("connect", help="List and interact with data connectors")
    subparsers.add_parser("process", help="Process and chunk input data to artefacts")
    subparsers.add_parser("prompt", help="Prompt registry operations")
    subparsers.add_parser("run", help="Execute a chain from YAML")
    subparsers.add_parser("infer", help="Single-shot inference using a prompt version")
    subparsers.add_parser("export", help="Export artefacts/results to configured sinks")

    return parser


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

    # Stub handlers: print a friendly message for unimplemented commands
    print(f"Command '{args.command}' is not implemented yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

