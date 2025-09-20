# Implementation Notes

- Streaming support now honours `FMF_EXPERIMENTAL_STREAMING`; when enabled, Azure and Bedrock adapters consume chunk events and invoke `on_token` per provider delta. Without the flag, they still emit a single chunk (no space-splitting). New tests cover both paths.
- Connectors inherit the shared `BaseConnector`, gaining optional `RunContext` plumbing and resilient retries. S3 uses exponential backoff with jitter and returns context-managed bodies to avoid leaking sockets. SharePoint retains its Graph client but now exposes selectors/exclude rules.
- Deterministic IDs are derived from content hashes via `fmf.core.ids`. Documents and chunks record provenance metadata (`created_at`, chunk index, length) to aid audit trails.
- YAML configuration gains `experimental` (streaming, OTEL), `processing.hash_algo`, and `retries.max_elapsed_s`
  sections; `load_config` now mirrors these to environment variables so existing code paths remain compatible.
- Provider registry (`fmf.inference.registry`) lets adapters self-register. `build_llm_client` first consults the registry, then falls back to legacy instantiation for compatibility.
- S3 exporter respects `write_mode` (`append`/`overwrite`) and uses atomic copy-on-write semantics for overwrites. Upserts are surfaced as TODO via `ExportError`.
- Error handling is centralised in `fmf.core.errors`, giving CLI/SDK a consistent base for mapping failures to exit codes.
- Logging remains structured but honours `FMF_OBSERVABILITY_OTEL` before wiring OpenTelemetry spans. Timestamps are now timezone-aware.
- `fmf keys test` prints a quick diagnostics report for connectors/providers/exporters, flagging missing configuration but avoiding destructive calls.
