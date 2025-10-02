#!/usr/bin/env python3
"""Images analysis using FMF fluent SDK - perfect example."""

from __future__ import annotations

from fmf.sdk import FMF


def main() -> None:
    """Perfect example of images analysis using FMF fluent SDK."""

    # Initialize FMF with configuration
    fmf = FMF.from_env("fmf.yaml")

    # Configure using fluent API
    fmf = (fmf
           .with_service("aws_bedrock")
           .with_response("jsonl")
           .with_source("local", name="local_tmp_images", root="./data", include=["*.{png,jpg,jpeg}"]))

    # Run images analysis
    result = fmf.images_analyse(
        prompt="Describe this image in 15 words or less.",
        select=["*.png", "*.jpg", "*.jpeg"],
        group_size=1,
        return_records=True
    )
    
    # Display results
    print(f"Processed {result.records_processed} images")
    print(f"Output: {result.primary_output_path}")

    # Show first result
    if result.data:
        print(f"Sample result: {result.data[0]}")


if __name__ == "__main__":
    main()
