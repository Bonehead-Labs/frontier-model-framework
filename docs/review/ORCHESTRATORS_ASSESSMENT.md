# Orchestrator Scripts Assessment

| Script | Pass? | Notes |
|--------|-------|-------|
| `scripts/analyse_csv.py` | ✅ | Parses flags (`--mode`, `--json`, RAG overrides) and delegates directly to `run_recipe_simple`. No provider logic or artefact walking; LOC 43. |
| `scripts/fabric_comments.py` | ✅ | Thin wrapper around `run_recipe_simple` with optional `--mode`. JSON output only through `RunSummary`. |
| `scripts/images_multi.py` | ✅ | Mirrors CSV orchestrator; no provider-specific branches, streaming handled via summary. |
| `scripts/text_to_json.py` | ✅ | Same pattern; keeps CLI thin and forwards `--mode` to SDK. |

**Common adjustments**
- Added `--mode {auto,regular,stream}` flag to every script.
- Switched to `run_recipe_simple(..., mode=...)` so summaries are produced in a single place.
- No scripts touch artefact directories or emit provider-specific progress; they simply print JSON/one-line summaries.
- All orchestrators remain ≤45 LOC and contain zero `import` statements from provider modules.

