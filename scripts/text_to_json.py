#!/usr/bin/env python3
"""
Example: Analyse text files (md, txt, html) and emit JSON outputs using a Recipe YAML.

Usage:
  python scripts/text_to_json.py --recipe examples/recipes/text_to_json.yaml -c fmf.yaml
"""

from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a text-to-JSON Recipe via FMF SDK")
    ap.add_argument("--recipe", required=True, help="Path to a Recipe YAML (e.g., examples/recipes/text_to_json.yaml)")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config (default: fmf.yaml)")
    args = ap.parse_args()

    from fmf.sdk import FMF

    fmf = FMF.from_env(args.config)
    fmf.run_recipe(args.recipe)
    print("Run complete. See artefacts for outputs defined in the recipe.")


if __name__ == "__main__":
    main()

