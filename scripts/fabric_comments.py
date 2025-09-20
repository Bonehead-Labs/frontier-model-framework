#!/usr/bin/env python3
"""Run the Fabric comments recipe (thin orchestrator)."""

from __future__ import annotations

import argparse
import json
import sys

from fmf.sdk import run_recipe_simple

DEFAULT_RECIPE = "examples/recipes/fabric_comments.yaml"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Fabric comments analysis via FMF")
    ap.add_argument("-r", "--recipe", default=DEFAULT_RECIPE, help="Path to recipe YAML")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary")
    ap.add_argument("--enable-rag", action="store_true", help="Enable recipe-provided RAG")
    ap.add_argument("--rag-pipeline", help="Override RAG pipeline name")
    ap.add_argument("--rag-top-k-text", type=int, help="Override RAG text top-k")
    ap.add_argument("--rag-top-k-images", type=int, help="Override RAG image top-k")
    args = ap.parse_args()

    summary = run_recipe_simple(
        args.config,
        args.recipe,
        use_recipe_rag=args.enable_rag,
        rag_pipeline=args.rag_pipeline,
        rag_top_k_text=args.rag_top_k_text,
        rag_top_k_images=args.rag_top_k_images,
    )

    if args.json:
        print(json.dumps(summary.__dict__, separators=(",", ":")))
    else:
        status = "OK" if summary.ok else "ERROR"
        run_id = summary.run_id or ""
        print(f"{status} {run_id}")
    return 0 if summary.ok else 1


if __name__ == "__main__":
    sys.exit(main())
