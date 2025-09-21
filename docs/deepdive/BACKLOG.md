# Prioritized Backlog

| Item | Area | Severity | Effort | Owner? | Notes |
|------|------|----------|--------|--------|-------|
| Decompose `chain.runner` into pipeline stages | Runtime Core | P0 | L | TBD | Reduces 880-LOC hotspot, unlocks targeted testing and parallelism. |
| Add pip-audit/bandit/secret scan to CI | Security | P0 | M | TBD | Currently no automated dependency or static analysis coverage. |
| Increase coverage for tracing, table_rows, SDK orchestrator | Testing | P1 | M | TBD | Modules below 60% coverage; add focused unit/integration tests. |
| Introduce radon/jscpd metrics in CI | Quality | P1 | S | TBD | Track complexity/duplication regressions; currently unavailable due to tooling. |
| Package reproducible dev environment (pip-enabled, install docs) | DX | P1 | M | TBD | `.venv` lacks pip; provide bootstrap script or switch to `uv` managed env. |
| Document retry/timeout knobs & collect metrics | Observability | P1 | M | TBD | Surface retry counts, timeouts, and per-step timings in logs/metrics. |
| Publish focused quickstart (config → recipe → outputs) | Documentation | P2 | S | TBD | Simplify onboarding; current `fmf.yaml` example is dense. |
| Evaluate legacy `inference/unified.py` necessity | Architecture | P2 | M | TBD | Low coverage module; consider removal or rewrite with modern provider registry. |
| Add streaming + exporter stress tests | Reliability | P2 | M | TBD | Validate chunk streaming and atomic exporters under load. |
| Expand recipe/script library with tested samples | DX | P2 | M | TBD | Consolidated scripts ready; add official dataset-driven examples for marketing. |

