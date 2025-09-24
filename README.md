Frontier Model Framework (FMF)
==============================

FMF is a pluggable, provider‑agnostic framework for building LLM‑powered data workflows across Azure OpenAI, AWS Bedrock, and more. It provides unified configuration, connectors, processing, inference adapters, prompt versioning, exports, and a simple CLI for running pipelines end‑to‑end.

Links
-----

- Unified workflow & use-case playbooks: `docs/USAGE.md`
- Architecture and conventions: `AGENTS.md`
- Build plan and milestone tracking: `docs/BUILD_PLAN.md`
- Deployment notes and IAM examples: `docs/DEPLOYMENT.md`, `docs/IAM_POLICIES.md`
- Examples: `examples/`

Features
--------

- YAML‑first configuration with env/CLI overrides and profiles
- Data connectors (local, S3, SharePoint/Graph) with streaming reads
- Processing: normalization, tables → Markdown, optional OCR, chunking
- Inference adapters: Azure OpenAI and Bedrock, with retries and rate limiting
- Prompt registry with versioning and content hashing
- Exports to S3 and DynamoDB (plus stubs for Excel/Redshift/Delta/Fabric)
- Observability: structured logs with redaction, basic metrics, optional tracing
- Reproducible artefacts and a simple CLI for processing, running chains, and export

Requirements
------------

- Python 3.12+
- uv (package/dependency manager): https://github.com/astral-sh/uv

Getting Started (uv)
--------------------

1) Create and activate an environment and install FMF with extras you need:

```
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync -E aws -E azure     # installs base + selected extras from pyproject
# Alternatively:
# uv pip install -e .[aws,azure]
```

2) Copy and edit the example config, and add some sample Markdown files under `./data`:

```
cp examples/fmf.example.yaml fmf.yaml
```

3) **Quick Start with Python SDK** (recommended):

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
       .defaults(service="azure_openai", rag=True, response="csv")
       .from_s3("my-bucket", "data/"))

# Context manager for resource cleanup
with fmf as f:
    result = f.csv_analyse(
        input="./data/comments.csv", 
        text_col="Comment", 
        id_col="ID", 
        prompt="Analyze sentiment"
    )
    print(f"Success: {result.success}, Records: {result.records_processed}")

# Source helpers for common patterns
fmf = (FMF.from_env("fmf.yaml")
       .from_sharepoint("https://contoso.sharepoint.com/sites/docs", "Documents")
       .from_local("./data", include_patterns=["**/*.md", "**/*.txt"])
       .defaults(service="azure_openai", rag={"pipeline": "documents"}))
```

### Fluent API vs CLI Mapping

| Fluent API Method | CLI Equivalent | Description |
|------------------|----------------|-------------|
| `with_service("azure_openai")` | `--set inference.provider=azure_openai` | Configure inference provider |
| `with_rag(enabled=True, pipeline="docs")` | `--enable-rag --rag-pipeline docs` | Enable RAG with pipeline |
| `with_response("csv")` | `--set export.sinks[0].format=csv` | Set output format |
| `with_source("s3", bucket="my-bucket")` | `--set connectors[0].type=s3` | Configure data source |
| `run_inference("csv", "analyse", ...)` | `fmf csv analyse` | Execute inference |
| `csv_analyse(...)` | `fmf csv analyse` | CSV analysis shortcut |
| `text_to_json(...)` | `fmf text infer` | Text processing shortcut |
| `images_analyse(...)` | `fmf images analyse` | Image analysis shortcut |

### Configuration Precedence & In-Memory Merge

FMF uses a sophisticated configuration system that merges multiple sources with clear precedence:

**Precedence Order (highest to lowest):**
1. **Fluent API overrides** - Programmatic configuration via `.with_service()`, `.with_rag()`, etc.
2. **Base YAML config** - Default configuration from `fmf.yaml`

**In-Memory Processing:**
- Configurations are merged in-memory using Pydantic models for type safety and validation
- No temporary files are created during execution
- All type coercion and validation happens at merge time
- Effective configuration is computed once and reused throughout execution

**Example:**
```python
# Base config: inference.provider = "azure_openai", temperature = 0.1
# Fluent override: provider = "aws_bedrock"

# Result: provider = "aws_bedrock" (fluent wins), temperature = 0.1 (base config)
fmf = (FMF.from_env("fmf.yaml")
       .with_service("aws_bedrock"))  # Fluent override
```

### SDK Ergonomics & Rich Results

FMF provides enhanced ergonomics for better developer experience:

**Rich Return Types:**
```python
result = fmf.csv_analyse(input="data.csv", text_col="Comment", id_col="ID", prompt="Analyze")

# Rich metadata and results
print(f"Success: {result.success}")
print(f"Records processed: {result.records_processed}")
print(f"Duration: {result.duration_ms:.1f}ms")
print(f"Output files: {result.output_paths}")
print(f"Service used: {result.service_used}")
print(f"RAG enabled: {result.rag_enabled}")

# Access raw data if needed
if result.data:
    for record in result.data:
        print(f"ID: {record['id']}, Analysis: {record['analysed']}")
```

**Convenience Methods:**
```python
# Set common defaults in one call
fmf = FMF.from_env("fmf.yaml").defaults(
    service="azure_openai",
    rag=True,
    response="csv"
)

# Source helpers for common patterns
fmf = (FMF.from_env("fmf.yaml")
       .from_sharepoint("https://contoso.sharepoint.com/sites/docs", "Documents")
       .from_s3("my-bucket", "data/", region="us-east-1")
       .from_local("./data", include_patterns=["**/*.md", "**/*.txt"]))
```

**Context Manager for Resource Cleanup:**
```python
# Automatic resource cleanup
with FMF.from_env("fmf.yaml").defaults(service="azure_openai") as fmf:
    result = fmf.csv_analyse(input="data.csv", text_col="Comment", id_col="ID", prompt="Analyze")
    # Resources are automatically cleaned up when exiting the context
```

**Scripts & CLI**

SDK Scripts (Recommended)
```
# CSV analysis with fluent API
python scripts/analyse_csv.py --input ./data/comments.csv --text-col Comment --id-col ID --prompt "Summarize"

# Text to JSON conversion
python scripts/text_to_json_sdk.py --input ./data/documents.md --prompt "Extract key information"

# With RAG enabled
python scripts/analyse_csv.py --input ./data/comments.csv --text-col Comment --id-col ID --prompt "Analyze" --enable-rag

# With custom service and output format
python scripts/analyse_csv.py --input ./data/comments.csv --text-col Comment --id-col ID --prompt "Analyze" --service azure_openai --output-format jsonl
```

CLI Convenience
```
uv run fmf csv analyse --input ./data/comments.csv --text-col Comment --id-col ID --prompt "Summarise" -c fmf.yaml
```

4) Run the processing and sample chain (via uv):

```
uv run fmf process --connector local_docs --select "**/*.md" -c fmf.yaml
uv run fmf run --chain examples/chains/sample.yaml -c fmf.yaml
```

5) Review artefacts under `artefacts/<run_id>/` (`docs.jsonl`, `chunks.jsonl`, `outputs.jsonl`, `run.yaml`).

CLI Overview
------------

The unified `fmf` CLI provides a single entry point for all FMF operations:

### Primary Commands (SDK-First)

- `fmf csv analyse --input file.csv --text-col COL --id-col COL --prompt "..."` – Analyze CSV files
- `fmf text --input file.txt --prompt "..."` – Process text files to JSON
- `fmf images --input file.png --prompt "..."` – Analyze images
- `fmf keys test [NAMES...]` – Verify secrets resolution

### Legacy Commands (Ops/CI)

- `fmf connect ls <connector> --select "glob"` – List ingestible resources
- `fmf process --connector <name> --select "glob"` – Normalize + chunk to artefacts
- `fmf prompt register <file>#<version>` – Register prompt version in registry
- `fmf infer --input file.txt [--mode auto|regular|stream]` – Single‑shot completion
- `fmf run --chain chains/sample.yaml` – Execute a chain file (end‑to‑end)
- `fmf export --sink <name> --input artefacts/<run_id>/outputs.jsonl` – Write results

### CLI Examples

```bash
# Basic CSV analysis
fmf csv analyse --input data/comments.csv --text-col Comment --id-col ID --prompt "Summarize"

# With RAG enabled
fmf csv analyse --input data/comments.csv --text-col Comment --id-col ID --prompt "Analyze" --rag

# With custom service and output format
fmf csv analyse --input data/comments.csv --text-col Comment --id-col ID --prompt "Analyze" --service azure_openai --response jsonl

# Text processing
fmf text --input "*.txt" --prompt "Extract key information" --output results.jsonl

# Image analysis
fmf images --input "*.png" --prompt "Describe the content" --rag --rag-pipeline documents

# Dry run to see what would be done
fmf csv analyse --input data/comments.csv --text-col Comment --id-col ID --prompt "Analyze" --dry-run
```

### Fluent API vs CLI Equivalence

| Fluent API | CLI Command | Description |
|------------|-------------|-------------|
| `FMF.from_env("config.yaml")` | `fmf --config config.yaml` | Load configuration |
| `.with_service("azure_openai")` | `--service azure_openai` | Set inference provider |
| `.with_rag(enabled=True, pipeline="docs")` | `--rag --rag-pipeline docs` | Enable RAG |
| `.with_response("csv")` | `--response csv` | Set output format |
| `.with_source("s3", bucket="my-bucket")` | `--source s3` | Configure data source |
| `.csv_analyse(input="file.csv", ...)` | `fmf csv analyse --input file.csv ...` | CSV analysis |
| `.text_to_json(prompt="...", ...)` | `fmf text --prompt "..." ...` | Text processing |
| `.images_analyse(prompt="...", ...)` | `fmf images --prompt "..." ...` | Image analysis |

Repository Layout
-----------------

```
src/fmf/
  auth/           # secret providers (env, Azure KV, AWS)
  chain/          # chain loader + runner
  config/         # YAML loader, overrides, profiles (Pydantic models)
  connectors/     # local, s3, sharepoint (Graph)
  exporters/      # s3, dynamodb, stubs for excel/redshift/delta/fabric
  inference/      # base types + Azure OpenAI + Bedrock adapters
  observability/  # logging, metrics, optional tracing spans
  processing/     # loaders, normalization, tables, OCR, chunking, persist
  prompts/        # YAML prompt registry + hashing

examples/
  fmf.example.yaml          # example configuration
  prompts/summarize.yaml    # example prompt (versioned)
  chains/sample.yaml        # example chain

docs/                       # usage, deployment, IAM samples
docker/                     # Lambda and Batch Dockerfiles
tests/                      # unit and e2e tests
```

Development
-----------

- Install dev deps and extras with uv:

```
uv sync -E aws -E azure -E excel -E redshift -E delta
```

- Run tests:

```
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

- Run CLI via uv (no manual activation required):

```
uv run fmf --help
```

Contributing
------------

- Please read `AGENTS.md` for architecture, extension points, and coding conventions.
- The project follows incremental milestones documented in `BUILD_PLAN.md`.
- Issues and PRs are welcome; keep changes small and focused.
