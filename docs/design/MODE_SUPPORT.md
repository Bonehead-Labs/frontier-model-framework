# Inference Mode Support

This document captures the runtime design for streaming vs regular inference in FMF.

## Mode semantics
- Mode values: `auto` (default), `regular`, `stream`.
- Precedence: environment (`FMF_INFER_MODE`) > explicit mode passed by CLI/SDK/orchestrator > recipe step (`infer.mode`) > default (`auto`).
- `auto` enables streaming when the provider reports capability; otherwise it falls back to regular mode and records `fallback_reason="streaming_unsupported"`.
- `regular` forces non-streaming even if the provider supports it.
- `stream` requires streaming support; FMF raises `ProviderError` when unsupported or when streaming fails before any content is emitted.

## Capability detection & guardrails
- Providers expose `supports_streaming()`; Azure/Bedrock implementations derive this from the configured streaming transport.
- `invoke_with_mode()` centralises capability checks, streaming invocation, and graceful fallback. It calls the provider with `stream=True` only when streaming is enabled.
- Mid-stream errors raise `InferenceError`. In `auto` mode FMF falls back to regular mode and annotates telemetry (`fallback_reason="stream_error:<status>"`). In `stream` mode the error surfaces as `ProviderError` with a remediation hint.
- Bedrock clients without streaming transport behave as streaming-unsupported; this mirrors the IAM requirement for `InvokeModelWithResponseStream`.

## Telemetry & summary contract
- `invoke_with_mode()` returns `(Completion, InferenceTelemetry)` where telemetry includes:
  - `streaming` (bool), `selected_mode` (resolved mode), `fallback_reason` (str | None)
  - `time_to_first_byte_ms`, `latency_ms`, `chunk_count`, `tokens_out`, `retries`
- `chain.runner` aggregates telemetry per step (`step_telemetry`) and at the run level (`metrics`). Aggregated metrics include averages for latency/TTFB, total chunk counts, streaming call counts, and retry totals.
- `run_recipe_simple` and CLI/SDK summaries reuse the same schema: `{ok, run_id, outputs_path, streaming, mode, time_to_first_byte_ms, latency_ms, tokens_out, retries, fallback_reason}`.
- CLI `fmf infer` prints the model output and writes a single summary JSON line to stderr; scripts print `RunSummary.__dict__`, ensuring downstream tooling receives a stable shape regardless of mode.

## Data flow updates
1. Configuration loading captures `FMF_INFER_MODE` once and records it in `RuntimeContext`.
2. `ChainStep` optionally carries `infer_mode`. Environment overrides always win over per-step configuration.
3. `_execute_chain_steps()` swaps direct `client.complete()` calls for `invoke_with_mode()` and accumulates telemetry totals.
4. `_finalize_run()` embeds telemetry in `run.yaml` (`metrics`, `step_telemetry`) for audit and downstream analysis.
5. SDK helpers (`csv_analyse`, `text_files`, `images_analyse`) and orchestrators accept `mode` and stamp `infer: {mode: ...}` into generated chains.

## Failure handling
- Unsupported streaming (`mode=stream` without capability) → `ProviderError` with message `Streaming is not supported by provider ...`.
- Streaming failure in `auto` → fallback to regular mode, telemetry includes `fallback_reason` and `streaming=False`.
- Regular mode is unaffected; tokens and latency metrics still populate with meaningful values.

