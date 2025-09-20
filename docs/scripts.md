# Orchestrator Scripts

Each script is a thin wrapper that forwards arguments to the shared SDK helper
`fmf.sdk.run_recipe_simple`, keeping orchestration out of project code.

## analyse_csv.py
```
python scripts/analyse_csv.py -r examples/recipes/csv_analyse.yaml -c fmf.yaml
python scripts/analyse_csv.py -r examples/recipes/csv_analyse.yaml -c fmf.yaml --json
```
Notes: accepts `--enable-rag`, `--rag-pipeline`, `--rag-top-k-text`, `--rag-top-k-images`.

## images_multi.py
```
python scripts/images_multi.py -r examples/recipes/images_multi.yaml -c fmf.yaml
python scripts/images_multi.py -r examples/recipes/images_multi.yaml -c fmf.yaml --json
```
Notes: same RAG flags; emits JSON summary when `--json` is passed.

## text_to_json.py
```
python scripts/text_to_json.py -r examples/recipes/text_to_json.yaml -c fmf.yaml
python scripts/text_to_json.py -r examples/recipes/text_to_json.yaml -c fmf.yaml --json
```
Notes: use `--json` for machine-readable output; other flags passed through to the helper.
