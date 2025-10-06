# FMF Examples

This directory contains working examples demonstrating the Frontier Model Framework SDK.

## Prerequisites

1. **Install FMF with required extras**:
   ```bash
   uv sync --extra aws --extra azure
   ```

2. **Configure credentials** in `.env` file:
   ```bash
   # AWS credentials (for Bedrock and S3)
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_SESSION_TOKEN=your_session_token  # if using temporary credentials
   AWS_REGION=ap-southeast-2

   # Azure credentials (for Azure OpenAI)
   AZURE_OPENAI_API_KEY=your_api_key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   ```

3. **Configure `fmf.yaml`** with your connectors and inference settings

## Running Examples

All examples can be run with:

```bash
uv run examples/<example_name>.py
```

## Available Examples

### 1. CSV Analysis with Bedrock (Local Files)

**File**: `analyse_csv_bedrock.py`

Analyzes a CSV file using AWS Bedrock with local file storage.

```bash
uv run examples/analyse_csv_bedrock.py
```

**What it does**:
- Reads `data/sample.csv` from local filesystem
- Uses AWS Bedrock for inference
- Analyzes sentiment and extracts themes from comments
- Saves results to `artefacts/<run_id>/`

**Key features**:
- Fluent API configuration
- Local file connector
- AWS Bedrock inference
- Returns processed records

### 2. CSV Analysis from S3

**File**: `analyse_csv_s3_bedrock.py`

Reads CSV files from an S3 bucket and analyzes them with Bedrock.

```bash
uv run examples/analyse_csv_s3_bedrock.py
```

**What it does**:
- Connects to S3 bucket (configured in `fmf.yaml`)
- Lists and reads CSV files matching pattern `*.csv`
- Analyzes each row with AWS Bedrock
- Automatically loads AWS credentials from `.env`

**Configuration required**:
```yaml
# fmf.yaml
connectors:
  - name: s3_raw
    type: s3
    bucket: "your-bucket-name"
    prefix: "your-prefix"
    region: "ap-southeast-2"
```

**Key features**:
- S3 connector integration
- Automatic credential loading
- Pattern matching for files
- Memory-safe processing (clears content after chunking)

### 3. DataFrame Analysis

**File**: `dataframe_analyse.py`

Analyzes a pandas DataFrame directly without file I/O.

```bash
uv run examples/dataframe_analyse.py
```

**Requirements**:
```bash
uv pip install pandas
```

**What it does**:
- Creates or loads a pandas DataFrame
- Analyzes rows using LLM inference
- No file system interaction required

**Use case**: When you already have data in memory as a DataFrame

### 4. Image Analysis

**File**: `images_analyse.py`

Analyzes images using multimodal LLM capabilities.

```bash
uv run examples/images_analyse.py
```

**What it does**:
- Reads image files from local directory
- Uses multimodal inference (vision models)
- Generates descriptions or analysis

**Supported formats**: PNG, JPG, JPEG

### 5. Text Analysis

**File**: `text_analysis.py`

Processes text files and extracts information.

```bash
uv run examples/text_analysis.py
```

**What it does**:
- Reads text/markdown files
- Chunks text if needed
- Runs inference on each chunk
- Aggregates results

## Common Patterns

### Basic Usage

```python
from fmf.sdk import FMF

# Initialize with config
fmf = FMF.from_env("fmf.yaml")

# Run analysis
result = fmf.csv_analyse(
    input="data/sample.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Analyze this",
    return_records=True
)

print(f"Processed {result.records_processed} records")
```

### Using Fluent API

```python
from fmf.sdk import FMF

# Chain configuration methods
fmf = (FMF.from_env("fmf.yaml")
       .with_service("aws_bedrock")  # Override inference provider
       .with_response("both"))        # Get both CSV and JSONL

result = fmf.csv_analyse(...)
```

### Accessing Results

```python
result = fmf.csv_analyse(...)

# Check success
if result.success:
    print(f"Processed: {result.records_processed}")
    print(f"Output: {result.primary_output_path}")
    
    # Access returned data
    if result.data:
        for record in result.data:
            print(record)
```

## Output Locations

All examples save outputs to:
```
artefacts/<run_id>/
├── analysis.csv      # CSV format results
├── analysis.jsonl    # JSONL format results
└── metadata.json     # Run metadata
```

Where `<run_id>` is a timestamp-based unique identifier (e.g., `20251006T031718Z`).

## Troubleshooting

### AWS Credentials Not Found

**Error**: `boto3 not installed` or `ExpiredToken`

**Solution**:
1. Install AWS extras: `uv sync --extra aws`
2. Check `.env` file has valid AWS credentials
3. Ensure credentials are not expired (especially session tokens)

### S3 Bucket Not Found

**Error**: `No CSV files found in the S3 bucket`

**Solution**:
1. Verify bucket name and prefix in `fmf.yaml`
2. Check AWS credentials have S3 read permissions
3. Confirm files exist in the specified S3 location

### Azure OpenAI Errors

**Error**: `API key not found` or `Endpoint not configured`

**Solution**:
1. Add Azure credentials to `.env`
2. Configure endpoint in `fmf.yaml`:
   ```yaml
   inference:
     provider: azure_openai
     azure_openai:
       endpoint: https://your-resource.openai.azure.com/
       api_version: 2024-02-15-preview
       deployment: gpt-4o-mini
   ```

## Next Steps

- Review `fmf.yaml` for configuration options
- Check `AGENTS.md` for architecture details
- See main `README.md` for full SDK documentation
