#!/usr/bin/env python3
"""Fabric comments analysis using FMF fluent SDK - perfect example."""

from __future__ import annotations

from fmf.sdk import FMF


def main() -> None:
    """Perfect example of Fabric comments analysis using FMF fluent SDK."""
    
    # Initialize FMF with configuration
    fmf = FMF.from_env("fmf.yaml")
    
    # Configure using fluent API with RAG
    fmf = (fmf
           .with_service("azure_openai")
           .with_rag(enabled=True, pipeline="fabric_comments")
           .with_response("both")
           .with_source("local", root="./data"))
    
    # Run Fabric comments analysis
    result = fmf.csv_analyse(
        input="data/fabric_comments.csv",
        text_col="Comment",
        id_col="ID",
        prompt="Analyze this Fabric comment for sentiment, key themes, and actionable insights",
        return_records=True
    )
    
    # Display results
    print(f"Processed {result.records_processed} Fabric comments")
    print(f"Output: {result.primary_output_path}")
    
    # Show first result
    if result.data:
        print(f"Sample result: {result.data[0]}")


if __name__ == "__main__":
    main()