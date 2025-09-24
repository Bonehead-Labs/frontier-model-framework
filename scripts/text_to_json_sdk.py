#!/usr/bin/env python3
"""Text to JSON conversion using FMF fluent API."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

from fmf.sdk import FMF


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert text files to JSON using FMF fluent API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic text to JSON conversion
  python scripts/text_to_json_sdk.py --input data/documents.md --prompt "Extract key information"

  # With RAG enabled
  python scripts/text_to_json_sdk.py --input data/documents.md --prompt "Summarize" --enable-rag

  # Process multiple files
  python scripts/text_to_json_sdk.py --input "data/*.md" --prompt "Extract metadata" --output-format jsonl
        """
    )
    
    # Required arguments
    ap.add_argument("--input", required=True, help="Path to input text file(s) or glob pattern")
    ap.add_argument("--prompt", required=True, help="Processing prompt")
    
    # Optional arguments
    ap.add_argument("-c", "--config", default="fmf.yaml", help="Path to FMF config file")
    ap.add_argument("--output", help="Path for output file (default: artefacts/${run_id}/text_outputs.jsonl)")
    ap.add_argument("--output-format", choices=["jsonl", "json"], default="jsonl", help="Output format")
    ap.add_argument("--connector", help="Data connector name (default: auto-detect)")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary")
    
    # RAG options
    ap.add_argument("--enable-rag", action="store_true", help="Enable RAG (Retrieval-Augmented Generation)")
    ap.add_argument("--rag-pipeline", help="RAG pipeline name")
    ap.add_argument("--rag-top-k-text", type=int, default=2, help="Number of text chunks to retrieve")
    ap.add_argument("--rag-top-k-images", type=int, default=2, help="Number of image chunks to retrieve")
    
    # Inference options
    ap.add_argument("--mode", choices=["auto", "regular", "stream"], help="Inference mode")
    ap.add_argument("--service", choices=["azure_openai", "aws_bedrock"], help="Inference service provider")
    ap.add_argument("--expects-json", action="store_true", default=True, help="Expect JSON output from LLM")
    ap.add_argument("--no-expects-json", dest="expects_json", action="store_false", help="Don't expect JSON output from LLM")
    
    args = ap.parse_args()
    
    # Validate input file(s) exist
    input_path = Path(args.input)
    if not input_path.exists() and "*" not in args.input:
        print(f"Error: Input file '{args.input}' not found.")
        return 1
    
    try:
        # Build FMF instance with fluent API
        fmf = FMF.from_env(args.config)
        
        # Apply service configuration
        if args.service:
            fmf = fmf.with_service(args.service)
        
        # Apply RAG configuration
        if args.enable_rag:
            rag_pipeline = args.rag_pipeline or "default_rag"
            fmf = fmf.with_rag(enabled=True, pipeline=rag_pipeline)
        
        # Apply response format configuration
        fmf = fmf.with_response(args.output_format)
        
        # Apply connector configuration
        if args.connector:
            fmf = fmf.with_source(args.connector)
        
        # Prepare RAG options
        rag_options = None
        if args.enable_rag:
            rag_options = {
                "pipeline": args.rag_pipeline or "default_rag",
                "top_k_text": args.rag_top_k_text,
                "top_k_images": args.rag_top_k_images,
            }
        
        # Determine select pattern
        if "*" in args.input:
            select_pattern = [args.input]
        else:
            select_pattern = [str(input_path)]
        
        # Run text to JSON conversion
        records = fmf.text_to_json(
            prompt=args.prompt,
            connector=args.connector,
            select=select_pattern,
            save_jsonl=args.output,
            expects_json=args.expects_json,
            rag_options=rag_options,
            mode=args.mode,
            return_records=True
        )
        
        # Output results
        if args.json:
            result = {
                "status": "success",
                "records_processed": len(records) if records else 0,
                "input_pattern": args.input,
                "prompt": args.prompt,
                "rag_enabled": args.enable_rag,
                "output_format": args.output_format,
            }
            print(json.dumps(result, separators=(",", ":")))
        else:
            if records:
                print(f"✓ Processed {len(records)} text chunks from {args.input}")
                if args.output:
                    print(f"  Output: {args.output}")
            else:
                print("⚠ No text chunks processed")
        
        return 0
        
    except Exception as e:
        if args.json:
            error_result = {
                "status": "error",
                "error": str(e),
                "input_pattern": args.input,
            }
            print(json.dumps(error_result, separators=(",", ":")))
        else:
            print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
