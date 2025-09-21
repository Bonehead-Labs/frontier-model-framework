# Reliability, Observability & Performance Review

## Error Handling
- Central taxonomy in `fmf/core/errors.py` (e.g., `ConfigError`, `AuthError`, `ConnectorError`, `ProcessingError`, `InferenceError`, `ExportError`).
- CLI maps domain errors to exit codes via `get_exit_code` (see `cli.py`), ensuring scripting friendliness. Unexpected exceptions fall back to code 1.
- `chain.runner` wraps step execution in try/except, optionally continuing on error when `continue_on_error` is set. Metrics increment for parse failures.
- Recommendation: add structured error reporting (error codes, context IDs) to help correlate with artefact manifests.

## Retries & Timeouts
- `core/retry.py` implements exponential backoff with jitter; connectors/exporters adopt via helper functions.
- `core/retry` now emits metrics (`retry.attempts`, `retry.failures`, `retry.success`, `retry.sleep_seconds`) with per-call labels so dashboards can spot hotspots.
- Inference adapters (Azure, Bedrock) wrap API calls with retry logic and streaming support (gated by `FMF_EXPERIMENTAL_STREAMING`).
- Exporters: S3 performs atomic overwrite by staging + copy; DynamoDB and others implement batch/retry guards.
- Gap: limited visibility into per-provider timeout defaults—document them and surface config override knobs.

## Observability
- Logging: `observability/logging.py` sets structured logging with redaction helper to avoid leaking secrets.
- Metrics: `observability/metrics.py` exposes counters (tokens, retries, parse failures) with lazy init to avoid dependency on Prometheus.
- Tracing: `observability/tracing.py` defines optional OpenTelemetry spans (`trace_span` context manager). Coverage is low (59%); add tests plus docs for enabling OTEL export.
- Artefacts: `processing/persist.py` writes manifests, chunk files, and `run.yaml` capturing prompts, models, metrics.

## Performance Considerations
- Chain execution concurrency limited via `ChainConfig.concurrency` (default 4). Uses `ThreadPoolExecutor` for chunk/table-row processing.
- Connectors stream files via context managers; ensure large table/image workflows rely on iteration instead of loading entire directory contents into memory.
- Inference streaming optional (`FMF_EXPERIMENTAL_STREAMING`). When disabled, entire response buffered—document trade-offs.
- Potential hotspots: `chain.runner` monolithic function; refactor into smaller units to avoid repeated config lookups per chunk.

## Tighten-Up Recommendations
1. **Error context**: include run_id/step_id in raised errors to ease triage; propagate through CLI JSON summary.
2. **Retry instrumentation**: expose retry counters (per connector/provider) via metrics/logs.
3. **Tracing coverage**: provide doc snippet for enabling OTEL exporter; add integration test to avoid regressions.
4. **Chunk pipeline modularisation**: split `chain.runner` into discrete stages (inputs, steps, outputs) to simplify reasoning and future parallelism upgrades.
5. **Performance telemetry**: record per-step timings and token usage in artefacts to highlight slow connectors or expensive prompts.
