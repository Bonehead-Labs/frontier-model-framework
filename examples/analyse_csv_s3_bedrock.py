#!/usr/bin/env python3
"""CSV analysis from S3 using FMF fluent SDK with AWS Bedrock."""

from __future__ import annotations

from fmf.sdk import FMF


def main() -> None:
    """Analyze CSV files from S3 bucket using FMF fluent SDK with AWS Bedrock."""
    
    # Initialize FMF with configuration
    # AWS credentials are automatically loaded from .env by the SDK
    fmf = FMF.from_env("fmf.yaml")
    
    # Configure using fluent API for Bedrock
    fmf = (fmf
           .with_service("aws_bedrock")
           .with_response("both"))
    
    # Run CSV analysis from S3
    # This will read CSV files from the s3_raw connector configured in fmf.yaml
    # bucket: gn-sandbox-bucket, prefix: fmf-test, region: ap-southeast-2
    result = fmf.csv_analyse(
        input="*.csv",  # Pattern to match CSV files in the S3 prefix
        text_col="Comment",
        id_col="ID",
        prompt="Analyze sentiment and extract key themes from this comment",
        return_records=True,
        connector="s3_raw",  # Use the S3 connector from fmf.yaml
        mode="regular"
    )
    
    # Display results
    print(f"\nProcessed {result.records_processed} records from S3")
    print(f"Output: {result.primary_output_path}")
    
    # Show first result
    if result.data:
        print(f"\nSample result:")
        print(f"  ID: {result.data[0].get('ID', 'N/A')}")
        print(f"  Comment: {result.data[0].get('Comment', 'N/A')[:100]}...")
        print(f"  Analysis: {result.data[0].get('analysed', 'N/A')[:200]}...")


if __name__ == "__main__":
    main()
