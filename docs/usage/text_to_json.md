# Text to JSON Conversion

Convert text files to structured JSON using FMF's fluent SDK or CLI.

## Prerequisites

- FMF installed and configured
- `fmf.yaml` config file with API keys
- Text files (markdown, plain text, etc.)

## SDK Usage

```python
from fmf.sdk import FMF

# Initialize and configure
fmf = (FMF.from_env("fmf.yaml")
       .with_service("azure_openai")
       .with_rag(enabled=True, pipeline="documents")
       .with_response("jsonl"))

# Run text to JSON conversion
result = fmf.text_to_json(
    prompt="Extract key information and convert to structured JSON format",
    select=["data/*.md", "data/*.txt"],
    return_records=True
)

# Display results
print(f"Processed {result.records_processed} text chunks")
print(f"Output: {result.primary_output_path}")
```

## CLI Usage

```bash
# Basic text processing (positional arguments)
fmf text data/documents.md "Extract key information"

# Process multiple files, save to JSONL, choose response format
fmf text "data/*.md" "Extract metadata" --output artefacts/text.jsonl --response jsonl

# With RAG enabled
fmf text data/documents.md "Summarize" --rag --rag-pipeline documents
```

## Expected Outputs

**JSONL Format:**
```json
{"source": "data/document1.md", "content": "Document content...", "extracted": {"title": "Document Title", "key_points": ["Point 1", "Point 2"]}}
{"source": "data/document2.txt", "content": "Another document...", "extracted": {"summary": "Brief summary", "topics": ["Topic A", "Topic B"]}}
```

**JSON Format:**
```json
[
  {
    "source": "data/document1.md",
    "content": "Document content...",
    "extracted": {
      "title": "Document Title",
      "key_points": ["Point 1", "Point 2"]
    }
  }
]
```

**Rich Results:**
- `result.records_processed` - Number of text chunks processed
- `result.primary_output_path` - Path to main output file
- `result.jsonl_path` - Path to JSONL output (if generated)
- `result.json_path` - Path to JSON output (if generated)
- `result.duration_ms` - Processing time in milliseconds
- `result.success` - Whether the operation succeeded

## Example Script

See `examples/text_analysis.py` for a complete working example.
