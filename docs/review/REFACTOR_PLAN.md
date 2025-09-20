# Refactor Plan (2 sprint outlook)

1. **Codify configuration models (Sprint 1)**  
   - *Acceptance criteria:* `load_config` returns fully-typed Pydantic models for connectors, processing, inference, export, and prompts. Legacy dict paths covered by compatibility shims. Unit tests verify env/--set precedence and profile overlays using the new models.
2. **Connector resilience pass (Sprint 1)**  
   - *Acceptance criteria:* Local/S3/SharePoint connectors inherit from `BaseConnector`, honour `RunContext`, and share retry/backoff + timeout policies. Streaming reads expose context managers that ensure closure; contract tests cover throttling scenarios.
3. **Processing pipeline hardening (Sprint 1-2)**  
   - *Acceptance criteria:* Processing outputs deterministic IDs (hash of `source_uri+offset`), large files are chunked lazily, and artefacts reuse `DocumentModel`/`ChunkModel`. CLI `process` reuses the same pipeline implementation as chain runs.
4. **Inference capability matrix (Sprint 2)**  
   - *Acceptance criteria:* `ModelSpec` metadata validated at startup; providers enforce modality/tool support and emit metrics (latency, tokens, retries). Streaming implemented for Azure & Bedrock with integration tests using recorded fixtures.
5. **Exporter idempotency & schema controls (Sprint 2)**  
   - *Acceptance criteria:* All exporters accept `RunContext`, support deterministic key selection, and document schema evolution. Redshift/Delta exporters include merge/upsert smoke tests using localstack/minio or duckdb backends.
6. **DX polish & observability (Sprint 2)**  
   - *Acceptance criteria:* CLI help text audited for consistency, `fmf keys test` surfaces profile and backend information, logs switched to timezone-aware timestamps, and tracing spans wrap connector/inference/export operations with optional OpenTelemetry integration.
