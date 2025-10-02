#!/usr/bin/env python3
"""CSV analysis using FMF fluent SDK with AWS Bedrock - perfect example."""

from __future__ import annotations

from fmf.sdk import FMF


def main() -> None:
    """Perfect example of CSV analysis using FMF fluent SDK with AWS Bedrock."""
    
    # Initialize FMF with configuration
    fmf = FMF.from_env("fmf.yaml")
    
    # Configure using fluent API for Bedrock
    fmf = (fmf
           .with_service("aws_bedrock")
           .with_response("both"))
    
    # Run CSV analysis
    result = fmf.csv_analyse(
        input="data/sample.csv",
        text_col="Comment",
        id_col="ID",
        prompt="Analyze sentiment and extract key themes from this comment",
        return_records=True,
        connector="local_docs",  # Explicitly specify the connector
        mode="regular"
    )
    
    # Display results
    print(f"Processed {result.records_processed} records")
    print(f"Output: {result.primary_output_path}")
    
    # Show first result
    if result.data:
        print(f"Sample result: {result.data[0]}")


if __name__ == "__main__":
    main()
