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
  backwards-compatible callbacks.
- Global `--quiet` suppresses non-essential CLI output; `--json` semantics are consistent across
  subcommands (e.g., `fmf keys test --json`, `fmf connect ls --json`).
- The orchestration scripts in `scripts/` remain recipe-only wrappers but now share the same
  `--recipe/--config` interface, delegating JSON summaries to a shared SDK helper instead of bespoke logic.

## Configuration toggles
- New YAML fields under `experimental`, `processing.hash_algo`, and `retries.max_elapsed_s` mirror the
  existing environment variables (`FMF_EXPERIMENTAL_STREAMING`, `FMF_OBSERVABILITY_OTEL`, `FMF_HASH_ALGO`,
  `FMF_RETRY_MAX_ELAPSED`). Environment variables continue to take precedence.

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
