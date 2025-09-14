# Frontier Model Framework — Build Plan & TODOs

Purpose: Convert AGENTS.md into an actionable, prioritized build plan for developers. Check off items as you deliver. Each task includes acceptance criteria and dependencies. T-shirt estimates: XS (<0.5d), S (0.5–1d), M (1–2d), L (2–4d), XL (>4d).

Status labels: [spec], [impl], [tests], [docs], [ops]

---

## Milestone M0 — Scaffolding & Foundations

- [x] Create package skeleton `src/fmf/` with subpackages: `config/`, `auth/`, `connectors/`, `processing/`, `inference/`, `prompts/`, `observability/`, `exporters/` [impl, S]
  - Acceptance: `python -m fmf` imports; basic `__init__.py` in each subpackage.
- [x] Add `fmf` CLI entrypoint via `pyproject.toml` (`[project.scripts]`) [impl, S]
  - Acceptance: `fmf --help` prints usage.
- [x] Initialize logging formatters (JSON + human) in `observability/logging.py` [impl, S]
  - Acceptance: Logs respect `FMF_LOG_FORMAT=json|human`.
- [x] Decide core third-party libs and pin minimal versions [spec, S]
  - Pydantic v2, boto3, azure-identity, azure-keyvault-secrets, msgraph/SharePoint client, tesseract optional, deltalake optional.

Dependencies: none

---

## Milestone M1 — Configuration & Secrets

- [x] Config models with Pydantic v2 (`src/fmf/config/models.py`) matching AGENTS.md [impl, M]
  - Acceptance: Loads `fmf.yaml`; env/CLI overrides; schema validation errors are actionable.
- [ ] Config loader with merge + precedence and `--set key.path=value` overrides [impl, M]
  - Acceptance: Values override per spec; supports double underscore env paths.
- [ ] Secret providers [impl, M]
  - [ ] `.env`/environment provider [impl, S]
  - [ ] Azure Key Vault provider [impl, M]
  - [ ] AWS Secrets Manager/SSM provider [impl, M]
  - Acceptance: `fmf keys test` resolves logical names; secrets never logged in clear.
- [ ] CLI: `fmf keys test` command [impl, S]

Dependencies: M0

---

## Milestone M2 — Data Connection Layer

- [ ] Define `DataConnector` protocol and common types (`ResourceRef`, `ResourceInfo`) [impl, S]
  - Acceptance: Type signatures stable and documented.
- [ ] Local connector [impl, S]
  - Acceptance: Glob include/exclude; returns correct metadata; streaming reads.
- [ ] S3 connector (boto3) [impl, M]
  - Acceptance: List by prefix/pattern; stream get; SSE/KMS options; pagination.
- [ ] SharePoint connector [impl, L]
  - Acceptance: List/download from site/drive/path; auth via MSAL/Graph; handles throttling.
- [ ] CLI: `fmf connect ls <name> --select "glob"` [impl, S]
- [ ] Contract tests with temp dirs and moto/localstack for S3 [tests, M]

Dependencies: M1

---

## Milestone M3 — Data Processing Layer

- [ ] Core dataclasses: `Document`, `Chunk`, `Blob` [impl, S]
- [ ] File type detection and loaders: text/markdown/html/csv/xlsx/parquet/png/jpg [impl, L]
- [ ] Text normalization + markdown preservation [impl, S]
- [ ] Table parsing (CSV/XLSX, optional parquet to markdown) [impl, M]
- [ ] OCR integration (tesseract or pluggable) [impl, M]
- [ ] Chunking strategies with overlap and token estimates [impl, M]
- [ ] Persist normalized docs/chunks under `artefacts/<run_id>/` [impl, S]
- [ ] CLI: `fmf process --connector <name> --select "**/*.md"` [impl, S]
- [ ] Unit tests for chunking, parsing, loaders [tests, M]

Dependencies: M2

---

## Milestone M4 — Inference Layer

- [ ] Unified message/types and `LLMClient` protocol [impl, S]
- [ ] Azure OpenAI adapter [impl, M]
  - Acceptance: `complete()` works with system/user/assistant messages; supports temperature/max_tokens.
- [ ] AWS Bedrock adapter [impl, M]
  - Acceptance: `complete()` works for selected model; error mapping to `InferenceError`.
- [ ] Retries, backoff, rate limiting [impl, S]
- [ ] Optional streaming callbacks [impl, S]
- [ ] Cost accounting (tokens/estimates when available) [impl, S]
- [ ] CLI: `fmf infer --prompt <id>#<v> --input file.txt` [impl, S]

Dependencies: M1

---

## Milestone M5 — Chain Runner

- [ ] Chain YAML schema and loader (`chains/*.yaml`) [impl, S]
- [ ] Step executor with variable interpolation (`${chunk.text}`, `${all.*}`) [impl, M]
- [ ] Concurrency controls; per-step params; error handling strategy [impl, M]
- [ ] Write `run.yaml` with metrics and prompt lineage [impl, S]
- [ ] CLI: `fmf run --chain chains/sample.yaml` [impl, S]
- [ ] E2E sample chain on local data (no network) [tests, S]

Dependencies: M3, M4, M7 (for export integration in outputs)

---

## Milestone M6 — Prompt Versioning

- [ ] YAML prompt registry with index and versions [impl, M]
- [ ] Content hashing and reference by `id#version` [impl, S]
- [ ] Validation + optional prompt tests [impl, S]
- [ ] Link used prompt versions into `run.yaml` [impl, S]
- [ ] CLI: `fmf prompt register <file>#<version>` [impl, S]

Dependencies: M0

---

## Milestone M7 — Data Export Layer

- [ ] Define `Exporter` protocol and `ExportError` taxonomy [impl, S]
- [ ] S3 exporter (JSONL, CSV, Parquet; compression, partitioning) [impl, M]
  - Acceptance: Appends to `s3://bucket/prefix/${run_id}/...`; idempotent on reruns.
- [ ] SharePoint Excel exporter (append/upsert) [impl, L]
  - Acceptance: Creates workbook/sheet if missing; upsert by key fields.
- [ ] DynamoDB exporter (BatchWrite/TransactWrite) [impl, M]
  - Acceptance: Capacity-aware retries; upsert by keys.
- [ ] Redshift exporter (COPY/UNLOAD + MERGE) [impl, L]
  - Acceptance: Stages to S3; merges by `key_fields`; transactional per batch.
- [ ] Delta exporter (S3 via delta-rs) [impl, L]
  - Acceptance: Appends/Upserts using Delta protocol; document limitations for Lambda.
- [ ] Fabric Delta exporter (Lakehouse) [impl, L]
- [ ] Chain outputs integration: `outputs: - export: <sink>` [impl, S]
- [ ] CLI: `fmf export --sink <name> --input artefacts/<run_id>/outputs.jsonl` [impl, S]
- [ ] localstack tests for S3/DynamoDB; smoke tests for Excel/Redshift (conditional) [tests, L]

Dependencies: M1

---

## Milestone M8 — Observability & Artefacts

- [ ] Structured logs; redaction for secrets [impl, S]
- [ ] Basic metrics: docs, chunks, tokens, retries, cost [impl, S]
- [ ] Optional OpenTelemetry tracing spans [impl, M]
- [ ] Artefact index and retention policy config [impl, S]

Dependencies: M0–M7

---

## Milestone M9 — Deployment Profiles & Ops

- [ ] Profiles in config: `local`, `aws_lambda`, `aws_batch` [impl, S]
- [ ] Lambda container image build (Dockerfile) and packaging notes [ops, M]
- [ ] Lambda runtime constraints (use `/tmp`, S3 artefacts, timeouts/retries) [docs, S]
- [ ] Batch job container with CLI entrypoint and IAM guidance [ops, M]
- [ ] IAM least-privilege policy samples for S3, DynamoDB, Redshift [docs, S]

Dependencies: M1, M7

---

## Milestone M10 — Docs & Examples

- [ ] Example `fmf.yaml` with connectors, processing, inference, export [docs, S]
- [ ] Example `prompts/` and `chains/` including export outputs [docs, S]
- [ ] README update linking AGENTS.md and BUILD_PLAN.md [docs, XS]

Dependencies: M1–M7

---

## Milestone M11 — Quality, Security, Release

- [ ] Add linting/formatting (ruff/black) and pre-commit [impl, S]
- [ ] Unit/E2E coverage targets (thresholds, critical paths) [tests, S]
- [ ] Secret scanning (git-secrets/trufflehog) guidance [ops, S]
- [ ] Versioning and changelog strategy (semver) [docs, XS]
- [ ] 0.1.0 release notes and tag [ops, XS]

Dependencies: all prior

---

## Open Questions / Spikes

- [ ] SharePoint SDK choice: Microsoft Graph vs. Office365-REST-Python-Client; auth tradeoffs [spec, S]
- [ ] Delta implementation: delta-rs vs. delta-spark (Lambda constraints) [spec, S]
- [ ] Redshift upsert strategy: COPY to staging + MERGE vs. UPSERT via stored proc [spec, S]
- [ ] OCR engine packaging for Lambda (tesseract layer vs. remote OCR) [spec, S]

---

## Definition of Done (per milestone)

- Features implemented with tests passing locally (and CI if configured)
- Config validated against Pydantic schema; examples runnable
- Logs structured; secrets redacted; errors mapped to taxonomy
- Artefacts written under `artefacts/<run_id>/` (or S3 for Lambda/Batch)
- Docs updated (README/AGENTS.md/examples)

---

## Delivery Order (Recommended Timeline)

1) M0, M1 — Foundations and secrets
2) M2 — Connectors (local, S3) and basic CLI
3) M3 — Processing (text/tables) and chunking
4) M4 — Inference (Azure, Bedrock) single-shot
5) M6 — Prompt registry minimal
6) M5 — Chain runner basic
7) M7 — Exporters (S3 first), wire into chains
8) M8 — Observability and cost tracking
9) M9 — Deployment profiles (Lambda/Batch)
10) M10 — Examples, docs; M11 — QA and release

---

## Issue Seeds (copy/paste as GitHub issues)

- Component: Config & Secrets — Implement Pydantic models and providers
- Component: Connectors — Local and S3 with contract tests
- Component: Connectors — SharePoint client integration
- Component: Processing — Loaders + chunking + OCR
- Component: Inference — Azure OpenAI adapter
- Component: Inference — AWS Bedrock adapter
- Component: Chains — YAML execution engine with interpolation
- Component: Prompts — YAML registry with versions
- Component: Export — S3 exporter with JSONL/Parquet
- Component: Export — SharePoint Excel exporter
- Component: Export — DynamoDB exporter
- Component: Export — Redshift staging + merge
- Component: Export — Delta/Fabric exporters
- Component: Observability — Logging, metrics, tracing
- Component: Deployment — Lambda/Batch profiles and packaging

---

## Acceptance Criteria Templates

- Functionality: “Given config X, when I run command Y, then artefact/export Z exists with schema S and metrics M are present in run.yaml.”
- Reliability: “Transient 429/5xx errors are retried with backoff and eventually succeed or fail with actionable error.”
- Security: “No secret values appear in logs; IAM policies are scoped to required actions only.”
- Performance: “Process N files totaling ≥100MB within T minutes using concurrency C without OOM.”

---

## Risks & Mitigations

- SharePoint API throttling and auth complexity — Mitigate with exponential backoff, small page sizes, and robust token caching.
- Lambda packaging for OCR/Delta — Prefer S3 exports first; make OCR and Delta optional; provide container images.
- Redshift MERGE permissions and locking — Use staging tables and small transactional batches; document IAM and WLM settings.
- Cost variability (LLM tokens) — Add cost tracking and rate limiting; dry-run mode for chains.
