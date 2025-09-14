# Frontier Model Framework — Build Plan V2

This plan turns three priority workflows into actionable requirements, phases, tasks, and acceptance criteria. Scope is minimal, additive, and aligned with current architecture.

Contents
- Overview and Goals
- Workflows and Requirements
- Current Coverage vs Gaps
- Phased Implementation
- Detailed Tasks by Phase
- Configuration Changes
- CLI and Developer Experience
- Testing Strategy
- Rollout and Validation
- Risks and Mitigations

## Overview and Goals

Primary goal: Enable end-to-end production workflows for (1) per-row tabular inference, (2) image multimodal analysis with structured outputs, and (3) generic text analysis; with reproducible artefacts and simple exports (JSONL/Parquet/S3), keeping changes minimal and pluggable.

Non-goals: Broad refactors, vendor-specific features beyond thin adapters, unrelated exporter backends (unless required by acceptance criteria).

## Workflows and Requirements

### 1) Per-Row Tabular Inference (CSV/Parquet)
- Input: CSV/Parquet via `local` or `s3` connector.
- Selection: `text_column` for LLM input; optional `pass_through` columns and row filtering.
- Prompting: Template can reference `${row.<col>}` and `${row_index}`.
- Execution: Row-wise iteration with concurrency and backoff; prompt versioning recorded.
- Output: Structured dict per row; must include keys to rejoin with source (e.g., `row_index`, pass-through columns).
- Export: Parquet to S3 (partitioned by date optional) and JSONL fallback.
- Observability: Counters for processed/succeeded/failed rows; token/cost accounting; per-row error records.

Acceptance Criteria
- Given CSV with columns `[user_id, survey_id, free_text]` and `text_column: free_text`, pipeline produces `artefacts/<run_id>/outputs.parquet` with `{user_id, survey_id, sentiment, category, rationale}` and writes to `s3://.../fmf/outputs/${run_id}/...` when configured.

### 2) Image Analysis (Multimodal)
- Input: Images (`.png`, `.jpg`) via `local`/`s3` connectors. Optional accompanying text.
- Prompting: YAML-configurable prompts; supports single or multiple prompts per image.
- Multimodal: LLM receives image(s) plus text; no OCR requirement for LLM path. OCR remains optional pre-processing.
- Structured Output: Enforce JSON schema; parse and repair invalid JSON with retry budget.
- Export: JSONL/Parquet with `image_uri`, prompt ids, metrics.

Acceptance Criteria
- Given a folder of PNGs and a step with `json_schema`, chain returns validated JSON per image, logs token metrics, and writes Parquet containing `image_uri` and parsed fields.

### 3) Generic Text File Analysis
- Input: Markdown/Text via `local`/`s3`.
- Processing: Normalize, chunk, run chain, aggregate optional.
- Output/Export: JSONL now; add Parquet option.

Acceptance Criteria
- Running the sample chain over `**/*.md` works as-is and can export Parquet when configured.

## Current Coverage vs Gaps (at a glance)

Covered
- Connectors: `local`, `s3`, `sharepoint`.
- CSV ingest: As a whole-document markdown table (not row-wise).
- Chains: Step execution over text chunks; registry present.
- Inference: Azure OpenAI and Bedrock text adapters; retries/rate limiting.
- Export: S3 JSONL; DynamoDB implemented; stubs for Delta/Redshift/Fabric.

Gaps
- Row-wise iteration for tables; templating against `${row.*}`.
- Parquet export path (and honoring `outputs[*].as: parquet`).
- True multimodal message content and JSON schema enforcement/repair.

## Phased Implementation

Phase 1 — Row Mode + Parquet (Highest Impact)
- Row-wise table iteration and `${row.*}` templating.
- Extend S3 exporter with Parquet support via `pyarrow`.
- Make chain outputs honor `as: parquet|jsonl` and pass structured records to exporters.

Phase 2 — JSON Enforcement
- Add JSON schema validation and repair loop for steps expecting JSON outputs.
- Emit parse errors per item without failing the whole run (configurable behavior).

Phase 3 — Multimodal Adapters
- Extend message model to support image + text content.
- Update Azure and Bedrock adapters to send multimodal payloads.
- Wire runner to assemble multimodal messages from `Document.blobs` or configured image refs.

## Detailed Tasks by Phase

### Phase 1: Row Mode + Parquet
1. Processing: Table Row Iterator
   - Add row-mode in `src/fmf/processing/loaders.py`:
     - New options under `processing.tables`: `row_mode: bool`, `text_column: str`, `pass_through: list[str] = []`.
     - New function to yield row records: `{row_index, values, source_uri, filename}`.
     - Backward compatible: default behavior unchanged when `row_mode` is false/omitted.
2. Chain Runner: Row Execution Path
   - Update `src/fmf/chain/runner.py`:
     - Detect row-mode and build a list of row items instead of a single doc chunk.
     - Expose `${row.<col>}` and `${row_index}` in template interpolation.
     - Collect per-row structured outputs (dict) and write to `outputs.jsonl` (list of dicts).
     - Keep metrics (rows processed, failures, tokens).
3. Output Format: Honor `outputs[*].as`
   - In runner, when exporting, if `as: parquet`, transform in-memory result list to Parquet bytes (or write local Parquet file) and pass to exporter; else use JSONL bytes.
4. S3 Exporter: Parquet Support
   - `src/fmf/exporters/s3.py`:
     - If `format: parquet`, expect dict records or JSONL path and convert using `pyarrow`.
     - Guard import with clear error message suggesting `pip install .[aws] pyarrow` or `uv sync -E aws` plus `pyarrow`.
     - Preserve `compression` semantics (`gzip` not typical for Parquet; ignore or warn when set).
5. Artefacts
   - Persist `outputs.parquet` in `artefacts/<run_id>/` when requested, alongside `outputs.jsonl` for parity (configurable minimalism: by default write only requested format).
6. Docs/Examples
   - Add example chain and config for row-mode CSV → Parquet with Bedrock.

Done When
- CLI run of a sample CSV produces Parquet locally and in S3 (when configured), with correct columns and row counts. JSONL remains supported.

### Phase 2: JSON Enforcement
1. Schema Config
   - Step-level config keys: `expects_json: true`, `json_schema: { … }`, `parse_retries: int`.
2. Runner Parsing Loop
   - After LLM completion, attempt `json.loads`; if fails or schema invalid, run a single repair prompt (or a deterministic cleanup function) up to `parse_retries`.
   - On final failure, record `{parse_error: str, raw_text: str}` fields.
3. Metrics
   - Counters for `json_parse_failures`.
4. Docs/Examples
   - Example: sentiment schema with enums and rationale field.

Done When
- Steps with `expects_json` produce validated dicts or error records; pipeline continues (configurable `continue_on_error`).

### Phase 3: Multimodal Adapters
1. Message Model
   - `src/fmf/inference/base_client.py`: extend `Message` to support `content` as union of `str | list[ContentPart]` where `ContentPart = {type: 'text'|'image_url'|'image_bytes', ...}`; maintain backward compatibility.
2. Azure OpenAI Adapter
   - `src/fmf/inference/azure_openai.py`: map multimodal messages to chat.completions payload for GPT‑4o style models (text+images); add image encoding logic (bytes → base64) as needed.
3. Bedrock Adapter
   - `src/fmf/inference/bedrock.py`: map to Claude 3 message format with images; include system prompt handling.
4. Runner Wiring
   - In `runner.py`, for steps with `mode: multimodal`, collect images from `Document.blobs` (or step `images: ${doc.blobs}`) and construct multimodal messages.
5. Examples/Docs
   - Provide minimal image-analysis chain using `expects_json` + `json_schema`.

Done When
- A folder of images can be processed; completions succeed; JSON schema enforced; Parquet export works.

## Configuration Changes

New/extended keys (backward compatible):
- `processing.tables.row_mode: bool`
- `processing.tables.text_column: str`
- `processing.tables.pass_through: list[str]`
- Step-level: `expects_json: bool`, `json_schema: dict`, `parse_retries: int`, `mode: 'text'|'multimodal'`, `images: var-ref`.
- Export: `export.sinks[*].format: 'jsonl'|'parquet'|'csv'|'delta'` (Parquet now honored).
- Chain outputs: `outputs[*].as: 'jsonl'|'parquet'`.

## CLI and Developer Experience

Commands stay the same; behaviors improve:
- `fmf run --chain chains/row_mode.yaml -c fmf.yaml`
- `fmf export --sink s3_results --input artefacts/<run_id>/outputs.parquet` (supported when Parquet exists)

Dev setup (examples):
- `uv sync -E aws` and install `pyarrow` for Parquet.
- For multimodal testing, ensure adapters are enabled and credentials set.

## Testing Strategy

Unit
- Row iterator from CSV with edge cases (quotes, commas, header rows, empty cells).
- Parquet serialization round-trip with `pyarrow`.
- JSON schema validation and repair paths.

Contract/Integration
- Row-mode chain over small CSV; verify outputs.jsonl/parquet and S3 upload (mock S3 or localstack if available).
- Multimodal: record/replay transport fakes for Azure and Bedrock adapters with image content.

E2E
- Sample chains in `examples/` covering all three workflows; artefacts verified.

## Rollout and Validation

Milestones
- M1: Row mode + Parquet exporter + example and docs.
- M2: JSON enforcement + example and docs.
- M3: Multimodal adapters + example and docs.

Validation
- Each milestone produces a runnable example and artefacts; include acceptance checks scripted in tests.

## Risks and Mitigations

- Parquet dependency size: Keep optional; guard imports; provide JSONL fallback.
- Provider payload drift: Wrap transports; keep strict unit tests with fixtures.
- Performance with large CSVs: Stream rows; bounded concurrency; rate limiter present.
- Schema drift in outputs: Centralize schemas in chain step config; validate and log diffs.

---

Checklist (Quick Reference)
- [ ] Phase 1: Row mode in loaders and runner
- [ ] Phase 1: Honor outputs.as + Parquet in runner
- [ ] Phase 1: S3Exporter Parquet support
- [ ] Phase 1: Examples + docs
- [ ] Phase 2: JSON enforcement (schema + repair) in runner
- [ ] Phase 2: Metrics + examples
- [ ] Phase 3: Multimodal message model
- [ ] Phase 3: Azure + Bedrock multimodal mapping
- [ ] Phase 3: Runner multimodal wiring + examples

