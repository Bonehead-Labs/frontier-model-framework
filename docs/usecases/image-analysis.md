# Image Analysis Example

Today, FMF does not send images directly to multimodal endpoints. Instead, enable OCR to extract text from images and analyze the extracted text. Full multimodal support is planned (see BUILD_TODOS Milestone R6).

Enable OCR in your config (requires extras: .[ocr]):

```yaml
# fmf.yaml (excerpt)
processing:
  images:
    ocr: { enabled: true, lang: eng }

connectors:
  - name: local_images
    type: local
    root: ./data
    include: ["**/*.png", "**/*.jpg", "**/*.jpeg"]
```

Run a simple chain that summarizes OCR’d text:

```yaml
# chain.yaml
name: image-ocr-summary
inputs: { connector: local_images, select: ["**/*.*"] }
steps:
  - id: summarize_ocr
    prompt: "inline: Summarize any text found in the image:\n{{ text }}"
    inputs: { text: "${chunk.text}" }
    output: ocr_summary
outputs:
  - export: s3_results
```

Python example using FMF loaders + adapters:

```python
import json
from fmf.inference.unified import build_llm_client
from fmf.inference.base_client import Message
from fmf.processing.loaders import load_document_from_bytes

# Build LLM client (Azure example)
client = build_llm_client({
    "provider": "azure_openai",
    "azure_openai": {
        "endpoint": "https://<resource>.openai.azure.com/",
        "api_version": "2024-02-15-preview",
        "deployment": "gpt-4o-mini",
    },
})

# OCR the image via FMF loader
with open("example.png", "rb") as f:
    data = f.read()
doc = load_document_from_bytes(
    source_uri="file://example.png",
    filename="example.png",
    data=data,
    processing_cfg={"images": {"ocr": {"enabled": True, "lang": "eng"}}},
)

ocr_text = doc.text or ""
prompt = (
    "Return a JSON object with keys 'text_summary' and 'notes'.\n"
    f"Image OCR text:\n{ocr_text}\n"
)
comp = client.complete([Message(role="user", content=prompt)])
try:
    result = json.loads(comp.text)
except json.JSONDecodeError:
    result = {"parse_error": True, "raw_text": comp.text}
# `result` can be written to JSONL or exported via S3 exporter
```

Notes
- Multimodal payloads and JSON schema enforcement are on the roadmap. For now, instruct the model to emit JSON and parse with fallback.
- Ensure `pytesseract` and `Pillow` are installed (use extras: `.[ocr]`).
