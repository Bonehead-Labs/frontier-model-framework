#!/usr/bin/env python3
"""
Example: Run a multi-image, multimodal workflow via Recipe YAML.

Usage:
  python scripts/images_multi.py --recipe examples/recipes/images_multi.yaml -c fmf.yaml \
    --enable-rag
"""

from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a multi-image Recipe via FMF SDK")
    ap.add_argument("--recipe", required=True, help="Path to a Recipe YAML (e.g., examples/recipes/images_multi.yaml)")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config (default: fmf.yaml)")
    ap.add_argument("--enable-rag", action="store_true", help="Use the recipe's optional RAG block if present")
    ap.add_argument("--rag-pipeline", help="Optional RAG pipeline name configured in fmf.yaml")
    ap.add_argument(
        "--rag-top-k-text",
        type=int,
        help="Override text passages to retrieve when RAG is enabled",
    )
    ap.add_argument(
        "--rag-top-k-images",
        type=int,
        help="Override image matches to retrieve when RAG is enabled",
    )
    args = ap.parse_args()

    from fmf.sdk import FMF

    fmf = FMF.from_env(args.config)
    rag_kwargs = {"use_recipe_rag": args.enable_rag}
    if args.rag_pipeline:
        rag_kwargs["rag_pipeline"] = args.rag_pipeline
    if args.rag_top_k_text is not None:
        rag_kwargs["rag_top_k_text"] = args.rag_top_k_text
    if args.rag_top_k_images is not None:
        rag_kwargs["rag_top_k_images"] = args.rag_top_k_images

    fmf.run_recipe(args.recipe, **rag_kwargs)
    print("Run complete. See artefacts for outputs defined in the recipe.")


if __name__ == "__main__":
    main()
