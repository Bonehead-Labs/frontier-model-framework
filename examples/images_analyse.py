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
           .with_service("azure_openai")
           .with_rag(enabled=True, pipeline="images")
           .with_response("jsonl")
           .with_source("local", root="./data"))
    
    # Run images analysis
    result = fmf.images_analyse(
        prompt="Describe the content and extract key visual elements from this image",
        select=["data/*.png", "data/*.jpg", "data/*.jpeg"],
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
