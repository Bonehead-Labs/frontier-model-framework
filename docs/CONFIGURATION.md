# FMF Configuration Guide

This guide covers all configuration options for the Frontier Model Framework.

## Quick Start

When using FMF as a package in your project, create `fmf.yaml` in your project root:

```yaml
project: my-project
artefacts_dir: artefacts

auth:
  provider: env
  env:
    file: .env

connectors:
  - name: local_docs
    type: local
    root: ./data
    include: ['**/*.csv', '**/*.txt', '**/*.md']

inference:
  provider: azure_openai
  azure_openai:
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    api_version: 2024-02-15-preview
    deployment: gpt-4o-mini
    temperature: 0.2
    max_tokens: 1024
```

Create `.env` with your credentials (add to `.gitignore`):

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
```

## Configuration File Location

- FMF looks for `fmf.yaml` in your **current working directory** (where you run your script).
- You can specify a custom path: `FMF.from_env("config/my-fmf.yaml")`
- The config file is **not** bundled with the FMF package—you must create it in your project.

## Authentication (`auth`)

### Environment Variables (`.env` file)

```yaml
auth:
  provider: env
  env:
    file: .env  # Path relative to working directory
```

Your `.env` file:
```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key

# AWS
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
```

### Azure Key Vault

```yaml
auth:
  provider: azure_key_vault
  azure_key_vault:
    vault_url: https://your-vault.vault.azure.net/
    tenant_id: your-tenant-id
    client_id: your-app-id
    secret_mapping:
      OPENAI_API_KEY: openai-api-key
```

### AWS Secrets Manager

```yaml
auth:
  provider: aws_secrets
  aws_secrets:
    region: us-east-1
    source: secretsmanager
    secret_mapping:
      BEDROCK_API_KEY: bedrock/api-key
```

## Connectors

### Local Filesystem

```yaml
connectors:
  - name: local_docs
    type: local
    root: ./data
    include: ['**/*.txt', '**/*.md', '**/*.csv']
    exclude: ['**/.git/**']
```

### AWS S3

```yaml
connectors:
  - name: s3_raw
    type: s3
    bucket: my-bucket
    prefix: raw/
    region: us-east-1
```

### SharePoint

```yaml
connectors:
  - name: sp_docs
    type: sharepoint
    site_url: https://contoso.sharepoint.com/sites/Documents
    drive: Documents
    root_path: Policies/
```

## Inference Providers

### Azure OpenAI

```yaml
inference:
  provider: azure_openai
  azure_openai:
    endpoint: ${AZURE_OPENAI_ENDPOINT}  # From .env
    api_version: 2024-02-15-preview
    deployment: gpt-4o-mini
    temperature: 0.2
    max_tokens: 1024
```

### AWS Bedrock

```yaml
inference:
  provider: aws_bedrock
  aws_bedrock:
    region: us-east-1
    model_id: anthropic.claude-3-haiku-20240307-v1:0
    temperature: 0.2
    max_tokens: 1024
```

## Processing Options

```yaml
processing:
  text:
    normalize_whitespace: true
    preserve_markdown: true
    chunking:
      strategy: recursive
      max_tokens: 1000
      overlap: 150
  tables:
    formats: [csv, xlsx]
    include_sheet_names: true
    to_markdown: true
  images:
    ocr:
      enabled: true
      engine: tesseract
      lang: en
  metadata:
    include_source_path: true
    include_hash: sha256
```

## Export Sinks

### S3

```yaml
export:
  default_sink: s3_results
  sinks:
    - name: s3_results
      type: s3
      bucket: my-bucket
      prefix: fmf/outputs/${run_id}/
      format: jsonl
      compression: gzip
      sse: kms
      kms_key_id: alias/fmf-writes
      mode: append
```

### DynamoDB

```yaml
export:
  sinks:
    - name: dynamodb_events
      type: dynamodb
      table: fmf-events
      region: us-east-1
      key_schema:
        pk: run_id
        sk: record_id
      mode: upsert
```

### SharePoint Excel

```yaml
export:
  sinks:
    - name: sp_excel
      type: sharepoint_excel
      site_url: https://contoso.sharepoint.com/sites/Analytics
      drive: Documents
      file_path: Reports/fmf-output.xlsx
      sheet: Results
      mode: upsert
      key_fields: [source_uri, step_id]
      create_if_missing: true
```

## RAG Pipelines

```yaml
rag:
  pipelines:
    - name: docs_rag
      connector: local_docs
      select: ["**/*.md", "**/*.txt"]
      modalities: ["text"]
      max_text_items: 8
      build_concurrency: 4
```

## Environment Variable Overrides

Override any config value using `FMF_` prefix with double underscores for nesting:

```bash
# Override inference provider
FMF_INFERENCE__PROVIDER=aws_bedrock

# Override temperature
FMF_INFERENCE__AZURE_OPENAI__TEMPERATURE=0.5

# Override connector root
FMF_CONNECTORS__0__ROOT=./other-data
```

## Profiles

Define multiple configurations and switch between them:

```yaml
profiles:
  active: dev  # or set FMF_PROFILE=prod

  dev:
    inference:
      provider: azure_openai
      azure_openai:
        deployment: gpt-4o-mini
        temperature: 0.1

  prod:
    inference:
      provider: aws_bedrock
      aws_bedrock:
        model_id: anthropic.claude-3-sonnet-20240229-v1:0
        temperature: 0.0
```

## Complete Example

See the [FMF repo's `fmf.yaml`](https://github.com/Bonehead-Labs/frontier-model-framework/blob/main/fmf.yaml) for a full working example with all available options.

## Validation

FMF validates your configuration at load time using Pydantic. If there are errors, you'll see detailed validation messages pointing to the problematic fields.

## Further Reading

- [Usage Examples](./usage/) - SDK and CLI usage patterns
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment patterns
- [IAM Policies](./IAM_POLICIES.md) - AWS permissions for S3/Bedrock/Secrets
