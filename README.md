Frontier Model Framework (FMF)
==============================

FMF is a pluggable, provider‑agnostic framework for building LLM‑powered data workflows across Azure OpenAI, AWS Bedrock, and more. It provides unified configuration, connectors, processing, inference adapters, prompt versioning, exports, and a simple CLI for running pipelines end‑to‑end.

Links
-----

- Unified workflow & use-case playbooks: `docs/USAGE.md`
- Architecture and conventions: `AGENTS.md`
- Build plan and milestone tracking: `docs/BUILD_PLAN.md`
- Deployment notes and IAM examples: `docs/DEPLOYMENT.md`, `docs/IAM_POLICIES.md`
- Examples: `examples/`

Features
--------

- YAML‑first configuration with env/CLI overrides and profiles
- Data connectors (local, S3, SharePoint/Graph) with streaming reads
- Processing: normalization, tables → Markdown, optional OCR, chunking
- Inference adapters: Azure OpenAI and Bedrock, with retries and rate limiting
- Prompt registry with versioning and content hashing
- Exports to S3 and DynamoDB (plus stubs for Excel/Redshift/Delta/Fabric)
- Observability: structured logs with redaction, basic metrics, optional tracing
- Reproducible artefacts and a simple CLI for processing, running chains, and export

Requirements
------------

- Python 3.12+
- uv (package/dependency manager): https://github.com/astral-sh/uv

Getting Started (uv)
--------------------

1) Create and activate an environment and install FMF with extras you need:

```
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync -E aws -E azure     # installs base + selected extras from pyproject
# Alternatively:
# uv pip install -e .[aws,azure]
```

2) Copy and edit the example config, and add some sample Markdown files under `./data`:

```
cp examples/fmf.example.yaml fmf.yaml
```

3) Quickest path — run a recipe (recommended) or use the SDK/CLI helpers:

Recipes (thin scripts)
```
python scripts/analyse_csv.py -r examples/recipes/csv_analyse.yaml -c fmf.yaml
python scripts/images_multi.py -r examples/recipes/images_multi.yaml -c fmf.yaml
python scripts/text_to_json.py -r examples/recipes/text_to_json.yaml -c fmf.yaml
```
Each script is a thin orchestrator around `fmf.run_recipe_simple`; pass `--json` for a compact summary or
forward RAG overrides (`--enable-rag`, `--rag-pipeline`, etc.) when the recipe supports them. Use
`--mode {auto,regular,stream}` to select the inference mode explicitly (defaults to `auto`).

Python SDK
```
from fmf.sdk import FMF
fmf = FMF.from_env("fmf.yaml")
fmf.csv_analyse(input="./data/comments.csv", text_col="Comment", id_col="ID", prompt="Summarise")
```

CLI convenience
```
uv run fmf csv analyse --input ./data/comments.csv --text-col Comment --id-col ID --prompt "Summarise" -c fmf.yaml
```

4) Run the processing and sample chain (via uv):

```
uv run fmf process --connector local_docs --select "**/*.md" -c fmf.yaml
uv run fmf run --chain examples/chains/sample.yaml -c fmf.yaml
```

5) Review artefacts under `artefacts/<run_id>/` (`docs.jsonl`, `chunks.jsonl`, `outputs.jsonl`, `run.yaml`).

CLI Overview
------------

- `fmf keys test [NAMES...]` – verify secrets resolution
- `fmf connect ls <connector> --select "glob"` – list ingestible resources
- `fmf process --connector <name> --select "glob"` – normalize + chunk to artefacts
- `fmf prompt register <file>#<version>` – register prompt version in registry
- `fmf infer --input file.txt [--mode auto|regular|stream]` – single‑shot completion using current provider
- `fmf run --chain chains/sample.yaml` – execute a chain file (end‑to‑end)
- `fmf export --sink <name> --input artefacts/<run_id>/outputs.jsonl` – write results

Repository Layout
-----------------

```
src/fmf/
  auth/           # secret providers (env, Azure KV, AWS)
  chain/          # chain loader + runner
  config/         # YAML loader, overrides, profiles (Pydantic models)
  connectors/     # local, s3, sharepoint (Graph)
  exporters/      # s3, dynamodb, stubs for excel/redshift/delta/fabric
  inference/      # base types + Azure OpenAI + Bedrock adapters
  observability/  # logging, metrics, optional tracing spans
  processing/     # loaders, normalization, tables, OCR, chunking, persist
  prompts/        # YAML prompt registry + hashing

examples/
  fmf.example.yaml          # example configuration
  prompts/summarize.yaml    # example prompt (versioned)
  chains/sample.yaml        # example chain

docs/                       # usage, deployment, IAM samples
docker/                     # Lambda and Batch Dockerfiles
tests/                      # unit and e2e tests
```

Development
-----------

- Install dev deps and extras with uv:

```
uv sync -E aws -E azure -E excel -E redshift -E delta
```

- Run tests:

```
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

- Run CLI via uv (no manual activation required):

```
uv run fmf --help
```

Contributing
------------

- Please read `AGENTS.md` for architecture, extension points, and coding conventions.
- The project follows incremental milestones documented in `BUILD_PLAN.md`.
- Issues and PRs are welcome; keep changes small and focused.
