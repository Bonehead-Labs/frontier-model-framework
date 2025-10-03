#!/usr/bin/env python3
"""PDF text analysis using FMF fluent SDK - perfect example."""

from __future__ import annotations

from fmf.sdk import FMF


def main() -> None:
    """Perfect example of PDF text analysis using FMF fluent SDK."""
    
    # Initialize FMF with configuration
    fmf = FMF.from_env("fmf.yaml")
    
    # Configure using fluent API
    fmf = (fmf
           .with_service("azure_openai")
           .with_response("jsonl"))
    
    # Run text analysis
    result = fmf.text_to_json(
        prompt="Read this document and find the hidden code, it is a number and should stand out from the rest. Return the output in a simple JSON format with the code as the value of the 'code' key.",
        connector="local_docs",
        select=["*.pdf"],
        return_records=True
    )
    
    # Display results
    if not result.success:
        print(f"ERROR: {result.error}")
        if result.error_details:
            print(f"Details: {result.error_details}")
        return
    
    print(f"Processed {result.records_processed} text chunks")
    print(f"Output: {result.primary_output_path}")
    print(f"Run ID: {result.run_id}")
    
    # Show first result
    if result.data:
        print(f"Sample result: {result.data[0]}")


if __name__ == "__main__":
    main()