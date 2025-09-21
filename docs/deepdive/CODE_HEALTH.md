# Code Health Snapshot

## Lint & Typecheck
| Tool | Scope | Result |
|------|-------|--------|
| Ruff (`pyproject` config) | `src/`, `tests/` | ✅ 0 issues (command: `.venv/bin/python -m ruff check src tests`) |
| Mypy (syntax stub mode) | `src/fmf/core`, `src/fmf/inference` | ✅ No errors (`.venv/bin/python -m mypy ...`) |
| Radon / bandit / jscpd | _Not run_ | ❌ Dependencies not available in offline env; recommend adding to CI |

## Largest Python Modules
| Rank | File | LOC |
|------|------|-----|
| 1 | `src/fmf/chain/runner.py` | 880 |
| 2 | `src/fmf/cli.py` | 673 |
| 3 | `src/fmf/sdk/client.py` | 413 |
| 4 | `src/fmf/config/models.py` | 322 |
| 5 | `src/fmf/rag/pipeline.py` | 300 |
| 6 | `src/fmf/exporters/s3.py` | 258 |
| 7 | `src/fmf/auth/providers.py` | 253 |
| 8 | `src/fmf/processing/loaders.py` | 209 |
| 9 | `src/fmf/inference/bedrock.py` | 201 |
| 10 | `src/fmf/connectors/sharepoint.py` | 195 |

> These modules dominate the codebase; consider splitting responsibilities (e.g., `chain.runner` handles config resolution, chunk orchestration, exporter wiring).

## Complexity & Duplication
- **Cyclomatic complexity**: Unable to run `radon` (missing `pip/ensurepip` in sandbox). Suggest enabling radon in CI to track hot functions (likely `chain.runner`’s inner loops and CLI dispatch).
- **Duplication**: `radon raw`/`jscpd` unavailable; manual inspection shows repeated prompt/recipe handling patterns. Consider centralising CLI argument parsing helpers.

## Additional Observations
- Generated helper packages (`src/mypy/__main__.py`, `src/ruff/__main__.py`) provide offline lint/type stubs—ensure they stay aligned with real tool behaviour.
- Tests rely on fixtures under `tests/fixtures/*`; keep synthetic data small to avoid bloating repo.

