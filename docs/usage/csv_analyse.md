# CSV Analysis

Analyze CSV files using FMF's fluent SDK or CLI.

## Prerequisites

- FMF installed and configured
- `fmf.yaml` config file with API keys
- CSV file with text and ID columns

## SDK Usage

```python
from fmf.sdk import FMF

# Initialize and configure
fmf = (FMF.from_env("fmf.yaml")
       .with_service("azure_openai")
       .with_rag(enabled=True, pipeline="documents")
       .with_response("both"))

# Run analysis
result = fmf.csv_analyse(
    input="data/comments.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Analyze sentiment and extract key themes from this comment",
    return_records=True
)

# Display results
print(f"Processed {result.records_processed} records")
print(f"Output: {result.primary_output_path}")
```

## CLI Usage

```bash
# Basic analysis (positional arguments)
fmf csv data/comments.csv Comment ID "Analyze sentiment"

# With RAG enabled (optional flags)
fmf csv data/comments.csv Comment ID "Analyze" --rag --rag-pipeline documents

# Specify provider and response format
fmf csv data/comments.csv Comment ID "Analyze" --service azure_openai --response both

# Save outputs to specific paths
fmf csv data/comments.csv Comment ID "Analyze" --output-csv artefacts/out.csv --output-jsonl artefacts/out.jsonl
```

## Expected Outputs

**CSV Format:**
```csv
ID,Comment,Analysis
1,"Great product!",Positive sentiment with product satisfaction theme
2,"Needs improvement",Negative sentiment with improvement request theme
```

**JSONL Format:**
```json
{"id": "1", "comment": "Great product!", "analysis": "Positive sentiment with product satisfaction theme"}
{"id": "2", "comment": "Needs improvement", "analysis": "Negative sentiment with improvement request theme"}
```

**Rich Results:**
- `result.records_processed` - Number of records analyzed
- `result.primary_output_path` - Path to main output file
- `result.csv_path` - Path to CSV output (if generated)
- `result.jsonl_path` - Path to JSONL output (if generated)
- `result.duration_ms` - Processing time in milliseconds
- `result.success` - Whether the operation succeeded

## Example Script

See `examples/analyse_csv.py` for a complete working example.
