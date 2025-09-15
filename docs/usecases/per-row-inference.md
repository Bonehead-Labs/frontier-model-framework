# Per-row Inference Example

This walkthrough shows two ways to do per‑row inference:

1) YAML chain with row‑mode (preferred)

```yaml
# examples/chains/per_row.yaml
name: per-row-csv
inputs:
  connector: local_docs
  select: ["**/*.csv"]
  mode: table_rows
  table: { text_column: message }
steps:
  - id: classify
    prompt: |
      inline: Classify sentiment for the following text:
      {{ text }}
    inputs: { text: "${row.text}" }
    output:
      name: sentiment
      expects: json
      parse_retries: 1
      schema:
        type: object
        required: [sentiment, category]
outputs:
  - save: artefacts/${run_id}/per_row.jsonl
    from: sentiment
    as: jsonl
```

Run it:

```
fmf run --chain examples/chains/per_row.yaml -c examples/fmf.example.yaml
```

2) Lightweight Python harness (direct adapter)

```python
import json
import pandas as pd
from fmf.inference.unified import build_llm_client
from fmf.inference.base_client import Message

# Source data
survey = pd.read_csv("survey.csv")

# Configure your provider (example: Azure OpenAI)
client = build_llm_client({
    "provider": "azure_openai",
    "azure_openai": {
        "endpoint": "https://<resource>.openai.azure.com/",
        "api_version": "2024-02-15-preview",
        "deployment": "gpt-4o-mini",
    },
})

records = []
for _, row in survey.iterrows():
    prompt = (
        "Return JSON with keys 'sentiment' and 'category'.\n"
        f"Text: {row['free_text']}"
    )
    comp = client.complete([Message(role="user", content=prompt)])
    try:
        data = json.loads(comp.text)
    except json.JSONDecodeError:
        data = {"parse_error": True, "raw_text": comp.text}
    records.append({
        "user_id": row.get("user_id"),
        "survey_id": row.get("survey_id"),
        **data,
    })

result = pd.DataFrame(records)
# `result` aligns with the original columns and can be joined back or exported

# Optional: export to S3 via FMF exporter
from fmf.exporters.s3 import S3Exporter
exp = S3Exporter(name="s3_results", bucket="my-bucket", prefix="fmf/outputs/${run_id}/", format="jsonl", compression="gzip")
exp.write(records, context={"run_id": "per-row-demo"})
exp.finalize()
```

Both patterns enable row‑wise analysis. The YAML approach is recommended for reproducibility and exports.
