"""Quickstart recipe that demonstrates CSV analysis via the SDK facade.

Run with:
    python examples/recipes/csv_quickstart.py --input data/comments.csv --prompt "Summarise"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fmf.sdk import FMF


def build_recipe(input_path: str, prompt: str, *, text_col: str = "Comment", id_col: str = "ID") -> dict[str, object]:
    """Return a declarative description of the intended run."""

    return {
        "input": input_path,
        "prompt": prompt,
        "text_col": text_col,
        "id_col": id_col,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CSV quickstart using the FMF SDK")
    parser.add_argument("--input", required=True, help="CSV file to analyse")
    parser.add_argument("--prompt", required=True, help="Prompt text for summarisation")
    parser.add_argument("--config", default="fmf.yaml", help="Config file to load")
    parser.add_argument("--text-col", default="Comment")
    parser.add_argument("--id-col", default="ID")
    parser.add_argument("--execute", action="store_true", help="Execute the run instead of printing plan")
    args = parser.parse_args()

    recipe = build_recipe(args.input, args.prompt, text_col=args.text_col, id_col=args.id_col)

    if not args.execute:
        print("[dry-run] Recipe plan:")
        for key, value in recipe.items():
            print(f"  {key}: {value}")
        print("Pass --execute to run csv_analyse() against the live connector.")
        return

    fmf = FMF.from_env(args.config)
    artefact_dir = Path("artefacts")
    artefact_dir.mkdir(parents=True, exist_ok=True)
    fmf.csv_analyse(
        input=args.input,
        text_col=args.text_col,
        id_col=args.id_col,
        prompt=args.prompt,
        save_csv=str(artefact_dir / "csv_quickstart.csv"),
        return_records=False,
    )


if __name__ == "__main__":
    main()
