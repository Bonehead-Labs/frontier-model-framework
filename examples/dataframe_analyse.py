#!/usr/bin/env python3
"""DataFrame analysis using FMF fluent SDK - perfect example."""

from __future__ import annotations

import pandas as pd
from fmf.sdk import FMF


def main() -> None:
    """Perfect example of DataFrame analysis using FMF fluent SDK."""
    
    # Create sample DataFrame (or load from any source)
    df = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'comment': [
            "This product is amazing! I love it.",
            "Not bad, but could be better.",
            "Terrible quality, waste of money.",
            "Great value for the price.",
            "Average product, nothing special."
        ],
        'rating': [5, 3, 1, 4, 2],
        'category': ['positive', 'neutral', 'negative', 'positive', 'neutral']
    })
    
    print(f"Loaded DataFrame with {len(df)} rows")
    print("Sample data:")
    print(df.head())
    print()
    
    # Initialize FMF with configuration
    fmf = FMF.from_env("fmf.yaml")

    # Configure using fluent API
    fmf = (fmf
           .with_service("azure_openai")
           .with_response("both"))
    
    # Run DataFrame analysis
    result = fmf.dataframe_analyse(
        df=df,
        text_col="comment",
        id_col="id",
        prompt="Analyze the sentiment and extract key themes from this comment. Also identify the overall sentiment score (1-5).",
        return_records=True
    )
    
    # Display results
    print(f"Processed {result.records_processed} records")
    print(f"Output: {result.primary_output_path}")
    
    # Show first result
    if result.data:
        print("\nSample analysis results:")
        for i, record in enumerate(result.data[:3]):  # Show first 3
            print(f"Record {i+1}: {record}")
    
    # Show summary
    print(f"\nAnalysis completed in {result.duration_ms:.1f}ms")
    print(f"Service used: {result.service_used}")
    print(f"RAG enabled: {result.rag_enabled}")


if __name__ == "__main__":
    main()
