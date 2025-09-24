# Orchestrator Assessment (Scripts)

| Script | LOC | S1 | S2 | S3 | S4 | S5 | S6 | S7 | Total | Notes |
|--------|-----|----|----|----|----|----|----|----|-------|-------|
| scripts/analyse_csv.py | 45 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 | Missing `--quiet/--dry-run`; recipe invocation pattern duplicated verbatim across scripts. |
| scripts/fabric_comments.py | 47 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 3 | Slightly over target LOC due to inline defaults; lacks shared flag parity (`--quiet`/`--dry-run`); duplicated logic. |
| scripts/images_multi.py | 45 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 | Same logic as CSV script; no quiet/dry-run flags. |
| scripts/text_to_json.py | 45 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 | Same duplication/flag gaps as peers. |

**Smell Index**: 9 (sum of totals)  
**Blast Radius (estimated)**: ≥5 files (all four scripts plus shared docs/SDK helpers to de-duplicate).

The scripts are already thin adapters but still violate flag parity and repeat identical orchestration glue that belongs in the SDK helper.
