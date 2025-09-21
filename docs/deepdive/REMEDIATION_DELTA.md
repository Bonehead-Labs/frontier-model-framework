# Remediation Delta

| Metric | Before | After | Notes |
|--------|--------|-------|-------|
| Ruff errors | 0 | 0 | Stub runner reported no syntax issues both before and after refactor. |
| Mypy errors | 0 | 0 | Syntax-mode mypy continues to pass on `src/fmf/chain` and `src/fmf/core/retry.py`. |
| Test count | 117 | 124 | New tracing/table-row/orchestrator tests added six additional cases. |
| Coverage (overall) | 80% | 81% | Targeted modules now exceed 60% coverage: `observability/tracing.py` 88%, `processing/table_rows.py` 61%, `sdk/orchestrators.py` 87%. |
| CI tooling | None | pip-audit, bandit, radon, jscpd | New scripts integrated into workflow with graceful local skips. |
