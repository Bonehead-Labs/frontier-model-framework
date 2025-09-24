#!/usr/bin/env python3
"""Demo script using the fluent SDK API for CSV analysis."""

from __future__ import annotations

import sys
from pathlib import Path

from fmf.sdk import FMF


def main() -> int:
    """Run CSV analysis using the fluent SDK API."""
    
    # Check if we have a config file
    config_path = "fmf.yaml"
    if not Path(config_path).exists():
        print(f"Error: Config file {config_path} not found.")
        print("Please copy examples/fmf.example.yaml to fmf.yaml and configure it.")
        return 1
    
    # Check if we have sample data
    data_path = Path("data/comments.csv")
    if not data_path.exists():
        print(f"Error: Sample data {data_path} not found.")
        print("Please create a CSV file with columns 'ID' and 'Comment' for testing.")
        return 1
    
    try:
        # Demonstrate fluent API usage
        print("=== FMF Fluent API Demo ===")
        print(f"Using config: {config_path}")
        print(f"Processing: {data_path}")
        print()
        
        # Method 1: Simple usage
        print("1. Simple CSV analysis:")
        fmf = FMF.from_env(config_path)
        
        # This will work if the config and data are properly set up
        try:
            records = fmf.csv_analyse(
                input=str(data_path),
                text_col="Comment",
                id_col="ID", 
                prompt="Summarize this comment in one sentence",
                return_records=True
            )
            
            if records:
                print(f"   ✓ Processed {len(records)} records")
                print(f"   ✓ First result: {records[0]}")
            else:
                print("   ⚠ No records returned (check config and data)")
                
        except Exception as e:
            print(f"   ⚠ Analysis failed: {e}")
            print("   This is expected if secrets are not configured")
        
        print()
        
        # Method 2: Fluent API configuration
        print("2. Fluent API configuration:")
        try:
            # Demonstrate fluent chaining (even if it doesn't do much yet)
            configured_fmf = (FMF.from_env(config_path)
                            .with_service("azure_openai")
                            .with_rag(enabled=True, pipeline="documents")
                            .with_response("csv")
                            .with_source("local", root="./data"))
            
            print("   ✓ Fluent configuration completed")
            print("   ✓ Service: azure_openai")
            print("   ✓ RAG: enabled with documents pipeline")
            print("   ✓ Response format: csv")
            print("   ✓ Source: local connector")
            
            # Try to run analysis with configured instance
            try:
                records = configured_fmf.csv_analyse(
                    input=str(data_path),
                    text_col="Comment",
                    id_col="ID",
                    prompt="Analyze sentiment and provide a brief summary",
                    return_records=True
                )
                
                if records:
                    print(f"   ✓ Processed {len(records)} records with fluent config")
                else:
                    print("   ⚠ No records returned with fluent config")
                    
            except Exception as e:
                print(f"   ⚠ Analysis with fluent config failed: {e}")
                
        except Exception as e:
            print(f"   ⚠ Fluent configuration failed: {e}")
        
        print()
        
        # Method 3: Text to JSON conversion
        print("3. Text to JSON conversion:")
        try:
            # Look for text files
            text_files = list(Path("data").glob("*.md")) + list(Path("data").glob("*.txt"))
            
            if text_files:
                text_file = str(text_files[0])
                print(f"   Processing: {text_file}")
                
                records = fmf.text_to_json(
                    prompt="Extract key information and convert to JSON format",
                    select=[text_file],
                    return_records=True
                )
                
                if records:
                    print(f"   ✓ Processed {len(records)} text chunks")
                    print(f"   ✓ First result: {records[0]}")
                else:
                    print("   ⚠ No text records returned")
            else:
                print("   ⚠ No text files found in data/ directory")
                
        except Exception as e:
            print(f"   ⚠ Text processing failed: {e}")
        
        print()
        print("=== Demo Complete ===")
        print()
        print("Next steps:")
        print("1. Configure your API keys in fmf.yaml")
        print("2. Add sample data to data/ directory")
        print("3. Run: python scripts/analyse_csv_sdk.py")
        print()
        print("For more examples, see:")
        print("- README.md (SDK quickstart)")
        print("- examples/ directory")
        print("- docs/USAGE.md")
        
        return 0
        
    except Exception as e:
        print(f"Demo failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
