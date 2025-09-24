# Orchestrator Scripts

Each script is a thin wrapper that delegates to the unified FMF CLI,
keeping orchestration out of project code.

## analyse_csv.py
```
python scripts/analyse_csv.py --input data.csv --text-col Comment --id-col ID --prompt "Analyze"
python scripts/analyse_csv.py --input data.csv --text-col Comment --id-col ID --prompt "Analyze" --json
```
Notes: accepts `--enable-rag`, `--rag-pipeline`, `--rag-top-k-text`, `--rag-top-k-images`.

## images_multi.py
```
python scripts/images_multi.py --input "**/*.png" --prompt "Describe this image"
python scripts/images_multi.py --input "**/*.png" --prompt "Describe this image" --json
```
Notes: same RAG flags; emits JSON summary when `--json` is passed.

## text_to_json.py
```
python scripts/text_to_json.py --input "**/*.md" --prompt "Extract key information"
python scripts/text_to_json.py --input "**/*.md" --prompt "Extract key information" --json
```
Notes: use `--json` for machine-readable output; other flags passed through to the helper.

## fabric_comments.py
```
python scripts/fabric_comments.py --input fabric_comments.csv --text-col Comment --id-col ID --prompt "Analyze"
python scripts/fabric_comments.py --input fabric_comments.csv --text-col Comment --id-col ID --prompt "Analyze" --json
```
Notes: supports the same optional RAG overrides.
