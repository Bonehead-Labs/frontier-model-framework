# Image Analysis

Analyze images using FMF's fluent SDK or CLI.

## Prerequisites

- FMF installed and configured
- `fmf.yaml` config file with API keys
- Image files (PNG, JPG, JPEG)

## SDK Usage

```python
from fmf.sdk import FMF

# Initialize and configure
fmf = (FMF.from_env("fmf.yaml")
       .with_service("azure_openai")
       .with_rag(enabled=True, pipeline="images")
       .with_response("jsonl"))

# Run image analysis
result = fmf.images_analyse(
    prompt="Describe the content and extract key visual elements from this image",
    select=["data/*.png", "data/*.jpg", "data/*.jpeg"],
    return_records=True
)

# Display results
print(f"Processed {result.records_processed} images")
print(f"Output: {result.primary_output_path}")
```

## CLI Usage

```bash
# Basic image analysis
fmf images --input data/image.png --prompt "Describe the content"

# Process multiple images
fmf images --input "data/*.png" --prompt "Extract visual elements" --output-format jsonl

# With RAG enabled
fmf images --input data/image.png --prompt "Analyze" --rag --rag-pipeline images
```

## Expected Outputs

**JSONL Format:**
```json
{"source": "data/image1.png", "analysis": "A modern office building with glass windows and concrete structure", "elements": ["building", "glass", "concrete", "modern architecture"]}
{"source": "data/image2.jpg", "analysis": "A person working at a computer desk with multiple monitors", "elements": ["person", "computer", "desk", "monitors"]}
```

**Rich Results:**
- `result.records_processed` - Number of images analyzed
- `result.primary_output_path` - Path to main output file
- `result.jsonl_path` - Path to JSONL output (if generated)
- `result.json_path` - Path to JSON output (if generated)
- `result.duration_ms` - Processing time in milliseconds
- `result.success` - Whether the operation succeeded

## Example Script

See `examples/images_analyse.py` for a complete working example.
