# Remediation Notes

## Phase 1 extraction for `chain.runner`
- Split the 880-LOC runner into helper dataclasses/functions (`_prepare_environment`, `_collect_inputs`, `_execute_chain_steps`, `_finalize_run`) to clarify the pipeline without altering behaviour.
- Existing tests continue to exercise the full runner path; helper extraction keeps instrumentation hooks centralised for upcoming refactors.

## Retry instrumentation
- Added metric emission (`retry.attempts`, `retry.failures`, `retry.success`, `retry.sleep_seconds`) in `core.retry`, with per-call labels.
- Documented the new counters in `ROBUSTNESS.md` and `DX.md` so observability dashboards can surface hot spots.

## CI security & quality gates
- Introduced `scripts/ci_security.sh` (pip-audit + bandit) and `scripts/ci_quality.sh` (radon + jscpd) with graceful skips when tooling is absent.
- Wired the scripts into `.github/workflows/ci.yml` alongside npm-backed jscpd installation.

## Coverage uplift
- Extended `tests/test_metrics_and_tracing.py` with an OpenTelemetry shim to drive `trace_span` through the OTEL branch.
- Added table-row edge cases (header dedupe, multi-text columns, invalid header rows) to `tests/test_processing_table_rows.py`.
- New `tests/test_sdk_orchestrators.py` stubs the SDK facade to cover success, failure, and missing-output scenarios.
- Overall coverage now 81% (previous deep-dive baseline: 80%); targeted modules cleared the 60% bar (`tracing.py` 88%, `table_rows.py` 61%, `sdk/orchestrators.py` 87%).

## Artefact hygiene
- All new CI scripts emit verbose skip messages to avoid confusing local contributors without the optional toolchain.

## Tests executed
- `python -m ruff check src tests`
- `python -m mypy src/fmf/chain src/fmf/core/retry.py`
- `python -m pytest --cov=src --cov-report=term --cov-report=xml`
- `./scripts/ci_security.sh`, `./scripts/ci_quality.sh`

## Streaming mode integration
- Added `invoke_with_mode` to centralise streaming vs regular execution, capability checks, and telemetry (TTFB, latency, chunk counts, retries).
- Wired `mode` through `chain.runner`, CLI, SDK, recipes, and orchestrators with a shared summary schema. Unsupported streaming now raises `ProviderError` with a clear remediation hint.
- Persisted per-step telemetry in `run.yaml` (`step_telemetry`) and enriched `RunSummary` so scripts/CLI expose consistent JSON regardless of mode.
- Expanded tests covering streaming fallbacks, chain-level overrides, and SDK/orchestrator summaries; documentation now includes design (`docs/design/MODE_SUPPORT.md`) and user guidance (`docs/usage/MODES.md`).
