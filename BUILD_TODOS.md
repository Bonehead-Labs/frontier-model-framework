# Build Plan V2 Todos

Assessment of current capabilities (repo state):

- `processing.loaders` converts CSV/XLSX/Parquet into a single text document (Markdown table when configured). No row-iteration utilities exist.
- `chain.runner` processes text chunks only; no row mode, `${row.*}` variables, or `${all.*}` flattening. It always exports the last step’s results and ignores `outputs[*].from`, `outputs[*].as`, and `outputs[*].save` from chain YAML.
- `exporters.s3` uploads JSONL bytes only. `format` is accepted but not honored beyond a `.jsonl` extension; no CSV/Parquet writers.
- `exporters.dynamodb` expects iterable dict records; current CLI `export` always passes raw bytes (JSONL), so DynamoDB can’t be used via CLI without extra parsing.
- `inference.base_client.Message` is text-only; multimodal content (images) not supported despite `Document.blobs` existing.
- No JSON output enforcement or schema validation in the runner.

These gaps map to the following prioritized milestones and tasks:

## Milestone R1 — Chain Outputs Parity (save/from/as)
- [ ] Implement chain outputs semantics in runner:
  - Respect `outputs[*].from` to select which step output to persist/export.
  - Support `outputs[*].save` to write to a path (with `${run_id}` interpolation) alongside `outputs.jsonl`.
  - Support `outputs[*].as` values: `jsonl` (default), `csv`, `parquet` (serialize selected output accordingly).
- [ ] Update `artefacts/<run_id>/` to include the saved file with correct extension and add its path to `run.yaml`.
- [ ] Docs: update example chain to demonstrate `save/from/as` working; note current defaults and limitations.

## Milestone R2 — Row Mode & Table Workflows
- [ ] Add table row iterator utility in processing (CSV/XLSX/Parquet) with options:
  - `text_column` (string concatenation or render subset of columns)
  - `pass_through` (list of columns echoed into `${row.<col>}`)
- [ ] Extend chain inputs to enable row mode (e.g., `inputs: { connector: ..., select: [...], mode: table_rows, table: { text_column: ..., pass_through: [...] } }`).
- [ ] Update runner to generate per-row contexts and `${row.*}` templating; produce one output per row.
- [ ] Ensure row-mode artefacts are persisted deterministically (docs, rows) and integrate with R1 `save/from/as`.
- [ ] Docs + example: CSV → per-row JSONL and Parquet export.

## Milestone R3 — JSON Output Enforcement
- [ ] Step-level post-processing config (extend chain schema):
  - `output: { expects: json, schema: <json-schema>, parse_retries: 1-2 }`.
- [ ] Implement robust JSON parse/repair with retries; on failure, record `{parse_error, raw_text}` and continue when `continue_on_error` is true.
- [ ] Track `json_parse_failures` metric and include per-step counts in `run.yaml`.
- [ ] Docs: schema-based example (e.g., sentiment classification) with failure handling.

## Milestone R4 — S3 Export Formats (CSV/Parquet)
- [ ] Extend `exporters.s3` to honor `format: csv|parquet` and `compression`:
  - CSV: accept iterable of dicts or JSONL bytes; normalize and write CSV.
  - Parquet: add optional dependency (`pyarrow`) and write Parquet with schema inference.
- [ ] Add `pyproject.toml` optional extra for Parquet (e.g., `[project.optional-dependencies].parquet = ["pyarrow>=...<..."]`).
- [ ] Tests: unit coverage for CSV and Parquet write paths (with patched boto3).
- [ ] Docs: note memory considerations and required extras.

## Milestone R5 — CLI Export Ergonomics
- [ ] Teach `fmf export` to parse JSONL input into iterable dicts when a sink requires records (e.g., DynamoDB, SharePoint Excel, Redshift stub), while still passing raw bytes to S3/Delta-type sinks.
- [ ] Auto-detect input format from file extension (`.jsonl`, `.csv`, `.parquet`) and provide `--input-format` override.
- [ ] Validate sink config vs. provided input format and fail fast with actionable errors.

## Milestone R6 — Multimodal Adapters
- [ ] Expand message model to support content parts (text + image). Keep backward compatibility with `content: str`.
- [ ] Update Azure OpenAI and Bedrock adapters to construct multimodal payloads (image URLs or inline base64, depending on provider constraints).
- [ ] Runner: new step `mode: multimodal` that collects images from `Document.blobs` (and optional OCR text) into messages.
- [ ] Example chain: basic image analysis producing structured JSON; document provider limitations and required extras.

## Milestone R7 — Interpolation & Aggregation Quality
- [ ] Implement `${all.*}` flattening and simple joins (e.g., `${join(all.chunk_summary, "\n")}`) to improve aggregation prompts.
- [ ] Sanitize and limit aggregated payload size (cutoff or sampling) to avoid overlong prompts.

Notes on scope alignment
- The config models already advertise features like S3 `format: parquet` and chain `outputs: ...`; the code doesn’t fully implement them yet. R1/R4 bring behavior in line with the declared schema and the examples.
- Exporter stubs (SharePoint Excel, Redshift, Delta, Fabric) are intentionally unimplemented; R5 keeps CLI behavior predictable without attempting to enable those paths.

Acceptance checkpoints (per milestone)
- Functionality is exercised by unit tests where feasible (no live network calls).
- Errors are mapped to existing taxonomy and secrets redacted in logs.
- Artefacts listed in `run.yaml` and index updated as today.

