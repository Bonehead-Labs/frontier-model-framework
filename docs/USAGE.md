# FMF Sample Usage

- Install FMF and extras for your providers:

```
pip install -e ".[aws,azure]"
```

- Copy the example config and adjust endpoints/keys:

```
cp examples/fmf.example.yaml fmf.yaml
# Edit fmf.yaml to set inference.azure_openai.endpoint, deployment, and auth provider
```

- Put a couple of Markdown files under `./data` for testing:

```
mkdir -p data
printf "# Doc 1\nHello." > data/doc1.md
printf "# Doc 2\nWorld." > data/doc2.md
```

## Verify Secrets

- If using environment secrets, ensure `OPENAI_API_KEY` is set.
- Test secrets resolution (redacts values):

```
fmf keys test OPENAI_API_KEY -c fmf.yaml
```

## List Input Files

- Check what your connector will ingest:

```
fmf connect ls local_docs --select "**/*.md" -c fmf.yaml
```

## Process Inputs (Normalize + Chunk)

- Run the processing pipeline only:

```
fmf process --connector local_docs --select "**/*.md" -c fmf.yaml
```

- Outputs:
  - `artefacts/<run_id>/docs.jsonl` – normalized documents
  - `artefacts/<run_id>/chunks.jsonl` – token-aware chunks

## Register a Prompt (Optional)

- The example chain references a prompt; you can pre-register:

```
fmf prompt register examples/prompts/summarize.yaml#v1 -c fmf.yaml
```

## Run a Chain (End‑to‑End)

- Executes steps defined in `examples/chains/sample.yaml`:

```
fmf run --chain examples/chains/sample.yaml -c fmf.yaml
```

- Outputs (under `artefacts/<run_id>/`):
  - `docs.jsonl`, `chunks.jsonl`, `outputs.jsonl`, `run.yaml` (includes metrics, prompts used)
- If `export` sinks are configured (e.g., S3), final results are also written there.

## Single‑Shot Inference

- Run an ad‑hoc completion with your current provider:

```
fmf infer --input path/to/text.txt -c fmf.yaml
```

## Exports Only

- Export previously generated outputs to a sink:

```
fmf export --sink s3_results --input artefacts/<run_id>/outputs.jsonl -c fmf.yaml
```

Notes on S3 export formats
- The S3 exporter supports `format: jsonl | csv | parquet` in `export.sinks`.
- For `csv` and `parquet`, if you pass JSONL bytes as input, the exporter parses JSONL into rows first.
- Parquet requires optional dependency `pyarrow` (install extras: `.[parquet]`).
- Exporter serializes all records in-memory before upload; for very large datasets prefer partitioning or streaming to S3 in stages.

## Overrides and Profiles

- Quick overrides via environment (double underscores for nesting):

```
FMF_INFERENCE__AZURE_OPENAI__TEMPERATURE=0.1 fmf run --chain examples/chains/sample.yaml -c fmf.yaml
```

- CLI `--set key.path=value`:

```
fmf run --chain examples/chains/sample.yaml -c fmf.yaml --set inference.azure_openai.max_tokens=512
```

- Activate a profile (e.g., for Lambda/Batch):

```
FMF_PROFILE=aws_lambda fmf run --chain examples/chains/sample.yaml -c fmf.yaml
```

## What To Expect

- Structured logs (JSON by default in non‑TTY) with sensitive keys redacted.
- `run.yaml` includes:
  - `prompts_used` (id, version, content_hash)
  - `metrics` (docs, chunks, tokens, retries, optional cost estimate)
- Artefacts index and optional retention:
  - `artefacts/index.json` tracks recent runs
  - Set `FMF_ARTEFACTS__RETAIN_LAST=N` to prune older runs

## Troubleshooting

- Missing dependencies: install the right extras (`.[aws]`, `.[azure]`, `.[excel]`, etc.).
- Secrets not found: confirm `fmf keys test` and your `auth` provider mapping.
- API throttling: FMF retries with backoff; consider lowering `concurrency` in chains.
- Lambda: write only to `/tmp` locally and use S3 for `artefacts_dir` via the `aws_lambda` profile.
