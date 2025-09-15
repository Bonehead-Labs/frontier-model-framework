#!/usr/bin/env python3
"""
Analyse a CSV using a Recipe YAML (first‑class, recommended path).

This script simply runs a recipe file via the FMF SDK. See
examples/recipes/csv_analyse.yaml for a ready‑to‑use template.

Usage:
  python scripts/analyse_csv.py --recipe examples/recipes/csv_analyse.yaml -c fmf.yaml

Notes:
  - The recipe defines input, columns, prompt, and save paths.
  - Outputs are separate (CSV/JSONL) and ready to join back to your original CSV.
"""

from __future__ import annotations

import argparse


def main():
    ap = argparse.ArgumentParser(description="Run a CSV analysis Recipe YAML via FMF SDK")
    ap.add_argument("--recipe", required=True, help="Path to a Recipe YAML (e.g., examples/recipes/csv_analyse.yaml)")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config (default: fmf.yaml)")
    args = ap.parse_args()

    # Use the SDK facade to run the recipe
    from fmf.sdk import FMF

    fmf = FMF.from_env(args.config)
    fmf.run_recipe(args.recipe)
    print("Run complete. See artefacts for outputs defined in the recipe.")


if __name__ == "__main__":
    main()
