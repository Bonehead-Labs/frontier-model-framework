# Generic Text File Analysis Example

Analysing plain text or markdown files is supported out of the box.
The snippet below runs the sample chain against Markdown files and exports JSONL results.

```bash
fmf run --chain examples/chains/sample.yaml -c examples/fmf.example.yaml
```

Note: the sample chain already declares `inputs.select: ["**/*.md"]`. To target other file types, edit `examples/chains/sample.yaml` or your own chain file.

The same can be invoked from Python:

```python
from fmf.chain.runner import run_chain

run_chain(
    "examples/chains/sample.yaml",
    fmf_config_path="examples/fmf.example.yaml",
)
```

Outputs are written under `artefacts/<run_id>/outputs.jsonl` and may be exported to configured sinks.
