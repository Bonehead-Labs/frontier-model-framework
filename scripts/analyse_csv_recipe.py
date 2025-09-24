#!/usr/bin/env python3
"""Legacy CSV analysis recipe wrapper (deprecated - use analyse_csv.py instead)."""

from __future__ import annotations

import argparse
import json
import sys
import warnings

from fmf.sdk import run_recipe_simple


def main() -> int:
    # Emit deprecation warning
    warnings.warn(
        "analyse_csv_recipe.py is deprecated. Use 'python scripts/analyse_csv.py' with fluent API arguments instead. "
        "Recipes are recommended for CI/Ops only.",
        DeprecationWarning,
        stacklevel=2
    )
    
    ap = argparse.ArgumentParser(
        description="[DEPRECATED] Run a CSV analysis recipe via FMF - use analyse_csv.py instead",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DEPRECATION NOTICE:
  This script is deprecated. Use the fluent API instead:
  
  # Old way (deprecated):
  python scripts/analyse_csv_recipe.py -r recipe.yaml -c config.yaml
  
  # New way (recommended):
  python scripts/analyse_csv.py --input data.csv --text-col Comment --id-col ID --prompt "Analyze"
  
  Recipes are now recommended for CI/Ops only.
        """
    )
    ap.add_argument("-r", "--recipe", required=True, help="Path to recipe YAML")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary")
    ap.add_argument("--enable-rag", action="store_true", help="Enable recipe-provided RAG")
    ap.add_argument("--rag-pipeline", help="Override RAG pipeline name")
    ap.add_argument("--rag-top-k-text", type=int, help="Override RAG text top-k")
    ap.add_argument("--rag-top-k-images", type=int, help="Override RAG image top-k")
    ap.add_argument("--mode", choices=["auto", "regular", "stream"], help="Inference mode override")
    args = ap.parse_args()

    summary = run_recipe_simple(
        args.config,
        args.recipe,
        use_recipe_rag=args.enable_rag,
        rag_pipeline=args.rag_pipeline,
        rag_top_k_text=args.rag_top_k_text,
        rag_top_k_images=args.rag_top_k_images,
        mode=args.mode,
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
