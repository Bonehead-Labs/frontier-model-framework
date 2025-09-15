#!/usr/bin/env python3
"""
Analyse a CSV (ID, Comment) using FMF's high‑level SDK and produce
separate, joinable outputs (CSV/JSONL) with fields {id, analysed}.
Join back to the original CSV in your preferred downstream tool.

Usage:
  python scripts/analyse_csv.py --input path/to/comments.csv -c fmf.yaml \
    --text-col Comment --id-col ID --prompt "Summarise this comment"

Requirements:
  - A valid FMF config (fmf.yaml). A local connector is auto‑selected when possible; override with --connector.
  - Azure OpenAI or Bedrock credentials in the environment, per your config
  - Outputs do not modify the original CSV; they are saved separately and ready to join on 'id'.
"""

from __future__ import annotations

import argparse
import os


def main():
    ap = argparse.ArgumentParser(description="Analyse CSV comments per-row via FMF SDK and save joinable outputs")
    ap.add_argument("--input", required=True, help="Path to input CSV (expects columns ID and Comment by default)")
    ap.add_argument("--connector", default=None, help="Optional connector name; when omitted, SDK auto-selects a connector")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config (default: fmf.yaml)")
    ap.add_argument("--id-col", default="ID", help="ID column name (default: ID)")
    ap.add_argument("--text-col", default="Comment", help="Comment/text column name (default: Comment)")
    ap.add_argument("--prompt", default="Summarise this comment:", help="High-level instruction used in the prompt")
    ap.add_argument("--save-csv", default=None, help="Path to save analysis CSV (default: artefacts/${run_id}/analysis.csv)")
    ap.add_argument("--save-jsonl", default=None, help="Path to save analysis JSONL (default: artefacts/${run_id}/analysis.jsonl)")
    args = ap.parse_args()

    input_csv = os.path.abspath(args.input)
    # Use the new SDK facade for convenience
    from fmf.sdk import FMF

    fmf = FMF.from_env(args.config)
    fmf.csv_analyse(
        input=input_csv,
        text_col=args.text_col,
        id_col=args.id_col,
        prompt=args.prompt,
        save_csv=args.save_csv,
        save_jsonl=args.save_jsonl,
        connector=args.connector,
    )
    print("Run complete. See artefacts for outputs.")


if __name__ == "__main__":
    main()
