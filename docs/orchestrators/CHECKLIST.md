# Orchestrator Streamlining Checklist

1. Confirm shared helper API and signature approved.
2. Implement helper with `mode`, `quiet`, `dry_run`, and JSON summary output.
3. Add helper unit tests (regular, stream, auto-fallback, failure).
4. Refactor `scripts/analyse_csv.py` to delegate to helper only.
5. Refactor `scripts/fabric_comments.py` to delegate to helper only.
6. Refactor `scripts/images_multi.py` to delegate to helper only.
7. Refactor `scripts/text_to_json.py` to delegate to helper only.
8. Ensure each script exposes flags: `--recipe`, `--config`, `--mode`, `--json`, `--quiet`, `--dry-run`.
9. Update README and docs/scripts section with unified examples.
10. Add pytest smokes covering `--help` and `--json --dry-run` for every script.
11. Hook smokes into CI workflow.
12. Re-run smell rubric; target total ≤4 with no duplication smell (S5=0) remaining.
13. Capture before/after metrics in docs/orchestrators/CHANGELOG.md.
14. Announce change in CHANGELOG main entry.
15. Verify release notes and version bump align with helper introduction.
