# Inference Modes

FMF supports both regular and streaming inference across CLI, SDK, and recipes.

## When to use each mode
- `regular`: deterministic, single-response calls. Use when providers charge per request or when streaming adds overhead.
- `stream`: emit tokens as soon as they arrive. Useful for long responses, UI streaming, or early cancellation.
- `auto` (default): choose streaming when supported, otherwise fall back to regular while recording `fallback_reason`.

## CLI examples
```bash
# Single prompt, force streaming
python -m fmf infer --input note.txt --mode stream

# CSV workflow, let FMF detect support
python -m fmf csv analyse --input comments.csv --prompt "Summarise" --mode auto --json
```

All CLI workflows honour `--mode` and also respect `FMF_INFER_MODE` if set:
```bash
export FMF_INFER_MODE=regular
python -m fmf images analyse --prompt "Describe" --json
```
Environment overrides win over CLI/SDK options.

## Recipe YAML
Per-step streaming preference is declared via `infer.mode`:
```yaml
steps:
  - id: draft
    prompt: prompts/draft.yaml#v2
    inputs:
      text: "${chunk.text}"
    output: response
    infer:
      mode: stream
```
If a recipe omits the field, FMF uses the runtime default (auto or `FMF_INFER_MODE`).

## SDK helpers
```python
from fmf.sdk import FMF

fmf = FMF.from_env("fmf.yaml")
fmf.text_files(prompt="Summarise", mode="stream")
```

## Summary & telemetry
Run summaries expose the same shape irrespective of mode:
```json
{
  "ok": true,
  "run_id": "20250921T141903Z",
  "outputs_path": "artefacts/20250921T141903Z/outputs.jsonl",
  "streaming": true,
  "mode": "stream",
  "time_to_first_byte_ms": 180,
  "latency_ms": 620,
  "tokens_out": 128,
  "retries": 0,
  "fallback_reason": null
}
```
Per-step telemetry is persisted in `run.yaml` under `step_telemetry` with call counts, streaming flags, and aggregate timings.

