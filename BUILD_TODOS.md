# Build Plan V2 Todos

Assessment of current capabilities shows:

- `processing.loaders` reads CSV/Parquet as whole documents; row-wise iteration is absent.
- `chain.runner` operates on text chunks only and lacks row-mode or `${row.*}` templating.
- `exporters.s3` serializes JSONL records only; no Parquet pathway exists.
- `inference.base_client.Message` accepts plain text content; multimodal parts are unsupported.
- No JSON output enforcement or schema validation in the runner.

These gaps map to the following milestones and tasks:

## Milestone M1 – Row Mode & Parquet
- [ ] Implement table row iterator with `text_column` and `pass_through` options.
- [ ] Update runner for row execution, `${row.*}` templating, and structured per-row outputs.
- [ ] Honor `outputs[*].as: parquet` and persist `outputs.parquet` artefacts.
- [ ] Extend `exporters.s3` to upload Parquet via optional `pyarrow`.
- [ ] Provide an example chain and docs for CSV ➜ Parquet.

## Milestone M2 – JSON Enforcement
- [ ] Add step config `expects_json`, `json_schema`, and `parse_retries`.
- [ ] Parse/repair JSON outputs; record `{parse_error, raw_text}` on failure.
- [ ] Track `json_parse_failures` metric.
- [ ] Document a schema-based sentiment example.

## Milestone M3 – Multimodal Adapters
- [ ] Expand message model to accept text and image parts.
- [ ] Update Azure and Bedrock clients to send multimodal payloads.
- [ ] Wire runner for `mode: multimodal` and image collection from `Document.blobs`.
- [ ] Document an image analysis chain producing JSON.

