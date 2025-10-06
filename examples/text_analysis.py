#!/usr/bin/env python3
"""PDF text analysis using FMF fluent SDK - perfect example with YAML prompts."""

from __future__ import annotations

from fmf.sdk import FMF


def main() -> None:
    """Perfect example of PDF text analysis using FMF fluent SDK with YAML prompts."""
    
    # Initialize FMF with configuration
    fmf = FMF.from_env("fmf.yaml")
    
    # Configure using fluent API with custom system prompt from YAML
    # Note: Paths are relative to the prompt_registry.path configured in fmf.yaml (./prompts)
    fmf = (fmf
           .with_service("azure_openai")
           .with_system_prompt("examples/document_analyst_system.yaml#v1")
           .with_response("jsonl"))
    
    # Run text analysis using YAML prompt file (v2 is simpler, v1 is more detailed)
    result = fmf.text_to_json(
        prompt="examples/extract_code.yaml#v2",
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