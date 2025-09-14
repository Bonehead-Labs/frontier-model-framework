# Per-row Inference Example

This walkthrough iterates through a tabular dataset using `pandas.DataFrame.iterrows` and invokes an LLM on a free-text column. The LLM response is parsed and appended back to the source structure.

```python
import json
import pandas as pd
from fmf.inference.unified import build_llm_client
from fmf.inference.base_client import Message

# Source data
survey = pd.read_csv("survey.csv")

client = build_llm_client({
    "provider": "azure_openai",
    "model": "gpt-4o-mini",
})

records = []
for i, row in survey.iterrows():
    prompt = (
        "Classify the sentiment and topic as JSON with keys 'sentiment' and 'category'.\n"
        f"Response: {row['free_text']}"
    )
    comp = client.complete([Message(role="user", content=prompt)])
    data = json.loads(comp.text)
    records.append({
        "user_id": row["user_id"],
        "survey_id": row["survey_id"],
        **data,
    })

result = pd.DataFrame(records)
# `result` aligns with the original columns and can be joined back or exported
```

This pattern enables row-wise analysis while keeping outputs structured for downstream processing.
