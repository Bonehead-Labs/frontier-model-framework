#!/usr/bin/env python3
"""Text to JSON conversion using FMF fluent SDK - perfect example."""

from __future__ import annotations

from fmf.sdk import FMF


def main() -> None:
    """Perfect example of text to JSON conversion using FMF fluent SDK."""
    
    # Initialize FMF with configuration
    fmf = FMF.from_env("fmf.yaml")
    
    # Configure using fluent API
    fmf = (fmf
           .with_service("azure_openai")
           .with_rag(enabled=True, pipeline="documents")
           .with_response("jsonl")
           .with_source("local", root="./data"))
    
    # Run text to JSON conversion
    result = fmf.text_to_json(
        prompt="Extract key information and convert to structured JSON format",
        select=["data/*.md", "data/*.txt"],
        return_records=True
    )
    
    # Display results
    print(f"Processed {result.records_processed} text chunks")
    print(f"Output: {result.primary_output_path}")
    
    # Show first result
    if result.data:
        print(f"Sample result: {result.data[0]}")


if __name__ == "__main__":
    main()