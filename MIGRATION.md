# Frontier Model Framework – Migration Notes

## Provider registry adoption
- Providers now self-register via `fmf.inference.registry.register_provider`. Existing code that called
  `fmf.inference.unified.build_llm_client` continues to work, but direct instantiation should migrate to
  registry-based factories. Custom providers can decorate their factory with
  `@register_provider("your-name")`.
- Legacy `inference.unified` retains conditional fallbacks for backward compatibility but will be
  deprecated in favour of registry lookups in a future release.

## S3 exporter write modes
- `ExportSpec.write_mode` replaces the old `mode` attribute; `S3Exporter` now performs atomic overwrite
  by uploading to a temporary key, verifying the checksum (Content-MD5), copying to the final key, and
  deleting the temporary object. Append semantics remain one-object-per-call. Upsert currently raises
  `ExportError` pending merge-manifest support.
- When checksum headers are unavailable, the exporter falls back to verifying object size and the
  `fmf-sha256` metadata recorded on each upload.
- YAML configs may still specify `mode:`; it is mapped to `write_mode` automatically.

## Deterministic IDs & provenance
- Documents and chunks derive identifiers from content hashes (`doc_<hash>`). Regenerated artefacts may
  change IDs compared to pre-follow-up runs; downstream systems should use provenance fields rather than
  UUID suffixes for correlation.
- `processing.hash_algo` controls the hashing algorithm (`blake2b` default, `xxh64` optional). Set via
  YAML or `FMF_HASH_ALGO`. Text normalisation (Unicode NFC, newline canonicalisation) ensures cross-platform
  stability.
- Blob/document namespaces now include MIME type and payload length to minimise collisions.
- `persist_artefacts` writes `manifest.json` summarising document/chunk IDs for run-level idempotency.

## Streaming & CLI updates
- Providers exposing streaming should now yield `TokenChunk` objects to carry metadata while preserving
  backwards-compatible callbacks. Capability is advertised via `supports_streaming()`.
- A unified `invoke_with_mode()` helper routes calls in `regular`, `stream`, or `auto` mode and emits
  telemetry (TTFB, latency, chunk counts, retries). `ProviderError` is raised when callers demand
  streaming but the adapter cannot provide it.
- CLI/SDK/workflow entrypoints accept `--mode {auto,regular,stream}` (or `mode=` in SDK). Environment
  variable `FMF_INFER_MODE` continues to override all other sources.
- Orchestrator scripts remain thin wrappers over recipes and now forward `--mode` to the shared summary
  helper.

## Configuration toggles
- New YAML fields under `experimental`, `processing.hash_algo`, and `retries.max_elapsed_s` continue to
  map to environment variables (`FMF_OBSERVABILITY_OTEL`, `FMF_HASH_ALGO`, `FMF_RETRY_MAX_ELAPSED`).
- Streaming enablement uses `FMF_INFER_MODE` instead of the legacy
  `FMF_EXPERIMENTAL_STREAMING`; remove references to the old name when migrating.

## Error hierarchy & CLI exits
- CLI commands map framework errors to deterministic exit codes (`ConnectorError` => 4, etc.). Scripts
  wrapping `fmf` should adjust to non-zero exit codes instead of string matching.

## Keys diagnostics
- `fmf keys test --json` emits structured diagnostics for secrets, connectors, providers, and exporters.
  Text output is unchanged otherwise.

**Upgrade guidance**
1. Review exporter configurations for `mode:` usage; specify `write_mode: overwrite` where atomic writes are required.
2. Update custom providers to use the registry decorator and ensure streaming generators raise `StopIteration` with the final completion.
3. For pipelines relying on old UUID chunk IDs, refresh downstream keys using the new deterministic `provenance` metadata.
