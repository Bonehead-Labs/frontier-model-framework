# Deployment Profiles and Notes

## Profiles

Configure profiles in `fmf.yaml` under `profiles` and set the active profile via `profiles.active`, `FMF_PROFILE` env var, or legacy `run_profile`.

Example:

```
profiles:
  local:
    artefacts_dir: artefacts
    auth: { provider: env }
  aws_lambda:
    artefacts_dir: s3://my-bucket/fmf/artefacts
    auth: { provider: aws_secrets }
    export: { default_sink: s3_results }
  aws_batch:
    artefacts_dir: s3://my-bucket/fmf/artefacts
    export: { default_sink: redshift_analytics }
```

## AWS Lambda

- Container image: see `docker/Dockerfile.lambda`
- Python: 3.12 runtime.
- Writable disk: only `/tmp` is writable; set `artefacts_dir` to S3 in the `aws_lambda` profile.
- Timeouts/retries: configure Lambda function timeouts; FMF clients implement retries with backoff; tune via environment and profile.
- Secrets: use AWS Secrets Manager/SSM via IAM role.
- Observability: JSON logs to CloudWatch; optional OpenTelemetry can be added.

## AWS Batch

- Container: see `docker/Dockerfile.batch` (installs FMF with AWS/Redshift/Delta/Excel extras).
- Entrypoint: FMF CLI (`fmf`). Pass job arguments to run chains and exports.
- IAM: use task role for S3, DynamoDB, Redshift access.
- Scale: use compute environments to scale workers.

