# Frontier Model Framework (FMF)
```                                                                    
FFFFFFFFFFFFFFFFFFFFFF   MMMMMMMM               MMMMMMMM   FFFFFFFFFFFFFFFFFFFFFF
F::::::::::::::::::::F   M:::::::M             M:::::::M   F::::::::::::::::::::F
F::::::::::::::::::::F   M::::::::M           M::::::::M   F::::::::::::::::::::F
FF::::::FFFFFFFFF::::F   M:::::::::M         M:::::::::M   FF::::::FFFFFFFFF::::F
  F:::::F       FFFFFF   M::::::::::M       M::::::::::M     F:::::F       FFFFFF
  F:::::F                M:::::::::::M     M:::::::::::M     F:::::F             
  F::::::FFFFFFFFFF      M:::::::M::::M   M::::M:::::::M     F::::::FFFFFFFFFF   
  F:::::::::::::::F      M::::::M M::::M M::::M M::::::M     F:::::::::::::::F   
  F:::::::::::::::F      M::::::M  M::::M::::M  M::::::M     F:::::::::::::::F   
  F::::::FFFFFFFFFF      M::::::M   M:::::::M   M::::::M     F::::::FFFFFFFFFF   
  F:::::F                M::::::M    M:::::M    M::::::M     F:::::F             
  F:::::F                M::::::M     MMMMM     M::::::M     F:::::F             
FF:::::::FF              M::::::M               M::::::M   FF:::::::FF           
F::::::::FF              M::::::M               M::::::M   F::::::::FF           
F::::::::FF              M::::::M               M::::::M   F::::::::FF           
FFFFFFFFFFF              MMMMMMMM               MMMMMMMM   FFFFFFFFFFF           
```                                                                          

FMF is a pluggable, provider-agnostic framework for building LLM-powered data workflows across Azure OpenAI, AWS Bedrock, and more. It provides unified configuration, connectors (local, S3, SharePoint), processing pipelines, inference adapters, and a fluent Python SDK for rapid development.

## Quick Install

```bash
# Clone the repository
git clone <repository-url>
cd frontier-model-framework

# Install with uv (recommended - handles venv creation automatically)
uv sync

# Or install with specific extras
uv sync --extra aws              # AWS support (S3, Bedrock)
uv sync --extra azure            # Azure support (Azure OpenAI)
uv sync --extra aws --extra azure  # Both providers

# For development
uv sync --extra aws --extra azure --extra dev --extra test
```

**Note**: `uv sync` automatically creates a virtual environment in `.venv/` and installs all dependencies from `pyproject.toml` and `uv.lock`.

## SDK Quickstart

### Basic CSV Analysis

```python
from fmf.sdk import FMF

# Initialize and run CSV analysis
fmf = FMF.from_env("fmf.yaml")
result = fmf.csv_analyse(
    input="data/sample.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Analyze sentiment and extract key themes from this comment",
    return_records=True,
    connector="local_docs"
)

print(f"Processed {result.records_processed} records")
print(f"Output: {result.primary_output_path}")
```

### Using Fluent API with AWS Bedrock

```python
from fmf.sdk import FMF

# Configure using fluent API
fmf = (FMF.from_env("fmf.yaml")
       .with_service("aws_bedrock")
       .with_response("both"))

result = fmf.csv_analyse(
    input="data/sample.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Analyze sentiment and extract key themes",
    return_records=True,
    connector="local_docs",
    mode="regular"
)

print(f"Processed {result.records_processed} records")
if result.data:
    print(f"Sample result: {result.data[0]}")
```

### Reading from S3

```python
from fmf.sdk import FMF

# AWS credentials are automatically loaded from .env
fmf = (FMF.from_env("fmf.yaml")
       .with_service("aws_bedrock")
       .with_response("both"))

# Analyze CSV files from S3
result = fmf.csv_analyse(
    input="*.csv",  # Pattern to match CSV files
    text_col="Comment",
    id_col="ID",
    prompt="Analyze sentiment and extract key themes",
    return_records=True,
    connector="s3_raw",  # S3 connector from fmf.yaml
    mode="regular"
)

print(f"Processed {result.records_processed} records from S3")
print(f"Output: {result.primary_output_path}")
```

## CLI Quickstart

```bash
# CSV analysis with local files
fmf csv data/sample.csv Comment ID "Analyze sentiment and extract key themes"

# With service override
fmf csv data/sample.csv Comment ID "Analyze sentiment" --service aws_bedrock

# Text processing
fmf text data/*.md "Extract key information"

# Image analysis
fmf images sample/images/*.jpg "Describe this image"
```

## Configuration

FMF uses a sophisticated configuration system that merges multiple sources with clear precedence:

**Precedence Order (highest to lowest):**
1. **Fluent API overrides** - Programmatic configuration via `.with_service()`, `.with_rag()`, etc.
2. **Base YAML config** - Default configuration from `fmf.yaml`

**In-Memory Processing:**
- Configurations are merged in-memory using Pydantic models for type safety and validation
- No temporary files are created during execution
- All type coercion and validation happens at merge time

**Example:**
```python
# Base config: inference.provider = "azure_openai", temperature = 0.1
# Fluent override: provider = "aws_bedrock"

# Result: provider = "aws_bedrock" (fluent wins), temperature = 0.1 (base config)
fmf = (FMF.from_env("fmf.yaml")
       .with_service("aws_bedrock"))  # Fluent override
```

## Examples

All examples are in the `examples/` directory and can be run with:

```bash
uv run examples/<example_name>.py
```

### Available Examples

- **`analyse_csv_bedrock.py`** - CSV analysis using AWS Bedrock with local files
- **`analyse_csv_s3_bedrock.py`** - CSV analysis reading from S3 bucket  
- **`dataframe_analyse.py`** - Direct pandas DataFrame analysis
- **`images_analyse.py`** - Image analysis with multimodal models
- **`text_analysis.py`** - Text file processing

### Example: CSV Analysis with Bedrock

```python
# examples/analyse_csv_bedrock.py
from fmf.sdk import FMF

fmf = (FMF.from_env("fmf.yaml")
       .with_service("aws_bedrock")
       .with_response("both"))

result = fmf.csv_analyse(
    input="data/sample.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Analyze sentiment and extract key themes",
    return_records=True,
    connector="local_docs"
)

print(f"Processed {result.records_processed} records")
```

### Example: S3 Integration

```python
# examples/analyse_csv_s3_bedrock.py  
from fmf.sdk import FMF

# Credentials loaded automatically from .env
fmf = (FMF.from_env("fmf.yaml")
       .with_service("aws_bedrock")
       .with_response("both"))

result = fmf.csv_analyse(
    input="*.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Analyze sentiment",
    connector="s3_raw"  # Configured in fmf.yaml
)

print(f"Processed {result.records_processed} records from S3")
```

## Features

- **YAML-first configuration** with env/CLI overrides and profiles
- **Data connectors** (local, S3, SharePoint/Graph) with streaming reads
- **Processing**: normalization, tables → Markdown, optional OCR, chunking
- **Inference adapters**: Azure OpenAI and Bedrock, with retries and rate limiting
- **Prompt registry** with versioning and content hashing
- **Exports** to S3, DynamoDB, Excel, Redshift, Delta, Fabric
- **Observability**: structured logs with redaction, metrics, optional tracing
- **Reproducible artefacts** and a simple CLI for processing, running chains, and export

## Development

```bash
# Install all dev dependencies
uv sync --extra aws --extra azure --extra dev --extra test

# Run linting
uv run ruff check src/

# Auto-format code
uv run ruff format src/

# Run tests (if available)
uv run pytest tests/

# Run CLI
uv run fmf --help

# Run examples
uv run examples/analyse_csv_bedrock.py
```

## Project Structure

```
frontier-model-framework/
├── src/fmf/              # Main package
│   ├── sdk/              # Fluent SDK API
│   ├── connectors/       # Data connectors (local, S3, SharePoint)
│   ├── inference/        # LLM clients (Azure OpenAI, Bedrock)
│   ├── processing/       # Document loaders and processors
│   ├── chain/            # Chain execution engine
│   ├── auth/             # Authentication providers
│   ├── exporters/        # Output exporters
│   └── cli.py            # Command-line interface
├── examples/             # Working examples
├── tests/                # Test suite
├── fmf.yaml              # Main configuration file
├── ruff.toml             # Linting configuration
└── pyproject.toml        # Package metadata
```

## Architecture

See `docs/adr/ADR-001-sdk-first.md` for the architectural decision record and design principles.

## Contributing

- Please read `AGENTS.md` for architecture, extension points, and coding conventions
- Issues and PRs are welcome; keep changes small and focused