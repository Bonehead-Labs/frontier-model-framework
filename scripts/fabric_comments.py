#!/usr/bin/env python3
"""Fabric comments analysis using FMF fluent API."""

from __future__ import annotations

import argparse
import json
import sys

from fmf.sdk import FMF


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Fabric comments analysis via FMF")
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary")
    ap.add_argument("--enable-rag", action="store_true", help="Enable RAG")
    ap.add_argument("--rag-pipeline", help="RAG pipeline name")
    ap.add_argument("--rag-top-k-text", type=int, help="RAG text top-k")
    ap.add_argument("--rag-top-k-images", type=int, help="RAG image top-k")
    ap.add_argument("--mode", choices=["auto", "regular", "stream"], help="Inference mode")
    args = ap.parse_args()

    # Build FMF instance with configuration
    fmf = FMF.from_env(args.config)
    
    # Apply RAG configuration if enabled
    if args.enable_rag:
        rag_options = {}
        if args.rag_pipeline:
            rag_options["pipeline"] = args.rag_pipeline
        if args.rag_top_k_text:
            rag_options["top_k_text"] = args.rag_top_k_text
        if args.rag_top_k_images:
            rag_options["top_k_images"] = args.rag_top_k_images
        
        fmf = fmf.with_rag(enabled=True, pipeline=rag_options.get("pipeline", "default_rag"))
    else:
        rag_options = None

    # Run CSV analysis (assuming Fabric comments are in CSV format)
    result = fmf.csv_analyse(
        input="fabric_comments.csv",  # This would need to be configured based on actual data source
        text_col="Comment",
        id_col="ID", 
        prompt="Analyze this Fabric comment for sentiment and key themes",
        rag_options=rag_options,
        mode=args.mode,
        return_records=False
    )

    if args.json:
        print(json.dumps(result.to_dict(), separators=(",", ":")))
    else:
        status = "OK" if result.success else "ERROR"
        run_id = result.run_id or ""
        print(f"{status} {run_id}")
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
