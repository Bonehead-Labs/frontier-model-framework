# Changelog

## [0.4.0] - 2025-10-08
- **Credential bootstrap refactor**: Introduced centralized bootstrap utilities in `src/fmf/auth/bootstrap.py`.
 - `.env` is used for AWS bootstrap credentials (ACCESS_KEY/SECRET/TOKEN/REGION) so AWS Secrets Manager can be accessed for app secrets.
 - Unified loading order across SDK and runner: `.env (bootstrap) → auth provider (e.g., aws_secrets) → application secrets (e.g., AZURE_OPENAI_API_KEY)`.
 - Removed duplicated credential logic from `src/fmf/sdk/client.py` and `src/fmf/chain/runner.py`; both now call the shared bootstrap.
 - Added clear debug/info logs for credential steps and Azure API key resolution.
 - `examples/analyse_csv.py` (Local CSV + Azure OpenAI)
 - `examples/analyse_csv_s3_bedrock.py` (S3 CSV + AWS Bedrock)
 - `examples/dataframe_analyse.py` (Pandas DataFrame + Azure OpenAI)
 - `examples/images_analyse.py` (Image groups + multimodal analysis)
 - `examples/text_analysis.py` (Plain text prompts)
 - `examples/secrets_test.py` (AWS Secrets Manager integration)
 - Improved Azure API key resolution via auth provider with environment fallback (`AZURE_OPENAI_API_KEY`/`OPENAI_API_KEY`).
 - Ensured S3 connector and Bedrock client respect environment/bootstrap credentials and region.

## [0.3.0] - 2025-09-21
- Added provider-agnostic inference modes (`auto`/`regular`/`stream`) and centralised execution via `invoke_with_mode`.
- Exposed streaming capability checks for Azure OpenAI and Bedrock, raising `ProviderError` when `mode=stream` is unsupported.
- Normalised telemetry and run summaries (TTFB, latency, chunk counts, retries, fallback reasons) across CLI/SDK/scripts.
- Simplified Orchestrator scripts and CLI entrypoints with a shared `--mode` flag; deprecated the `FMF_EXPERIMENTAL_STREAMING` toggle in favour of `FMF_INFER_MODE`.
## [0.2.0] - 2025-09-21
- Refactored `chain.runner` into helper stages to simplify future pipeline work with no behaviour changes.
- Emitted retry metrics (`retry.attempts`, `retry.failures`, `retry.success`, `retry.sleep_seconds`) and documented observability knobs.
- Added CI security and quality gates (pip-audit, bandit, radon, jscpd) with reusable scripts.
- Increased coverage for tracing, table-row processing, and SDK orchestrators with new targeted unit tests.

## [0.1.0]
- Initial release.
