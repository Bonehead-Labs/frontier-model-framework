# Orchestrator Streamlining Plan

## Milestones (target: 1–2 sprints)

1. **Centralise shared recipe wrapper (Owner: SDK team, 1 sprint)**  
   - Move repeated `run_recipe_simple` argument massaging into a reusable helper (e.g. `fmf.sdk.recipes.run`), returning a stable summary dataclass.  
   - Add optional quiet/dry-run support in the helper so scripts remain flag-thin.  
   - Provide unit tests that cover mode, RAG overrides, and JSON summary contract.

2. **Slim individual scripts (Owner: CLI/tooling, 0.5 sprint)**  
   - Refactor each script to ≤35 LOC by delegating to the new helper.  
   - Ensure standard flags: `-r/--recipe`, `-c/--config`, `--mode`, `--json`, `--quiet`, `--dry-run`.  
   - Verify exit codes propagate directly from helper (no manual branching).

3. **Update SDK/CLI docs and examples (Owner: Docs, 0.5 sprint)**  
   - README + usage guide updates covering the consistent flag set.  
   - Add a scripts section summarising how to run `--json --dry-run` for smoketests.  
   - Link to the helper API in the SDK reference.

4. **Automated smokes & CI hooks (Owner: QA, 0.5 sprint)**  
   - Introduce pytest-based smoke tests invoking each script with `--help` and `--json --dry-run`.  
   - Wire into CI (fast job) to prevent regressions in flag handling or summary schema.

## Risks & Mitigations
- **Helper signature churn**: downstream users might rely on current script behaviour. → Keep helper API additive, maintain backward compatibility in `run_recipe_simple` until scripts migrate.  
- **Flag surface creep**: new flags may diverge again. → Document canonical flag list and add schema validation in the helper.  
- **Test fixture brittleness**: dry-run must avoid touching artefacts. → Implement helper-level dry-run mode that short-circuits before file writes.

## Success Metrics
- Each script ≤35 LOC, smell score ≤1.  
- Shared helper exposes `--quiet/--dry-run` and is reused by all scripts.  
- CI smoke job runs in <5s and validates JSON summary schema.  
- Documentation updated with consistent usage examples and flag table.

## TODO Backlog
- [ ] Design helper signature (`run_recipe_cli(recipe_path, *, config, mode, rag_options, quiet, dry_run)`)
- [ ] Implement helper with summary dataclass + quiet/dry-run support.
- [ ] Write helper unit tests (streaming + regular mode, rag overrides, failure surfaces).
- [ ] Refactor scripts to call helper (remove duplicate JSON printing).  
- [ ] Add argparse flag parity across scripts.
- [ ] Extend README/docs with new usage section.  
- [ ] Add pytest smokes for scripts.  
- [ ] Update CI workflow to run script smokes.  
- [ ] Validate smell rubric post-change (target ≤1 each).  
- [ ] Announce change in CHANGELOG / release notes.
