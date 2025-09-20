# FMF Workflow Guide

This guide consolidates the recommended, repeatable workflow for FMF. Regardless of
provider or modality, every run follows the same layered process:

1. **Connect** – choose a connector (local, S3, SharePoint, etc.) and list the resources
   to ingest.
2. **Process** – normalize inputs into `Document`/`Chunk` artefacts using the processing
   layer (text loaders, table row extraction, multimodal blobs).
3. **Infer** – run a recipe or chain that maps to one of the three primary use cases
   (structured rows, multimodal images, generic text).
4. **Persist** – export results to the desired sink (JSONL/CSV locally or S3/Delta/DynamoDB).

Optional: attach Retrieval-Augmented Generation (RAG) pipelines when a step needs
contextual retrieval.

The CLI, SDK, and helper scripts are thin wrappers over this sequence. The most
maintainable approach is to capture each workflow in a **recipe YAML** which the
scripts use via `FMF.run_recipe(...)`. Direct SDK helpers remain available for rapid
experiments but the recipe+config path keeps runs reproducible.

---

## Core Workflow

### 0. Environment & Install

```bash
uv venv
source .venv/bin/activate
uv sync -E aws -E azure  # install FMF + provider extras
```

```bash
cp examples/fmf.example.yaml fmf.yaml
# Edit fmf.yaml to set auth provider, connectors, inference deployment, exporters.
```

### 1. Connect

- Define connectors in `fmf.yaml` (`connectors:`). Use `fmf connect ls <name>` to
  verify glob patterns and auth.

```bash
uv run fmf connect ls local_docs --select "**/*.md" -c fmf.yaml
```

### 2. Process

- Optionally run processing only to inspect normalized artefacts.

```bash
uv run fmf process --connector local_docs --select "**/*.md" -c fmf.yaml
# artefacts/<run_id>/docs.jsonl, chunks.jsonl
```

### 3. Infer (Recipe or Chain)

- Create/update a recipe in `examples/recipes/`. Recipes identify the connector,
  prompt, and output targets, and can include a `rag:` block.
- Run with CLI helper scripts or directly via SDK.

```bash
python scripts/text_to_json.py --recipe examples/recipes/text_to_json.yaml --enable-rag -c fmf.yaml
# or
uv run fmf run --chain examples/chains/sample.yaml -c fmf.yaml
```

### 4. Persist / Export

- Configure exporters under `export:` in `fmf.yaml`.
- Results from the final step land in `artefacts/<run_id>/outputs.jsonl`. Use
  `fmf export` for additional sinks or rely on chain outputs.

```bash
uv run fmf export --sink s3_results --input artefacts/<run_id>/outputs.jsonl -c fmf.yaml
```

### Operational Notes

- `fmf keys test` verifies secrets before a run.
- Overrides: environment (`FMF_INFERENCE__...`) or CLI `--set key.path=value`.
- Profiles adjust artefact locations for Lambda/Batch.
- `run.yaml` under each artefact directory captures prompts, config hash, metrics, and
  retrieved RAG records for reproducibility.

---

## Entry Points

| Entry point                    | When to use                                         | Command                             |
|--------------------------------|-----------------------------------------------------|-------------------------------------|
| Helper scripts (`scripts/*.py`) | Recommended. Thin wrapper around `run_recipe`.       | `python scripts/analyse_csv.py ...` |
| CLI (`fmf run`, `fmf csv analyse`, etc.) | Interactive or automation without custom scripts. | `uv run fmf csv analyse ...`        |
| SDK direct (`FMF.csv_analyse`) | Rapid prototyping/notebooks.                          | `from fmf.sdk import FMF`           |

All three honour the same recipe/config pipeline; pick the surface that fits your
automation story.

---

## Playbooks by Use Case

Each playbook lists the layered flow (connect → process → infer → persist), the
relevant recipe fields, and concrete commands. Adjust connectors, RAG, and exporters as
required; components are intentionally plug-and-play.

### 1. Structured Row-by-Row Inference (Cloud Ingestion → JSON Output)

**Scenario**: Data lands in S3 (or SharePoint). We run a model against each row and
store structured JSON for downstream services.

1. **Connect** – configure a cloud connector.

```yaml
# fmf.yaml (excerpt)
connectors:
  - name: s3_surveys
    type: s3
    bucket: my-input-bucket
    prefix: surveys/2025/
    region: eu-west-1

export:
  default_sink: s3_results
  sinks:
    - name: s3_results
      type: s3
      bucket: my-output-bucket
      prefix: fmf/runs/${run_id}/
      format: jsonl
      compression: gzip
```

2. **Process** – optional dry run to inspect rows.

```bash
uv run fmf connect ls s3_surveys --select "**/*.csv" -c fmf.yaml
```

3. **Infer** – update `examples/recipes/csv_analyse.yaml`:

```yaml
recipe: csv_analyse
connector: s3_surveys
input: surveys/latest.csv        # resolved relative to connector root
id_col: respondent_id
text_col: free_text
prompt: |
  Return JSON with fields: respondent_id, sentiment, key_points.
save:
  jsonl: artefacts/${run_id}/survey_analysis.jsonl
rag:
  pipeline: knowledge_base
  top_k_text: 3
```

Run the helper script (honours recipe RAG when `--enable-rag` is set):

```bash
python scripts/analyse_csv.py --recipe examples/recipes/csv_analyse.yaml \
    --enable-rag -c fmf.yaml
```

4. **Persist** – chain outputs land locally *and* in S3 via the configured sink. Each
record carries `respondent_id` for joining back to source tables.

### 2. Multimodal Image Analysis (Local Files → Azure OpenAI → JSON Artefacts)

**Scenario**: Inspect product photos, capture objects/colours, store JSON locally.

1. **Connect** – default `local_docs` from `examples/fmf.example.yaml` already scans
   `./data`.

2. **Process** – optional preview of available assets.

```bash
uv run fmf connect ls local_docs --select "**/*.{png,jpg,jpeg}" -c fmf.yaml
```

3. **Infer** – recipe (`examples/recipes/images_multi.yaml`):

```yaml
recipe: images_analyse
connector: local_docs
select: ["products/**/*.png"]
prompt: |
  Describe each image with keys: objects, colors, quality_notes.
expects_json: true
group_size: 3
save:
  jsonl: artefacts/${run_id}/image_descriptions.jsonl
rag:
  pipeline: sample_images   # optional; pulls exemplar shots for reference
  top_k_images: 2
```

Run:

```bash
python scripts/images_multi.py --recipe examples/recipes/images_multi.yaml \
    --enable-rag -c fmf.yaml
```

4. **Persist** – outputs stored under `artefacts/<run_id>/image_descriptions.jsonl` and
summarised in `outputs.jsonl`. Add an S3 exporter if cloud storage is required.

### 3. Fabric SQL → Delta Export → Bedrock Row Inference (Write Back to Delta/S3)

**Scenario**: Execute a Microsoft Fabric SQL query, land the results as Parquet/Delta in
S3, score each row via Bedrock, and persist enriched rows for downstream analytics.

1. **Connect** – point an S3 connector at the exported dataset (Fabric one-click export
   can materialise tables into your data lake).

```yaml
connectors:
  - name: s3_fabric_orders
    type: s3
    bucket: analytics-lake
    prefix: fabric/daily_orders/
    region: eu-west-1

export:
  sinks:
    - name: delta_enriched
      type: delta
      storage: s3
      path: s3://analytics-lake/delta/orders_scored
      mode: upsert
      key_fields: [order_id]
    - name: s3_audit
      type: s3
      bucket: analytics-lake
      prefix: fmf/audit/${run_id}/
      format: jsonl
```

2. **Process** – inspect available objects to confirm partitioning and filenames.

```bash
uv run fmf connect ls s3_fabric_orders --select "**/*.parquet" -c fmf.yaml
```

3. **Infer** – reuse the CSV/table recipe with Bedrock as the provider. Parquet rows are
converted to table records by the processing layer.

```yaml
# recipes/orders_delta.yaml
recipe: csv_analyse
connector: s3_fabric_orders
input: fabric/daily_orders/latest.parquet
id_col: order_id
text_col: customer_notes
prompt: |
  Produce JSON with fields: order_id, risk_flag, follow_up_reason.
save:
  jsonl: artefacts/${run_id}/orders_scored.jsonl
```

Run with the Bedrock profile active (ensures credentials and exporters are aligned):

```bash
FMF_PROFILE=aws_batch \
python scripts/analyse_csv.py --recipe recipes/orders_delta.yaml -c fmf.yaml
```

4. **Persist** – the exporter writes both to Delta (for Fabric/Fabric Lakehouse
consumption) and JSONL audit files in S3, keeping `order_id` for upserts.

---

## Retrieval-Augmented Generation (Optional Layer)

- Declare pipelines in `fmf.yaml` under `rag.pipelines` (e.g., `local_docs_rag`,
  `knowledge_base`). Pipelines reuse connectors and processing rules.
- Attach retrieval per step by adding a `rag:` block in the recipe. Scripts can toggle
  recipe-defined RAG with `--enable-rag`, or replace it via `--rag-pipeline`.
- Artefacts record retrieved passages/images under `artefacts/<run_id>/rag/` to keep
  runs auditable.

---

## Troubleshooting & Ops

- **Secrets**: `uv run fmf keys test OPENAI_API_KEY -c fmf.yaml`
- **Dependencies**: install extras (`uv sync -E aws -E azure -E delta`).
- **Throttling**: lower `chain.concurrency` or increase backoff.
- **Profiles**: `FMF_PROFILE=aws_lambda` switches artefact directories to S3.
- **Artefact hygiene**: set `FMF_ARTEFACTS__RETAIN_LAST=N` to retain only recent runs.

---

## Extending the Playbooks

- Swap connectors (`s3`, `sharepoint`, `local`) without changing recipe structure.
- Change inference provider (`inference.provider`) in `fmf.yaml`; recipes remain the
  same.
- Add exporters (Delta, DynamoDB, SharePoint Excel) to persist enriched data where the
  downstream system expects it.

By committing to this connect → process → infer → persist pattern, FMF stays
approachable while remaining fully extensible.
