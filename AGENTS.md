# Frontier Model Framework (FMF)

A pluggable framework for frontier LLMs across providers (Azure via Azure OpenAI, AWS via Bedrock, and others), with unified data ingestion, processing, inference, prompt versioning, and key management. This document serves both LLM agents and human developers as the single source of truth for architecture, conventions, and extension points.

## Design Principles
- Plug-and-play components with clear, minimal interfaces
- Human-readable YAML-first configuration; no hard‑coding
- Provider-agnostic core with thin provider adapters
- Deterministic, reproducible runs via prompt + config versioning
- Secure-by-default secret handling; no secrets in code or logs
- Observable: structured logs, metrics, and run artifacts
- Resilient: retries, backoff, rate limiting, idempotent operations
- Async-first where practical for throughput
 - Developer UX: first‑class Python SDK and convenience CLI; YAML remains available but optional

## Layered Architecture
- Data Connection Layer: Configurable connectors for SharePoint, S3, and local files
- Data Processing Layer: Normalize text/tables/images into LLM-ready documents
- Inference Layer: Unified LLM API for single prompts and chains across providers
- Data Export Layer: Write inferences and artefacts to external sinks (SharePoint Excel, S3, Fabric/Delta, Redshift, DynamoDB)
- Prompt Versioning Layer: Track prompts, versions, lineage, and run outputs
- Auth & Keys Layer: Pluggable secret backends (.env, Azure Key Vault, AWS)

```
+---------------------------+
|        CLI / SDK          |
+-------------+-------------+
              |
+-------------v-------------+
|     YAML Config Loader    |
+-------------+-------------+
              |
   +----------v----------+
   |     Auth & Keys     |
   +----------+----------+
              |
+-------------v-------------+
|     Data Connection       |
+-------------+-------------+
              |
+-------------v-------------+
|     Data Processing       |
+-------------+-------------+
              |
+-------------v-------------+
|        Inference          |
+-------------+-------------+
              |
+-------------v-------------+
|        Data Export        |
+-------------+-------------+
              |
+-------------v-------------+
| Prompt Versioning & Runs  |
+---------------------------+
```

## Target Python Runtime
- Python `>=3.12`
- Packaging via `pyproject.toml`

## Proposed Source Layout
- `src/fmf/` (package root)
  - `config/` – loaders, schema validation (Pydantic)
  - `auth/` – secret providers: `.env`, Azure, AWS
  - `connectors/` – `base.py`, `local.py`, `s3.py`, `sharepoint.py`
  - `processing/` – loaders, parsers, chunkers, ocr, table readers
  - `inference/` – `base_client.py`, `azure_openai.py`, `bedrock.py`, `unified.py`, `chains/`
  - `prompts/` – registry, storage backends, templates
  - `sdk/` – high‑level developer API (FMF facade: csv_analyse, text_files, images_analyse)
- `observability/` – logging, metrics, tracing
- `types.py` – common dataclasses (Document, Chunk, RunRecord, etc.)
  - `exporters/` – sink writers (s3, sharepoint_excel, delta, redshift, dynamodb)

Keep changes minimal and focused; follow existing style when present.

---

# Configuration

FMF is configured via YAML. CLI flags and environment variables can override YAML fields. Validation should use Pydantic models.

## Global Config (fmf.yaml)
```yaml
# fmf.yaml
project: frontier-model-framework
run_profile: default
artefacts_dir: artefacts

auth:
  provider: env              # one of: env, azure_key_vault, aws_secrets
  env:
    file: .env               # optional; default is process env only
  azure_key_vault:
    vault_url: https://<your-vault>.vault.azure.net/
    tenant_id: <tenant-id>
    client_id: <app-id>
    secret_mapping:          # logical name -> KV secret name
      OPENAI_API_KEY: openai-api-key
  aws_secrets:
    region: us-east-1
    source: secretsmanager   # or ssm
    secret_mapping:
      BEDROCK_API_KEY: bedrock/api-key

connectors:
  - name: local_docs
    type: local
    root: ./data
    include: ['**/*.txt', '**/*.md', '**/*.csv']
  - name: s3_raw
    type: s3
    bucket: my-bucket
    prefix: raw/
    region: us-east-1
  - name: sp_hr
    type: sharepoint
    site_url: https://contoso.sharepoint.com/sites/HR
    drive: Documents
    root_path: Policies/

processing:
  text:
    chunking:
      strategy: recursive
      max_tokens: 800
      overlap: 150
      splitter: by_sentence
  tables:
    formats: [csv, xlsx, parquet]
    header_row: 1
    treat_as_md_table: false
  images:
    ocr:
      enabled: true
      lang: en
      engine: tesseract       # placeholder; pluggable
  metadata:
    include_source_path: true
    include_hash: sha256

inference:
  provider: azure_openai      # or aws_bedrock
  azure_openai:
    endpoint: https://<your-resource>.openai.azure.com/
    api_version: 2024-02-15-preview
    deployment: gpt-4o-mini
    temperature: 0.2
    max_tokens: 1024
  aws_bedrock:
    region: us-east-1
    model_id: anthropic.claude-3-haiku-20240307-v1:0
    temperature: 0.2
    max_tokens: 1024

export:
  default_sink: s3_results
  sinks:
    - name: s3_results
      type: s3
      bucket: my-bucket
      prefix: fmf/outputs/${run_id}/
      format: jsonl           # jsonl | parquet | csv | delta
      compression: gzip       # none | gzip | snappy (parquet)
      partition_by: [date]    # optional
      sse: kms                # s3 | kms | none
      kms_key_id: alias/fmf-writes
      mode: append            # append | upsert | overwrite
    - name: sp_excel
      type: sharepoint_excel
      site_url: https://contoso.sharepoint.com/sites/Analytics
      drive: Documents
      file_path: Reports/fmf-output.xlsx
      sheet: Results
      mode: upsert
      key_fields: [source_uri, step_id]
      create_if_missing: true
    - name: dynamodb_events
      type: dynamodb
      table: fmf-events
      region: us-east-1
      key_schema:
        pk: run_id
        sk: record_id
      ttl_attribute: expires_at
      mode: upsert
    - name: redshift_analytics
      type: redshift
      cluster_id: my-redshift
      database: analytics
      schema: public
      table: fmf_results
      unload_staging_s3: s3://my-bucket/fmf/staging/
      copy_options:
        timeformat: 'auto'
        jsonpaths: auto
      mode: upsert
      key_fields: [record_id]
    - name: delta_s3
      type: delta
      storage: s3
      path: s3://my-bucket/delta/fmf_results
      mode: append
    - name: fabric_delta
      type: fabric_delta
      workspace: MyWorkspace
      lakehouse: MyLakehouse
      table: fmf_results
      mode: upsert

prompt_registry:
  backend: git_yaml            # git_yaml | local_yaml | sqlite | dynamodb | azure_table
  path: prompts/               # for yaml-based backends
  index_file: prompts/index.yaml

run:
  chain_config: chains/sample.yaml
  inputs:
    connector: local_docs
    select:
      - "**/*.md"
```

### Override Hierarchy
- Highest: CLI flags (e.g., `--inference.temperature 0.1`)
- Then: Environment variables (e.g., `FMF_INFERENCE__TEMPERATURE=0.1`)
- Then: Local config file values

Environment variable nesting uses double underscores for path separators.

### RAG Pipelines
- Define retrieval indexes that reuse existing connectors and processing settings. Pipelines are configured under a top-level `rag.pipelines` list in `fmf.yaml`.

```yaml
rag:
  pipelines:
    - name: sample_images
      connector: local_docs
      select: ["**/*.{png,jpg,jpeg}"]
      modalities: ["image", "text"]
      max_text_items: 8
      max_image_items: 12
```

- `modalities` controls whether text chunks, images, or both are indexed. Limits (`max_*`) keep pre-built indices manageable for large corpora.
- Pipelines persist retrieved queries and matches to `artefacts/<run_id>/rag/<pipeline>.jsonl` for auditability.
- Steps opt-in to retrieval by adding a `rag` block. Retrieved text is injected into the prompt (unless `inject_prompt` is `false`) and image matches are attached automatically for multimodal calls.

```yaml
steps:
  - id: analyse
    mode: multimodal
    prompt: "inline: Describe the item using retrieved context\n{{ rag_context }}"
    inputs:
      focus: "${chunk.source_uri}"
    output: report
    rag:
      pipeline: sample_images
      query: "${document.metadata.filename}"
      top_k_text: 2
      top_k_images: 2
      text_var: rag_context
      image_var: rag_samples
```

- At runtime, the runner records retrieved samples, appends a "Retrieved context" section to the user message, and injects image data URLs alongside the primary artefact when `mode: multimodal` is used.

---

# Data Connection Layer

## Responsibilities
- Authenticate using selected `auth` provider
- Enumerate resources (files, objects, items) based on `include`/`exclude` glob patterns
- Stream/buffer reads; avoid loading entire large files into memory
- Emit structured metadata: `source_uri`, `modified_at`, `etag/hash`, `bytes`

## Connector Interface (Python sketch)
```python
class DataConnector(Protocol):
    name: str
    def list(self, selector: list[str] | None = None) -> Iterable[ResourceRef]: ...
    def open(self, ref: ResourceRef, mode: str = "rb") -> IO[bytes]: ...
    def info(self, ref: ResourceRef) -> ResourceInfo: ...
```

## Supported Connectors
- `local`: Reads from local filesystem root with glob selection
- `s3`: Uses AWS SDK (boto3) to list/get objects by prefix and patterns
- `sharepoint`: Uses Microsoft Graph/SharePoint REST to traverse and download items

## Connector Config Examples
```yaml
connectors:
  - name: local_docs
    type: local
    root: ./data
    include: ['**/*.txt', '**/*.md']
    exclude: ['**/.git/**']
  - name: s3_raw
    type: s3
    bucket: my-bucket
    prefix: raw/
    region: us-east-1
    kms_required: false
  - name: sp_policies
    type: sharepoint
    site_url: https://contoso.sharepoint.com/sites/Policies
    drive: Documents
    root_path: Policies/
    auth_profile: default
```

---

# Data Processing Layer

## Responsibilities
- Detect and load file type: text, markdown, html, csv, xlsx, parquet, images (png/jpg)
- Parse semantics: headings, sections, tables, alt text; basic HTML/Markdown normalization
- OCR for images when enabled; attach extracted text + image metadata
- Chunking strategies with overlap; token-aware sizing for target model family
- Produce `Document` and `Chunk` objects with metadata for inference

## Core Types (sketch)
```python
@dataclass
class Document:
    id: str
    source_uri: str
    text: str | None
    blobs: list[Blob] | None
    metadata: dict[str, Any]

@dataclass
class Chunk:
    id: str
    doc_id: str
    text: str
    tokens_estimate: int
    metadata: dict[str, Any]
```

## Processing Config Examples
```yaml
processing:
  text:
    normalize_whitespace: true
    preserve_markdown: true
    chunking:
      strategy: recursive
      max_tokens: 1000
      overlap: 150
  tables:
    formats: [csv, xlsx]
    include_sheet_names: true
    to_markdown: true
  images:
    ocr:
      enabled: true
      engine: tesseract
      lang: en
```

Artifacts (normalized docs, chunks) should be stored under `artefacts/` with run IDs for reproducibility.

---

# Inference Layer

## Goals
- Unified client interface across providers
- Support text-only prompts, multimodal (text + image), and structured tool responses when available
- Single-shot and chain execution from YAML
- Robust retries, timeouts, rate limiting; optional streaming

## Unified Client Interface (sketch)
```python
class LLMClient(Protocol):
    def complete(self, messages: list[Message], **params) -> Completion:
        ...
    def embed(self, inputs: list[str], **params) -> Embeddings:
        ...  # optional; provider-dependent
```

`Message` supports `role` in {system, user, assistant, tool} and multimodal content parts (text + image) when available.

## Provider Configs
- Azure OpenAI
  - `endpoint`, `api_version`, `deployment`
- AWS Bedrock
  - `region`, `model_id`

## Example Inference Config
```yaml
inference:
  provider: azure_openai
  azure_openai:
    endpoint: https://<resource>.openai.azure.com/
    api_version: 2024-02-15-preview
    deployment: gpt-4o-mini
    temperature: 0.2
    max_tokens: 1024
```

## Chain YAML (Declarative)
```yaml
# chains/sample.yaml
name: summarize-markdown
inputs:
  connector: local_docs
  select: ["**/*.md"]
steps:
  - id: summarize_chunk
    prompt: prompts/summarize.yaml#v1
    inputs:
      text: ${chunk.text}
    output: chunk_summary
  - id: aggregate
    prompt: prompts/aggregate.yaml#v2
    inputs:
      summaries: ${all.chunk_summary}
    output: report
outputs:
  - save: artefacts/${run_id}/report.md
    from: report
  - export: s3_results
    from: report
    as: jsonl
```

- `${chunk.text}` and `${all.*}` denote runtime variable interpolation
- `prompt` references use `path#version`

## Runtime Behaviors
- Concurrency: configurable max in-flight requests
- Backoff: exponential with jitter on 429/5xx
- Streaming: optional token stream handlers
- Cost accounting: track tokens and estimated USD per run (if available)

---

# Data Export Layer

## Responsibilities
- Persist LLM results to external stores for downstream analytics and apps
- Reuse connectors where possible (e.g., S3, SharePoint); add DB-specific exporters where needed
- Map outputs to tabular or document formats with configurable schemas
- Support write modes: `append`, `upsert`, `overwrite`; ensure idempotency via keys
- Handle batching, retries, partial failures, and backpressure

## Exporter Interface (sketch)
```python
class Exporter(Protocol):
    name: str
    def write(
        self,
        records: Iterable[dict[str, Any]] | bytes | str,
        *,
        schema: dict[str, Any] | None = None,
        mode: Literal["append", "upsert", "overwrite"] = "append",
        key_fields: list[str] | None = None,
    ) -> ExportResult: ...

    def finalize(self) -> None: ...  # flush/close handles
```

`records` may be a stream of normalized dicts or a serialized payload (CSV/Parquet/JSONL). Upserts require `key_fields`.

## Supported Sinks
- `s3`: JSONL/CSV/Parquet/Delta with optional partitioning and encryption (SSE-S3/KMS)
- `sharepoint_excel`: Append/upsert rows in a workbook/sheet; create file if missing
- `delta`/`fabric_delta`: Write Delta tables to S3 or Microsoft Fabric Lakehouse
- `redshift`: COPY/UNLOAD staging strategy with merge/upsert by key
- `dynamodb`: BatchWrite/TransactWrite with exponential backoff and capacity-aware throttling

## Standard Output Record
All exporters should accept a canonical record shape; additional fields are allowed.
```yaml
record:
  run_id: ${run_id}
  chain_id: ${chain.id}
  step_id: ${step.id}
  source_uri: ${chunk.source_uri}
  prompt_id: summarize
  prompt_version: v2
  input: ${chunk.text}
  output: ${report}
  model: ${provider.model}
  created_at: ${now}
  meta:
    tokens_prompt: ${metrics.tokens_prompt}
    tokens_completion: ${metrics.tokens_completion}
```

Schema mapping can be configured per sink, including field renames, type coercions, and JSON flattening.

## Idempotency & Schemas
- Deduplicate on `run_id + step_id + source_uri` by default, override with `key_fields`
- Schema evolution is sink-specific: Parquet/Delta support additive columns; Excel/Redshift require migrations

---

# Prompt Versioning Layer

## Goals
- Reproducibility: Every output ties back to exact prompt version
- Auditability: Who changed what and why
- Discoverability: Tags, purpose, owner, and usage examples

## Prompt Record (YAML)
```yaml
# prompts/summarize.yaml
id: summarize
versions:
  - version: v1
    created_at: 2025-09-14T19:00:00Z
    author: team@contoso.com
    tags: [summarization, md]
    inputs:
      required: [text]
    template: |
      You are a helpful assistant. Summarize:
      ---
      {{ text }}
    tests:
      - name: short-md
        inputs: { text: "# Title\nSome text." }
        assertions:
          contains: ["Title", "Some"]
    notes: Initial version.
  - version: v2
    created_at: 2025-09-20T10:00:00Z
    author: team@contoso.com
    changes: "Tighter style; keep bullets under 6 lines"
    template: |
      Summarize in 3-5 bullets. Use concise phrasing:
      {{ text }}
```

## Backends
- `git_yaml`: YAML files committed to Git. Version is explicit (`v1`, `v2`) and tracked with commit SHAs; a `content_hash` can be computed to lock content.
- `local_yaml`: YAML on disk without Git requirements.
- `sqlite`/`dynamodb`/`azure_table`: Store prompts and versions as rows with unique `(id, version)`.

## Run Record
Link outputs to prompt versions and configs for reproducibility.
```yaml
# artefacts/<run_id>/run.yaml
run_id: 2025-09-14T19-22-31Z-abc123
profile: default
inputs:
  connector: local_docs
  selector: ["**/*.md"]
config_hash: 9f1c...
prompts_used:
  - id: summarize
    version: v2
    content_hash: 45ab...
provider:
  name: azure_openai
  model: gpt-4o-mini
metrics:
  tokens_prompt: 1234
  tokens_completion: 543
  cost_estimate_usd: 0.06
artefacts:
  - path: artefacts/...
```

---

# Auth & API Keys

## Providers
- `env`: read from process environment and optional `.env` file
- `azure_key_vault`: resolve logical names to Key Vault secrets
- `aws_secrets`: resolve via AWS Secrets Manager or SSM Parameter Store

## Secret Resolution Contract
- Logical names (e.g., `OPENAI_API_KEY`) used in provider configs
- Resolution occurs at startup; values cached in-memory with TTL
- No secrets logged; redact using `****` in debug output

## Example
```yaml
auth:
  provider: aws_secrets
  aws_secrets:
    region: us-east-1
    source: secretsmanager
    secret_mapping:
      BEDROCK_API_KEY: bedrock/api-key
```

---

# Python SDK (Convenience)

For developer convenience, an optional high‑level SDK exposes simple methods that internally build a chain and call the runner:

```python
from fmf.sdk import FMF

fmf = FMF.from_env("fmf.yaml")  # auto‑loads config; falls back to sensible defaults

# CSV per‑row analysis – produces artefacts and can return in‑memory records
records = fmf.csv_analyse(
    input="./data/comments.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Summarise this comment concisely.",
    save_csv="artefacts/${run_id}/analysis.csv",
    return_records=True,
)
```

Internally the SDK calls a programmatic runner (run_chain_config) to execute the generated chain; artefacts and metrics behave the same as with YAML‑driven runs.

---

# CLI (Proposed)

- `fmf keys test` – verify secret resolution for the current profile
- `fmf connect ls <connector>` – list resources matching `select`
- `fmf process --connector <name> --select "**/*.md"` – extract + chunk into artefacts
- `fmf prompt register <file>#<version>` – validate and add to registry
- `fmf run --chain chains/sample.yaml` – execute a chain
- `fmf infer --prompt <id>#<version> --input file.txt` – single-shot completion
- `fmf export --sink <name> --input artefacts/<run_id>/outputs.jsonl` – write outputs to a configured sink
- `fmf run --chain chains/sample.yaml --sinks s3_results,redshift_analytics` – run and export in one go

Convenience wrappers (mirror the SDK):
- `fmf csv analyse --input comments.csv --text-col Comment --id-col ID --prompt "Summarise"`
- `fmf text infer --select "**/*.md" --prompt "Summarise"`
- `fmf images analyse --select "**/*.{png,jpg,jpeg}" --prompt "Describe"`

All commands accept `-c fmf.yaml` and `--set key.path=value` overrides.

---

# Observability & Artefacts

- Logs: structured JSON by default; human format for TTY
- Metrics: counts for documents, chunks, tokens, costs, retries
- Tracing: optional OpenTelemetry spans around I/O and API calls
- Artefacts directory: `artefacts/<run_id>/...` stores normalized docs, chunk files, run.yaml, and outputs

---

# Error Handling & Retries

- Taxonomy: `ConfigError`, `AuthError`, `ConnectorError`, `ProcessingError`, `InferenceError`, `PromptRegistryError`, `ExportError`
- Retries: exponential backoff with jitter on transient errors (429, 5xx, throttling)
- Idempotency: use run IDs and deterministic artefact paths; safe to resume
- Partial failures: continue when possible; record per-item status in artefacts

---

# Security & Compliance

- Least privilege for IAM and KV access; scoped roles for read-only data ingestion
- Optional local-only mode for air-gapped processing
- PII handling: optional pre-processing redaction; configurable allow/deny lists
- Redact secrets in logs and error messages
- Data residency: connectors can enforce region or path constraints
- Audit: prompt and config version recorded in `run.yaml`

---

# Performance

- Async I/O for connectors and inference
- Batching for embeddings and table reads where supported
- Token-aware chunking to reduce overflow and retries
- Optional caching for model responses keyed by prompt hash + inputs

---

# Deployment Targets

## Profiles
- Use `run_profile` and environment overrides to tailor behavior for `local`, `aws_lambda`, and `aws_batch`.
- Prefer remote artefacts (S3) in serverless; use `/tmp` for ephemeral local scratch only.

## AWS Lambda
- Packaging: container image (Python 3.12) with required extras; avoid heavy native deps unless using container images or layers
- Storage: write temporary files to `/tmp`; persist artefacts/exports to S3
- Networking: VPC only if required (e.g., Redshift private endpoint); enable retries/timeouts mindful of Lambda limits
- Secrets: resolve via AWS Secrets Manager or SSM; IAM role with least privilege
- Observability: emit JSON logs for CloudWatch; optional X-Ray tracing

## AWS Batch
- Containerized worker with `fmf` CLI entrypoint; pull configs and prompts from S3/Git
- Scale via compute environments; use IAM task role for S3, DynamoDB, Redshift access
- Prefer bulk export strategies (Parquet/Delta, Redshift COPY/UNLOAD) for throughput

## Local Machine
- Default to `.env` secrets and local filesystem for fast iteration
- Optional Docker compose for localstack (S3, DynamoDB) to test exporters

## Config Profiles Example
```yaml
profiles:
  local:
    artefacts_dir: artefacts
    auth: { provider: env }
  aws_lambda:
    artefacts_dir: s3://my-bucket/fmf/artefacts
    auth: { provider: aws_secrets }
    export: { default_sink: s3_results }
  aws_batch:
    artefacts_dir: s3://my-bucket/fmf/artefacts
    export: { default_sink: redshift_analytics }
```

Use `FMF_PROFILE=aws_lambda` or `--set profiles.active=aws_lambda` to activate.

---

# Testing Strategy

- Unit: pure functions (chunking, normalization, templating)
- Contract tests: each connector tested against local/mocked endpoints
- Provider fakes: record/replay inference fixtures to avoid live calls
- E2E: minimal chain run on sample data verifies artefact outputs
- Exporters: prefer localstack for S3 and DynamoDB; conditional integration tests for Redshift and SharePoint

---

# Extensibility Guides

## Add a Connector
- Create `src/fmf/connectors/<name>.py` implementing `DataConnector`
- Register a factory in `src/fmf/connectors/__init__.py`
- Add config schema and a small contract test with fixtures

## Add a Processor
- Implement loader/parser in `src/fmf/processing/...`
- Expose via a registry keyed by MIME or file extension
- Extend Pydantic config and sample YAML

## Add a Provider (LLM)
- Implement `LLMClient` adapter in `src/fmf/inference/<provider>.py`
- Map unified parameters (temperature, max_tokens) to provider-specific fields
- Add rate limiting, retries, and error mapping to `InferenceError`

## Add a Chain Step
- Create a YAML step referencing an existing prompt and inputs
- Optional custom step runner when non-LLM logic is required

## Add an Exporter
- Create `src/fmf/exporters/<name>.py` implementing `Exporter`
- Register in `src/fmf/exporters/__init__.py` and add config schema
- Include batching, retries, and idempotent `upsert` when supported by the sink

---

# Minimal Contribution Conventions

- Code style: follow existing patterns; prefer Pydantic for config
- Naming: snake_case for Python, kebab-case for files, lower_snake for YAML keys
- No secrets in code or tests; use fakes and env indirection
- Small, focused changes; keep public interfaces stable
- Update this AGENTS.md if you add/modify interfaces or configs

---

# Quickstart (Conceptual)

1) Create `fmf.yaml` using templates above
2) Place sample data under `./data` and define a `local_docs` connector
3) Add a prompt YAML (e.g., `prompts/summarize.yaml#v1`)
4) Run: `fmf process --connector local_docs --select "**/*.md"`
5) Run: `fmf run --chain chains/sample.yaml --sinks s3_results` and inspect S3 and `artefacts/<run_id>/`

SDK Quickstart (optional)

```python
from fmf.sdk import FMF
fmf = FMF.from_env("fmf.yaml")
fmf.csv_analyse(input="./data/comments.csv", text_col="Comment", id_col="ID", prompt="Summarise")
```

---

# Glossary
- Connector: Component that lists and reads resources from a source
- Document: Normalized representation of a source item
- Chunk: Token-aware slice of a document for LLM consumption
- Chain: Declarative series of steps executed over inputs
- Prompt Registry: Versioned store of prompt templates and metadata
- Run Record: Artefact capturing inputs, versions, metrics, and outputs
- Exporter: Component that writes outputs to an external sink (e.g., S3, Excel, Delta, Redshift, DynamoDB)
