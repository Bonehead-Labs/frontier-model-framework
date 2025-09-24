#!/usr/bin/env python3
"""FMF SDK demonstration - perfect examples of fluent API usage."""

from __future__ import annotations

from fmf.sdk import FMF


def csv_analysis_example() -> None:
    """Example: CSV analysis with fluent API."""
    print("=== CSV Analysis Example ===")
    
    fmf = (FMF.from_env("fmf.yaml")
           .with_service("azure_openai")
           .with_rag(enabled=True, pipeline="documents")
           .with_response("both"))
    
    result = fmf.csv_analyse(
        input="data/comments.csv",
        text_col="Comment",
        id_col="ID",
        prompt="Analyze sentiment and extract key themes",
        return_records=True
    )
    
    print(f"Processed {result.records_processed} records")
    print(f"Output: {result.primary_output_path}")


def text_processing_example() -> None:
    """Example: Text to JSON conversion."""
    print("\n=== Text Processing Example ===")
    
    fmf = (FMF.from_env("fmf.yaml")
           .with_service("azure_openai")
           .with_response("jsonl"))
    
    result = fmf.text_to_json(
        prompt="Extract structured information from this text",
        select=["data/*.md"],
        return_records=True
    )
    
    print(f"Processed {result.records_processed} text chunks")
    print(f"Output: {result.primary_output_path}")


def images_analysis_example() -> None:
    """Example: Images analysis."""
    print("\n=== Images Analysis Example ===")
    
    fmf = (FMF.from_env("fmf.yaml")
           .with_service("azure_openai")
           .with_rag(enabled=True, pipeline="images")
           .with_response("jsonl"))
    
    result = fmf.images_analyse(
        prompt="Describe the visual content and extract key elements",
        select=["data/*.png", "data/*.jpg"],
        return_records=True
    )
    
    print(f"Processed {result.records_processed} images")
    print(f"Output: {result.primary_output_path}")


def context_manager_example() -> None:
    """Example: Using FMF as context manager."""
    print("\n=== Context Manager Example ===")
    
    with FMF.from_env("fmf.yaml").with_service("azure_openai") as fmf:
        result = fmf.csv_analyse(
            input="data/comments.csv",
            text_col="Comment",
            id_col="ID",
            prompt="Quick analysis",
            return_records=True
        )
        print(f"Context manager processed {result.records_processed} records")


def defaults_example() -> None:
    """Example: Using defaults for common configuration."""
    print("\n=== Defaults Example ===")
    
    fmf = (FMF.from_env("fmf.yaml")
           .defaults(
               service="azure_openai",
               rag_enabled=True,
               response_format="jsonl"
           ))
    
    result = fmf.text_to_json(
        prompt="Extract key information",
        select=["data/*.txt"],
        return_records=True
    )
    
    print(f"Defaults example processed {result.records_processed} text chunks")


def main() -> None:
    """Run all SDK examples."""
    print("FMF SDK Examples")
    print("================")
    
    try:
        csv_analysis_example()
        text_processing_example()
        images_analysis_example()
        context_manager_example()
        defaults_example()
        
        print("\nAll examples completed successfully!")
        
    except Exception as e:
        print(f"Example failed: {e}")
        print("Make sure you have:")
        print("1. fmf.yaml configured with API keys")
        print("2. Sample data in data/ directory")
        print("3. Required dependencies installed")


if __name__ == "__main__":
    main()
