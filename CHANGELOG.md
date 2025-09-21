# Changelog

## [0.3.0] - 2025-09-21
- Added provider-agnostic inference modes (`auto`/`regular`/`stream`) and centralised execution via `invoke_with_mode`.
- Exposed streaming capability checks for Azure OpenAI and Bedrock, raising `ProviderError` when `mode=stream` is unsupported.
- Normalised telemetry and run summaries (TTFB, latency, chunk counts, retries, fallback reasons) across CLI/SDK/scripts.
- Simplified orchestrator scripts and CLI entrypoints with a shared `--mode` flag; deprecated the `FMF_EXPERIMENTAL_STREAMING` toggle in favour of `FMF_INFER_MODE`.

## [0.2.0] - 2025-09-21
- Refactored `chain.runner` into helper stages to simplify future pipeline work with no behaviour changes.
- Emitted retry metrics (`retry.attempts`, `retry.failures`, `retry.success`, `retry.sleep_seconds`) and documented observability knobs.
- Added CI security and quality gates (pip-audit, bandit, radon, jscpd) with reusable scripts.
- Increased coverage for tracing, table-row processing, and SDK orchestrators with new targeted unit tests.

## [0.1.0]
- Initial release.
