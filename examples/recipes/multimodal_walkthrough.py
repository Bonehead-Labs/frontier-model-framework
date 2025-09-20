"""Demonstrates a multimodal chain invocation with optional retrieval."""

from __future__ import annotations

import argparse
from pathlib import Path

from fmf.sdk import FMF


def build_recipe(image_select: list[str] | None = None) -> dict[str, object]:
    return {
        "connector": "local_docs",
        "select": image_select or ["**/*.{png,jpg,jpeg}"],
        "prompt": "Describe the visual content in two concise bullets.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Multimodal analysis walkthrough")
    parser.add_argument("--select", action="append", default=None, help="Glob selector for images")
    parser.add_argument("--config", default="fmf.yaml")
    parser.add_argument("--execute", action="store_true", help="Execute SDK call instead of dry-run")
    args = parser.parse_args()

    recipe = build_recipe(args.select)
    if not args.execute:
        print("[dry-run] Multimodal plan:")
        for key, value in recipe.items():
            print(f"  {key}: {value}")
        print("Pass --execute to run images.analyse via the SDK.")
        return

    fmf = FMF.from_env(args.config)
    artefact_dir = Path("artefacts")
    artefact_dir.mkdir(parents=True, exist_ok=True)
    fmf.images_analyse(
        select=args.select,
        prompt=recipe["prompt"],
        save_jsonl=str(artefact_dir / "multimodal_walkthrough.jsonl"),
    )


if __name__ == "__main__":
    main()
