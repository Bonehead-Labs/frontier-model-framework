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

V3-M1 — Programmatic Runner
- [ ] Add run_chain_config(conf: ChainConfig | dict, *, fmf_config_path: str) -> dict
- [ ] Unit test: in-memory chain dict + DummyClient → outputs.jsonl exists; metrics present.

V3-M2 — SDK Skeleton (csv_analyse)
- [ ] Add package src/fmf/sdk/__init__.py, client.py implementing FMF.from_env and csv_analyse
- [ ] CSV row path: build chain dict with inputs.mode: table_rows; step JSON enforcement (id + analysed); outputs save jsonl/csv; leverage run_chain_config
- [ ] Optionally parse outputs.jsonl to return in-memory records
- [ ] Tests:
  - csv_analyse writes artefacts and returns records (DummyClient)
  - honours custom save paths

V3-M3 — SDK: text_files and images_analyse
- [ ] Implement text_files with chunking defaults (by_sentence) and outputs save
- [ ] Implement images_analyse with multimodal step and JSON enforcement optional
- [ ] Tests for both with DummyClient

V3-M4 — CLI Wrappers
- [ ] Add fmf csv analyse subcommand (thin wrapper to FMF.csv_analyse)
- [ ] Add fmf text infer and fmf images analyse wrappers
- [ ] Tests: CLI triggers SDK and prints output paths

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
- Existing: connectors, processing (table_rows), inference, outputs.save/as unchanged — SDK builds on them.

