# Testing & Coverage

## Pytest Results
- Command: `PYTHONPATH=src .venv/bin/pytest --cov=src --cov-report=xml --cov-report=term`
- Outcome: **116 passed**, 1 skipped (exporter smoke), coverage report generated.
- Duration: ~7.2 s on sandbox runner.

## Coverage Summary
| Metric | Value |
|--------|-------|
| Overall line coverage | **80%** (3,874 statements, 785 missed) |
| Coverage artefact | [`docs/deepdive/coverage.xml`](coverage.xml) |

### Notable Low-Coverage Areas
| Module | Coverage | Notes |
|--------|----------|-------|
| `src/fmf/sdk/orchestrators.py` | 33% | New helper exercised only indirectly by scripts. Add unit tests for success/error paths. |
| `src/fmf/inference/unified.py` | 28% | Legacy compatibility layer; consider pruning or adding contract tests. |
| `src/fmf/processing/table_rows.py` | 55% | Complex CSV/XLSX row handling; bolster tests for header offsets & pass-through columns. |
| `src/fmf/observability/tracing.py` | 59% | Lacks OTEL span tests; mock tracer to cover span contexts. |
| `src/fmf/sdk/client.py` | 63% | Many recipe branches untested; add table/image workflows to SDK unit tests. |

### Execution Constraints
- Network-dependent exporters/inference already mocked; suite runs offline.
- Recommend adding targeted tests around retries, streaming adapters, and CLI JSON summary flag.

