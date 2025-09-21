# Remediation Plan

| Item | Area | Why now | Files likely | Risk | Test approach |
|------|------|---------|--------------|------|---------------|
| Phase 1 extraction for `chain.runner` | Runtime Core | 880-LOC hotspot flagged as P0; extracting clearly bounded stages lowers cognitive load without behaviour change. | `src/fmf/chain/runner.py` | Low | `python -m ruff check src tests`, `python -m mypy src/fmf/chain`, `pytest --cov` |
| Add pip-audit/bandit/secret scan in CI | Security | Deep-dive SECURITY.md highlights missing automated scanning (P0); ensures regressions caught pre-merge. | `.github/workflows/ci.yml`, new `scripts/ci_security.sh` | Low | CI workflow lint via `act` (if available) or syntax check; local shell lint via `shellcheck` emulation |
| Add radon & jscpd metrics to CI | Quality | CODE_HEALTH backlog (P1,S) to track complexity/duplication; cheap signal for future refactors. | `.github/workflows/ci.yml`, `scripts/ci_quality.sh` | Low | `bash -n scripts/ci_quality.sh`, CI dry-run |
| Raise coverage for tracing/table_rows/SDK orchestrator | Testing | TESTING.md flags <60% coverage; small-focused tests increase safety of future changes. | `tests/test_metrics_and_tracing.py`, `tests/test_processing_table_rows.py`, `tests/test_sdk_orchestrators.py` | Low | `python -m pytest --cov tests/test_metrics_and_tracing.py tests/test_processing_table_rows.py tests/test_sdk_orchestrators.py` |
| Instrument retry metrics & document knobs | Observability | ROBUSTNESS.md notes missing visibility into retry counts/timeouts; instrumentation + docs deliver quick win. | `src/fmf/core/retry.py`, `src/fmf/observability/metrics.py`, `docs/deepdive/ROBUSTNESS.md`, `docs/deepdive/DX.md` | Low | Unit tests for metrics increments; docs lint via `python -m ruff check docs` |
