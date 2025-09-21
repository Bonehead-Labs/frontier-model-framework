# Developer Experience & Configuration

## Configuration Model
- Primary config: `fmf.yaml`. Key sections: `auth`, `connectors`, `processing`, `inference`, `export`, `prompt_registry`, optional `rag`, and `run` defaults.
- Override hierarchy: CLI `--set key.path=value` > environment variables (`FMF_SECTION__FIELD`) > YAML values.
- Profiles: `profiles` block supports environment-specific overrides (`local`, `aws_lambda`, `aws_batch`). Activate via `FMF_PROFILE` or `--set profiles.active=<name>`.
- Feature toggles:
  - `FMF_EXPERIMENTAL_STREAMING` (enable streaming chunk emission).
  - `processing.hash_algo` & `FMF_HASH_ALGO` for deterministic IDs.
  - Retry tuning through `core/retry` (e.g., `FMF_RETRY_MAX_ELAPSED`).
  - Retry metrics surface via `observability.metrics.get_all()` (`retry.attempts`, `retry.failures`, `retry.success`, `retry.sleep_seconds`), enabling dashboards without extra wiring.

## CLI Ergonomics
| Command | Purpose | Helpful Flags |
|---------|---------|---------------|
| `fmf keys test` | Secret diagnostics | `--json`, `--set`, `-c` |
| `fmf connect ls` | Enumerate connector resources | `--select`, `--json` |
| `fmf process` | Normalise & chunk documents | `--connector`, `--select`, `--set` |
| `fmf run` | Execute chain YAML | `--chain`, `--set`, `--quiet` |
| `fmf recipe run` | Run recipe YAML | `--file`, new `--emit-json-summary` |
| `fmf export` | Ship artefacts to sink | `--input`, `--sink`, `--input-format` |
- Quiet/JSON flags: `--quiet` suppresses info messages; `--json` (per command) delivers machine-friendly output.
- Recipe orchestrators (`scripts/*.py`) use `run_recipe_simple` so downstream teams can benchmark recipes without touching internals.

## SDK Touchpoints
```python
from fmf.sdk import FMF, run_recipe_simple

fmf = FMF.from_env("fmf.yaml")
summary = run_recipe_simple("fmf.yaml", "examples/recipes/csv_analyse.yaml", use_recipe_rag=True)
print(summary.run_id)
```
- SDK convenience methods (e.g., `FMF.csv_analyse`, `FMF.text_files`) still available for custom flows.
- Deterministic IDs and artefact manifests enable reproducible pipelines; encourage teams to version-control recipe YAML alongside prompts.

## Pitfall → Polished Checklist
- [ ] Document minimal `fmf.yaml` for newcomers (current example includes many optional sections).
- [x] Provide thin scripts with shared flag UX (`--recipe`, `--config`, `--json`).
- [ ] Add `uv`/`pip` bootstrap instructions; current `.venv` lacks `pip`, complicating extra tooling installs.
- [ ] Publish CI badges showing lint/type/test coverage to build trust.
- [ ] Package quickstart notebook or markdown linking config → recipe → CLI run for end-to-end orientation.
