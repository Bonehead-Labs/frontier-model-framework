# Image Analysis Example

FMF supports multimodal steps. You can send images directly alongside text.

Config (excerpt):

```yaml
connectors:
  - name: local_images
    type: local
    root: ./data
    include: ["**/*.png", "**/*.jpg", "**/*.jpeg"]
```

Multimodal chain with JSON enforcement:

```yaml
# examples/chains/image_analysis.yaml
name: image-analysis
inputs:
  connector: local_images
  select: ["**/*.{png,jpg,jpeg}"]
steps:
  - id: describe
    mode: multimodal
    prompt: |
      inline: Return a JSON object with keys 'objects' and 'colors' describing the image.
    inputs: {}
    output:
      name: analysis
      expects: json
      parse_retries: 1
      schema: { type: object, required: [objects, colors] }
outputs:
  - save: artefacts/${run_id}/image_analysis.jsonl
    from: analysis
    as: jsonl
```

Run the chain:

```
fmf run --chain examples/chains/image_analysis.yaml -c examples/fmf.example.yaml
```

Notes
- Azure and Bedrock adapters map image parts for their respective APIs. Images are attached as data URLs; no OCR is required.
- OCR remains available when you need to extract text from images (install extras: `.[ocr]`).
