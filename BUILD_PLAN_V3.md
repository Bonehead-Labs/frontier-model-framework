# FMF Build Plan V3 — Developer UX First

Purpose
- Maximise developer convenience. A new user should be able to point at their data, choose a prompt, and get results out with 1–2 lines of Python or a single CLI command — without writing YAML or assembling dict chains.
- Preserve existing power‑user paths (YAML chains, connectors, exporters), but make them optional and composable under the hood of a higher‑level SDK.

Product Goals (V3)
- Zero‑to‑first‑result in under 60 seconds, with only a CSV path and a prompt.
- Progressive disclosure: start with a tiny Python/CLI, graduate to YAML chains when needed.
- Opinionated defaults that respect existing config and environment.
- Keep runs reproducible: when SDK is used, still write artefacts and run.yaml unless explicitly disabled.

Primary Workflows (priority)
- CSV rows → per‑row inference → separate joinable outputs (JSONL/CSV) → optional export (S3/DynamoDB).
- Text files → chunk → summarise / classify → save/export.
- Images → multimodal description → save/export.

UX Pillars
1) High‑level Python SDK (fmf.sdk) with simple, typed methods; no chain dicts.
2) High‑level CLI wrappers that mirror the SDK (fmf csv analyse, fmf text infer, fmf images analyse).
3) Smart defaults + auto‑config: use fmf.yaml if present; otherwise infer provider from env; use local connectors automatically.
4) Composable under the hood: SDK internally builds a ChainConfig and calls the runner, so power features remain available.

Current Infrastructure Snapshot (for future agentic work)
- Connectors: local, s3, sharepoint implemented with factories and Pydantic configs.
- Processing:
  - Text normalization and chunking (by_sentence/by_paragraph/none) with token estimates.
  - Table rows: processing.table_rows.iter_table_rows supports CSV/XLSX/Parquet, text_column + pass_through.
  - Persist artefacts: docs.jsonl, chunks.jsonl, outputs.jsonl, run.yaml (plus rows.jsonl for row‑mode).
- Inference:
  - Unified LLM client; Azure OpenAI and AWS Bedrock adapters with retries and rate limiting.
  - Multimodal parts (text+image) supported; adapters map to provider payloads.
  - JSON enforcement in chain steps: expects, schema(required), parse_retries with repair.
- Runner / Chains:
  - YAML chain loader; programmatic runner currently file‑based (run_chain(path)).
  - Variable interpolation including ${row.*}, ${chunk.*}, ${all.*}, and ${join(...)} with size limits.
  - outputs: save/export with as: jsonl/csv/parquet and ${run_id} interpolation.
- Exporters: s3 (jsonl/csv/parquet), dynamodb; stubs for sharepoint_excel/redshift/delta/fabric.
- CLI today: keys, connect ls, process, run, infer, export.
- Tests: broad unit and e2e with DummyClient pattern, patched boto3, etc.

Proposed Components & Changes

1) Programmatic Runner
- Add: run_chain_config(conf: ChainConfig | dict, *, fmf_config_path: str) -> dict
  - Behaviour: accept an in‑memory chain dict or ChainConfig and execute exactly as run_chain.
  - Rationale: remove the need for temp YAML files in scripts; enables the SDK to be thin.

2) Python SDK Facade (new package: src/fmf/sdk/)
- fmf.sdk.FMF
  - classmethod from_env(config_path: str | None = None) -> FMF
    - Loads fmf.yaml when present; otherwise builds a minimal in‑memory config (local connector + defaults) and infers provider from env.
  - csv_analyse(input: str, *, text_col: str, id_col: str, prompt: str,
                save_csv: str | None = None, save_jsonl: str | None = None,
                expects_json: bool = True, parse_retries: int = 1,
                return_records: bool = False) -> list[dict] | None
    - Row‑mode on CSV; returns {id, analysed} records in memory when requested; also writes artefacts + saves outputs per save_csv/save_jsonl.
  - text_files(prompt: str, *, connector: str | None = None, select: list[str] | None = None,
               save_jsonl: str | None = None, save_csv: str | None = None) -> list[dict] | None
    - Chunk + infer for text sources.
  - images_analyse(prompt: str, *, connector: str | None = None, select: list[str] | None = None,
                   save_jsonl: str | None = None) -> list[dict] | None
    - Multimodal path over images; produces JSON results if requested.
- Internals:
  - Build a minimal chain dict with sensible defaults (concurrency, JSON enforcement when asked).
  - Call run_chain_config; optionally rehydrate outputs.jsonl to return_records.
  - Honour artefacts_dir and export settings from loaded config; SDK saves files via chain outputs to avoid duplicating exporter logic.

2.5) ChainBuilder + Recipes (typed, minimal API)
- ChainBuilder: small fluent builder that constructs ChainConfig without dicts:
  - ChainBuilder.csv(input, text_col, id_col).step(prompt, expects_json=True, schema=...).save(csv=..., jsonl=...)
  - ChainBuilder.text(select).step(...).save(...)
  - ChainBuilder.images(select).step(...).save(...)
- Recipes: csv_row_analysis, text_file_summary, image_description call ChainBuilder with best‑practice defaults; SDK methods delegate to recipes.

3) CLI Convenience (wrappers over SDK)
- fmf csv analyse --input comments.csv --text-col Comment --id-col ID --prompt "Summarise"
- fmf text infer --select "**/*.md" --prompt "Summarise"
- fmf images analyse --select "**/*.{png,jpg}" --prompt "Describe"
Notes: These commands only require a connector name when the default local connector cannot see the path; otherwise auto.

4) Optional Output Helpers (non‑blocking)
- In SDK, provide a tiny Outputs helper to get in‑memory records without the caller parsing outputs.jsonl manually (SDK does it).

5) Keep Backwards Compatibility
- Do not remove run_chain or YAML chains. SDK and CLI wrappers are additive.
- The chain runner remains the single orchestrator; the SDK builds and forwards.

4.5) Auto Source Resolution
- Given a path/URL, infer a connector:
  - local: absolute/relative filesystem paths
  - s3: s3://bucket/prefix
  - sharepoint: sharepoint:/sites/... or https URLs where feasible
- Log decisions and allow explicit override (connector=...).
- SDK/CLI auto‑wire connector when unambiguous, eliminating extra flags.

6) Quickstart & Diagnostics
- fmf quickstart: interactive wizard suggesting the right SDK/CLI incantation for CSV/Text/Images; can scaffold a sample chain YAML.
- fmf doctor: validates provider/env, lists visible connectors and what will be used by default, prints missing credentials.

API Sketches

Python
```python
from fmf.sdk import FMF

fmf = FMF.from_env("fmf.yaml")  # or None -> auto config

# CSV per-row analysis -> CSV/JSONL and return in-memory records (optional)
records = fmf.csv_analyse(
    input="./data/comments.csv",
    text_col="Comment",
    id_col="ID",
    prompt="Summarise this comment concisely.",
    save_csv="artefacts/${run_id}/analysis.csv",
    return_records=True,
)
```

CLI
```bash
fmf csv analyse --input ./data/comments.csv --text-col Comment --id-col ID \
  --prompt "Summarise this comment concisely." -c fmf.yaml
```

Milestones & Tasks (V3)

V3-M0 — DX Charter & Guardrails
- [ ] Document “zero‑to‑first‑result” scenarios and make SDK/CLI the default entry point in README and AGENTS.md
- [ ] Add logging conventions for SDK/CLI auto‑detection (provider, connector)
- [ ] Add “no YAML required” pledge for priority workflows (CSV/Text/Images)

V3-M1 — Programmatic Runner
- [x] Add run_chain_config(conf: ChainConfig | dict, *, fmf_config_path: str) -> dict
- [x] Unit test: in-memory chain dict + DummyClient → outputs.jsonl exists; metrics present.

V3-M2 — SDK Skeleton (csv_analyse)
- [x] Add package src/fmf/sdk/__init__.py, client.py implementing FMF.from_env and csv_analyse
- [x] CSV row path: build chain dict with inputs.mode: table_rows; step JSON enforcement (id + analysed); outputs save jsonl/csv; leverage run_chain_config
- [x] Optionally parse outputs.jsonl to return in-memory records
- [x] Tests:
  - csv_analyse writes artefacts and returns records (DummyClient)
  - honours custom save paths

V3-M3 — SDK: text_files and images_analyse
- [x] Implement text_files with chunking defaults (by_sentence) and outputs save
- [x] Implement images_analyse with multimodal step and JSON enforcement optional
- [x] Tests for both with DummyClient

V3-M4 — CLI Wrappers
- [ ] Add fmf csv analyse subcommand (thin wrapper to FMF.csv_analyse)
- [ ] Add fmf text infer and fmf images analyse wrappers
- [ ] Tests: CLI triggers SDK and prints output paths

V3-M4.5 — Auto Source Resolution
- [ ] Implement source auto‑resolution in SDK (path/URL → connector)
- [ ] CLI uses SDK auto‑resolution; add flag to override
- [ ] Tests: local path, s3 URL mapping, ambiguous cases logged

V3-M5 — Docs & Examples
- [ ] README quickstart update: Python SDK and CLI paths
- [ ] Add examples using SDK for CSV/Text/Images
- [ ] USAGE: describe zero‑config behaviour and env/provider auto detection

Non‑Goals (V3)
- No GUI; no breaking changes to existing YAML chain formats.
- No attempt to duplicate exporters in SDK — we keep saving via chain outputs.

Risks & Mitigations
- Risk: Two paths (SDK and YAML) diverge. Mitigation: SDK always builds a chain dict and calls run_chain_config; one orchestrator.
- Risk: Users bypass artefacts with return_records and lose reproducibility. Mitigation: default to writing artefacts; make return_records optional and documented.
- Risk: Too much magic in from_env. Mitigation: log what was auto‑detected (provider, connector) and allow override.

Acceptance Criteria
- “Given a CSV file and valid credentials, when I call FMF.csv_analyse with a prompt, then an analysis.csv and analysis.jsonl are written under artefacts/run_id and I can call return_records=True to get a list of {id, analysed}.”
- “Given no fmf.yaml, FMF.from_env() still runs by auto‑creating a minimal config with a local connector and picks Azure or Bedrock from env vars.”
- “Given text files/images, SDK methods run with <5 lines of code and write the same artefacts as the chain runner.”

Appendix: Backing Changes Summary
- New: run_chain_config in runner
- New: fmf.sdk package (FMF facade)
- New: CLI wrappers for CSV/Text/Images (optional if time‑boxed)
- New: ChainBuilder and Recipes for priority workflows
V3-M6 — Quickstart Wizard & Doctor
- [ ] fmf quickstart wizard (CSV/Text/Images) prints a ready command or Python snippet
- [ ] fmf doctor validates provider/env and prints inferred defaults
- [ ] Tests: non‑interactive modes and basic output
- New: Auto Source Resolution
- New: Quickstart wizard and Doctor diagnostics
- Existing: connectors, processing (table_rows), inference, outputs.save/as unchanged — SDK builds on them.
