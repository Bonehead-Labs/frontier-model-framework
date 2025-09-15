#!/usr/bin/env python3
"""
Analyse a CSV (ID, Comment) using FMF row‑mode and produce a separate, joinable
output file (CSV/JSONL) with fields {id, analysed}. The join back to the
original CSV can be handled by your preferred downstream tool.

Usage:
  python scripts/analyse_csv.py --input path/to/comments.csv --connector local_docs -c fmf.yaml \
    --save-csv artefacts/analysis.csv

Requirements:
  - A valid FMF config with a connector pointing to the directory of your CSV (pass its name via --connector)
  - Azure OpenAI or Bedrock credentials in the environment, per your config

Notes:
  - This script builds a minimal chain in a temporary file and runs it.
  - It does not modify the original CSV; outputs are separate files ready to join on 'id'.
"""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from typing import Dict, Any

import yaml


def run(
    *,
    input_csv: str,
    base_config: str,
    connector: str,
    id_col: str,
    text_col: str,
    prompt: str,
    save_csv: str | None,
    save_jsonl: str | None,
) -> None:
    """Build a minimal chain to analyse CSV rows and save separate outputs."""
    filename = os.path.basename(input_csv)

    # Default save paths (include ${run_id} for reproducibility)
    if not save_csv:
        save_csv = f"artefacts/${{run_id}}/analysis.csv"
    if not save_jsonl:
        save_jsonl = f"artefacts/${{run_id}}/analysis.jsonl"

    chain: Dict[str, Any] = {
        "name": "csv-comment-analysis",
        "inputs": {
            "connector": connector,
            "select": [filename],
            "mode": "table_rows",
            "table": {"text_column": text_col, "pass_through": [id_col]},
        },
        "steps": [
            {
                "id": "analyse",
                "prompt": (
                    "inline: Return a JSON object with fields 'id' and 'analysed'.\n"
                    "Only output valid JSON, nothing else.\n\n"
                    "ID: {{ id }}\n"
                    "Comment:\n{{ text }}\n"
                ),
                "inputs": {"id": f"${{row.{id_col}}}", "text": "${row.text}"},
                "output": {
                    "name": "analysed",
                    "expects": "json",
                    "parse_retries": 1,
                    "schema": {"type": "object", "required": ["id", "analysed"]},
                },
            }
        ],
        "outputs": [
            {"save": save_jsonl, "from": "analysed", "as": "jsonl"},
            {"save": save_csv, "from": "analysed", "as": "csv"},
        ],
        "concurrency": 4,
        "continue_on_error": True,
    }

    # Write temp chain YAML and run
    tdir = tempfile.TemporaryDirectory()
    chain_path = os.path.join(tdir.name, "chain.yaml")
    with open(chain_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(chain, f, sort_keys=False)

    from fmf.chain.runner import run_chain

    res = run_chain(chain_path, fmf_config_path=base_config)
    run_dir = res.get("run_dir")
    print("Run complete.")
    print(f"run_id={res.get('run_id')}")
    print(f"outputs_dir={run_dir}")
    print(f"saved_csv={save_csv}")
    print(f"saved_jsonl={save_jsonl}")


def main():
    ap = argparse.ArgumentParser(description="Analyse CSV comments per-row via FMF and save joinable outputs")
    ap.add_argument("--input", required=True, help="Path to input CSV (expects columns ID and Comment by default)")
    ap.add_argument("--connector", default="local_docs", help="Connector name configured in fmf.yaml that can see the CSV (default: local_docs)")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config (default: fmf.yaml)")
    ap.add_argument("--id-col", default="ID", help="ID column name (default: ID)")
    ap.add_argument("--text-col", default="Comment", help="Comment/text column name (default: Comment)")
    ap.add_argument("--prompt", default="Summarise this comment:", help="High-level instruction used in the prompt")
    ap.add_argument("--save-csv", default=None, help="Path to save analysis CSV (default: artefacts/${run_id}/analysis.csv)")
    ap.add_argument("--save-jsonl", default=None, help="Path to save analysis JSONL (default: artefacts/${run_id}/analysis.jsonl)")
    args = ap.parse_args()

    input_csv = os.path.abspath(args.input)
    run(
        input_csv=input_csv,
        base_config=args.config,
        connector=args.connector,
        id_col=args.id_col,
        text_col=args.text_col,
        prompt=args.prompt,
        save_csv=args.save_csv,
        save_jsonl=args.save_jsonl,
    )


if __name__ == "__main__":
    main()
