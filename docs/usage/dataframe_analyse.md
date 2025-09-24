# DataFrame Analysis

Analyze pandas DataFrames directly using FMF's fluent SDK.

## Prerequisites

- FMF installed with DataFrame support: `pip install -e .[dataframe]`
- `fmf.yaml` config file with API keys
- pandas DataFrame with text data

## SDK Usage

```python
import pandas as pd
from fmf.sdk import FMF

# Load data from any source
df = pd.read_csv("data.csv")
# or df = pd.read_parquet("data.parquet")
# or df = pd.read_sql("SELECT * FROM table", connection)

# Initialize and configure
fmf = (FMF.from_env("fmf.yaml")
       .with_service("azure_openai")
       .with_rag(enabled=True, pipeline="documents")
       .with_response("both"))

# Run analysis
result = fmf.dataframe_analyse(
    df=df,
    text_col="comment",
    id_col="id",
    prompt="Analyze sentiment and extract key themes from this comment",
    return_records=True
)

# Display results
print(f"Processed {result.records_processed} records")
print(f"Output: {result.primary_output_path}")
```

## Parameters

- **`df`**: pandas DataFrame to analyze
- **`text_col`**: Column name containing text to analyze
- **`id_col`**: Column name for unique identifiers (optional, uses index if not provided)
- **`prompt`**: Analysis prompt template
- **`expects_json`**: Whether to expect JSON output (default: True)
- **`return_records`**: Whether to return processed records in result
- **`save_csv`**: Path to save CSV output (optional)
- **`save_jsonl`**: Path to save JSONL output (optional)
- **`rag_options`**: RAG configuration options
- **`mode`**: Inference mode (auto, regular, stream)

## Expected Outputs

**CSV Format:**
```csv
id,analysed
1,"{'sentiment': 'positive', 'themes': ['product satisfaction'], 'score': 5}"
2,"{'sentiment': 'neutral', 'themes': ['improvement'], 'score': 3}"
```

**JSONL Format:**
```json
{"id": "1", "analysed": {"sentiment": "positive", "themes": ["product satisfaction"], "score": 5}}
{"id": "2", "analysed": {"sentiment": "neutral", "themes": ["improvement"], "score": 3}}
```

**Rich Results:**
- `result.records_processed` - Number of records analyzed
- `result.primary_output_path` - Path to main output file
- `result.csv_path` - Path to CSV output (if generated)
- `result.jsonl_path` - Path to JSONL output (if generated)
- `result.duration_ms` - Processing time in milliseconds
- `result.success` - Whether the operation succeeded
- `result.data` - List of processed records (if `return_records=True`)

## Data Sources

DataFrame analysis works with data from any source:

```python
# CSV files
df = pd.read_csv("comments.csv")

# Parquet files
df = pd.read_parquet("data.parquet")

# Database queries
df = pd.read_sql("SELECT * FROM comments", connection)

# Excel files
df = pd.read_excel("data.xlsx")

# JSON files
df = pd.read_json("data.json")

# API responses
df = pd.DataFrame(api_response)

# In-memory data
df = pd.DataFrame({
    'id': [1, 2, 3],
    'text': ['comment 1', 'comment 2', 'comment 3']
})
```

## Example Script

See `examples/dataframe_analyse.py` for a complete working example.
