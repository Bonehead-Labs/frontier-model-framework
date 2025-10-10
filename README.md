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

## Features

- **Fluent Python SDK** - Chainable API for CSV, text, image, and DataFrame analysis
- **Multi-provider inference** - Azure OpenAI, AWS Bedrock with unified interface
- **Data connectors** - Local files, S3, SharePoint with streaming reads
- **YAML-first configuration** - Human-readable config with environment overrides
- **Processing pipelines** - Text chunking, table parsing, OCR, metadata extraction
- **Export sinks** - S3, DynamoDB, Excel, Redshift, Delta, Fabric
- **Observability** - Structured logs, metrics, optional OpenTelemetry tracing

## Getting Started

Choose your path:
- **[Use as a Package](#use-as-a-package)** → Install FMF in your project via Git
- **[Develop Locally](#develop-locally)** → Clone and contribute to FMF

---

## Use as a Package

Install FMF from Git and use it in your projects without cloning the full repository.

### Install

Using **uv** (recommended):
```bash
uv add "git+https://github.com/Bonehead-Labs/frontier-model-framework.git#egg=frontier-model-framework[aws,azure]"
```

Using **pip**:
```bash
pip install "git+https://github.com/Bonehead-Labs/frontier-model-framework.git#egg=frontier-model-framework[aws,azure]"
```

### Configure

Create `fmf.yaml` and `.env` in your project root:

**fmf.yaml**:
```yaml
project: my-project
artefacts_dir: artefacts

auth:
  provider: env
  env:
    file: .env

connectors:
  - name: local_docs
    type: local
    root: ./data
    include: ['**/*.csv', '**/*.txt', '**/*.md']

inference:
  provider: azure_openai  # or aws_bedrock
  azure_openai:
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    api_version: 2024-02-15-preview
    deployment: gpt-4o-mini
    temperature: 0.2
```

**.env** (add to `.gitignore`):
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key

AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
```

**Resources**:
- [Full Configuration Guide](docs/CONFIGURATION.md)
- [Example Template](fmf.example.yaml)
- [Working Examples](examples/)

### Quick Usage

**Python SDK**:
```python
from fmf.sdk import FMF

fmf = (FMF.from_env("fmf.yaml")
       .with_service("aws_bedrock")
       .with_response("both"))

result = fmf.csv_analyse(
    input="data/sample.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Analyze sentiment",
    return_records=True
)

print(f"Processed {result.records_processed} records")
```

---

## Develop Locally

Clone the repository to contribute or run examples.

### Install

```bash
# Clone the repository
git clone https://github.com/Bonehead-Labs/frontier-model-framework.git
cd frontier-model-framework

# Install with uv (creates .venv automatically)
uv sync --extra aws --extra azure

# Or install specific extras
uv sync --extra aws              # AWS support only
uv sync --extra azure            # Azure support only
uv sync --extra dev --extra test # Development tools
```

**Note**: `uv sync` automatically creates a virtual environment in `.venv/` and installs all dependencies from `pyproject.toml` and `uv.lock`.

### Configure

The repo includes `fmf.yaml` and `.env` templates. Copy and customize:

```bash
# Create your .env from template
cp .env.example .env
# Edit .env with your credentials

# fmf.yaml is already configured for local development
```

### Run Examples

```bash
# Run any example script
uv run examples/analyse_csv_bedrock.py

# Run CLI commands
uv run fmf --help
```

---

## Usage Examples

### Python SDK

#### Basic CSV Analysis

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

#### Using Fluent API with AWS Bedrock

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

#### Reading from S3

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

## Examples Directory

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

## Architecture & Features

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

## Fork this Repo

To maintain a customized version for your organization while syncing with upstream patches:

1. Fork the repository on GitHub to your org's account.
2. Clone your fork locally: `git clone https://github.com/your-org/frontier-model-framework.git`
3. Add upstream remote: `git remote add upstream https://github.com/boneheadlabs/frontier-model-framework.git`
4. Sync updates: `git fetch upstream && git merge upstream/main` (resolve any merge conflicts).
5. Develop custom changes on branches, commit, and push to your fork.

This keeps your version independent while pulling in latest changes from the original.
