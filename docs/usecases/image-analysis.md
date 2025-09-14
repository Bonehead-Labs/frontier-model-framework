# Image Analysis Example

This example demonstrates analysing images with a multimodal LLM and enforcing a JSON response using a YAML-defined schema.

```yaml
# chain.yaml
steps:
  - id: describe
    prompt: inline: |
      You are a vision model. Return a JSON object with `objects` and `colors`.
    mode: multimodal
    images: ${doc.blobs}
    expects_json: true
    json_schema:
      type: object
      properties:
        objects:
          type: array
          items: {type: string}
        colors:
          type: array
          items: {type: string}
      required: [objects, colors]
    parse_retries: 1
outputs:
  - export: s3_results
    as: parquet
```

```python
import base64
import json
from fmf.inference.unified import build_llm_client
from fmf.inference.base_client import Message

client = build_llm_client({"provider": "azure_openai", "model": "gpt-4o"})

with open("example.png", "rb") as f:
    img = base64.b64encode(f.read()).decode("utf-8")

messages = [
    Message(role="user", content=[
        {"type": "text", "text": "List objects and dominant colors"},
        {"type": "image_base64", "data": img},
    ])
]

comp = client.complete(messages)
result = json.loads(comp.text)
# `result` follows the schema and can be written to Parquet or JSONL
```

The schema configuration guards against malformed outputs by retrying once before recording an error.
