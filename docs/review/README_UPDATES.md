# DX Updates & Contribution Notes

## CLI ergonomics
- `fmf run` now honours `--set key.path=value` overrides, keeping parity with `process`, `infer`, and `connect`.
- `fmf connect list` is available as a human-friendly alias for `connect ls`.
- `fmf keys test` includes richer help text and reiterates that values are redacted; ideal starting point for onboarding scripts.

## Quick profiles for `fmf.yaml`
```yaml
project: frontier-model-framework
run_profile: local
artefacts_dir: artefacts

profiles:
  active: local
  local:
    auth: { provider: env }
    inference:
      provider: azure_openai
      azure_openai:
        endpoint: https://localhost.mock
        deployment: gpt-4o-mini
        api_version: 2024-02-15-preview
  stage:
    artefacts_dir: s3://my-bucket/fmf/stage
    auth: { provider: azure_key_vault, azure_key_vault: { vault_url: https://stage.vault.azure.net/ } }
    export: { default_sink: s3_results }
  prod:
    artefacts_dir: s3://my-bucket/fmf/prod
    auth: { provider: aws_secrets, aws_secrets: { region: us-east-1 } }
    inference:
      provider: aws_bedrock
      aws_bedrock:
        region: us-east-1
        model_id: anthropic.claude-3-haiku-20240307-v1:0
```

Environment overrides:
```bash
# Force prod profile & tweak temperature without editing YAML
env FMF_PROFILE=prod FMF_INFERENCE__AWS_BEDROCK__TEMPERATURE=0.1 fmf run --chain chains/sample.yaml
```

## Adding new platform components

### Connector
1. Create `src/fmf/connectors/<name>.py` inheriting from `fmf.core.interfaces.BaseConnector`.
2. Define a matching `ConnectorSpec` fragment (see `src/fmf/core/interfaces/models.py`).
3. Register the factory in `src/fmf/connectors/__init__.py` and add unit tests with local fixtures under `tests/connectors/test_<name>.py`.

### Inference provider
1. Scaffold under `src/fmf/inference/providers/<provider>/` by copying the template introduced in `template_provider/provider.py`.
2. Implement `_invoke_completion` (and optionally `stream`/`embed`) returning `Completion` objects; leverage `ModelSpec` metadata for validation.
3. Wire provider into `build_llm_client` with config parsing + retry policies, and add contract tests with recorded fixtures.

### Exporter
1. Implement a subclass of `fmf.core.interfaces.BaseExporter` in `src/fmf/exporters/<name>.py`.
2. Map config into an `ExportSpec` instance, ensure `RunContext` (run_id, profile) propagates to destination metadata.
3. Register via `src/fmf/exporters/__init__.py` and extend smoke tests in `tests/test_exporters_smoke.py`.

## Runnable recipe snippets
- `examples/recipes/csv_quickstart.py` (dry-run by default, opt-in execution via `--execute`).
- `examples/recipes/multimodal_walkthrough.py` for image prompts with RAG selectors.

Each script relies on `FMF.from_env` to inherit config/secrets and creates artefacts under `artefacts/` when executed.
