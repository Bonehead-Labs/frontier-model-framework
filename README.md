# Frontier Model Framework (FMF)

FMF is a pluggable, provider-agnostic framework for building LLM-powered data workflows across Azure OpenAI, AWS Bedrock, and more. It provides unified configuration, connectors, processing, inference adapters, prompt versioning, exports, and a simple CLI for running pipelines end-to-end.

## Install

```bash
# Install with uv (recommended)
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync -E aws -E azure

# Or with pip
pip install -e .[aws,azure]
```

## SDK Quickstart

```python
from fmf.sdk import FMF

# Simple analysis with rich results
fmf = FMF.from_env("fmf.yaml")
result = fmf.csv_analyse(
    input="./data/comments.csv", 
    text_col="Comment", 
    id_col="ID", 
    prompt="Summarise this comment"
)

print(f"Processed {result.records_processed} records in {result.duration_ms:.1f}ms")
print(f"Output saved to: {result.primary_output_path}")

# Fluent API with ergonomics
fmf = (FMF.from_env("fmf.yaml")
       .with_service("azure_openai")
       .with_rag(enabled=True, pipeline="documents")
       .with_response("csv")
       .with_source("local", root="./data"))

# Context manager for resource cleanup
with fmf as f:
    result = f.csv_analyse(
        input="./data/comments.csv", 
        text_col="Comment", 
        id_col="ID", 
        prompt="Analyze sentiment"
    )
    print(f"Success: {result.success}, Records: {result.records_processed}")
```

## CLI Quickstart

```bash
# CSV analysis
fmf csv analyse --input ./data/comments.csv --text-col Comment --id-col ID --prompt "Summarise"

# Text processing
fmf text --input ./data/documents.md --prompt "Extract key information"

# With RAG enabled
fmf csv analyse --input ./data/comments.csv --text-col Comment --id-col ID --prompt "Analyze" --rag
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

- **CSV Analysis**: `examples/analyse_csv.py` - [Usage Guide](docs/usage/csv_analyse.md)
- **Text Processing**: `examples/text_to_json.py` - [Usage Guide](docs/usage/text_to_json.md)
- **Image Analysis**: `examples/images_analyse.py` - [Usage Guide](docs/usage/images_analyse.md)
- **SDK Demo**: `examples/sdk_demo.py` - Comprehensive SDK examples

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
# Install dev dependencies
uv sync -E aws -E azure -E excel -E redshift -E delta

# Run tests
uv run python -m unittest discover -s tests -p "test_*.py" -v

# Run CLI
uv run fmf --help
```

## Architecture

See `docs/adr/ADR-001-sdk-first.md` for the architectural decision record and design principles.

## Contributing

- Please read `AGENTS.md` for architecture, extension points, and coding conventions
- Issues and PRs are welcome; keep changes small and focused