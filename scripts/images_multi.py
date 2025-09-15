#!/usr/bin/env python3
"""
Example: Run a multi-image, multimodal workflow via Recipe YAML.

Usage:
  python scripts/images_multi.py --recipe examples/recipes/images_multi.yaml -c fmf.yaml
"""

from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a multi-image Recipe via FMF SDK")
    ap.add_argument("--recipe", required=True, help="Path to a Recipe YAML (e.g., examples/recipes/images_multi.yaml)")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config (default: fmf.yaml)")
    args = ap.parse_args()

    from fmf.sdk import FMF

    fmf = FMF.from_env(args.config)
    fmf.run_recipe(args.recipe)
    print("Run complete. See artefacts for outputs defined in the recipe.")


if __name__ == "__main__":
    main()

