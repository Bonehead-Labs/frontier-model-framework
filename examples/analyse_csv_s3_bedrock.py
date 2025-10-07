#!/usr/bin/env python3
"""CSV analysis from S3 using FMF fluent SDK with AWS Bedrock - reads from S3 and writes back to S3."""

from __future__ import annotations

from fmf.sdk import FMF


def main() -> None:
    """Analyze CSV files from S3 bucket using FMF fluent SDK with AWS Bedrock.
    
    This example demonstrates:
    - Reading CSV files from S3 (gn-sandbox-bucket/fmf-test/)
    - Processing with AWS Bedrock (Claude)
    - Writing results back to S3 (gn-sandbox-bucket/outputs/)
    """
    
    # Initialize FMF with configuration
    # AWS credentials are automatically loaded from .env by the SDK
    fmf = FMF.from_env("fmf.yaml")
    
    # Configure using fluent API for Bedrock
    # Only save CSV output (not JSONL)
    fmf = (fmf
           .with_service("aws_bedrock")
           .with_response("csv"))
    
    # Run CSV analysis from S3
    # Input: Read from s3_raw connector (gn-sandbox-bucket/fmf-test/)
    # Output: Save to local artefacts AND export to S3 (gn-sandbox-bucket/outputs/)
    result = fmf.csv_analyse(
        input="*.csv",  # Pattern to match CSV files in the S3 prefix
        text_col="Comment",
        id_col="ID",
        prompt="Analyze sentiment and extract key themes from this comment",
        return_records=True,
        connector="s3_raw",  # Use the S3 connector from fmf.yaml
        mode="regular",
        export_to="s3_csv_output"
    )
    
    # Display results
    print(f"\n{'='*70}")
    print(f"CSV Analysis Complete")
    print(f"{'='*70}")
    print(f"Processed: {result.records_processed} records from S3")
    print(f"Local output: {result.primary_output_path}")
    print(f"S3 export: s3://gn-sandbox-bucket/outputs/ (via s3_csv_output sink)")
    print(f"Run ID: {result.run_id}")
    
    # Show first result
    if result.data:
        print(f"\n{'='*70}")
        print(f"Sample Result")
        print(f"{'='*70}")
        print(f"  ID: {result.data[0].get('ID', 'N/A')}")
        print(f"  Comment: {result.data[0].get('Comment', 'N/A')[:100]}...")
        print(f"  Analysis: {result.data[0].get('analysed', 'N/A')[:200]}...")
        print(f"{'='*70}")


if __name__ == "__main__":
    main()
