# Security & Dependency Review

## Dependency Snapshot
- Core dependencies: `pydantic>=2.7,<3`, `pyyaml>=6.0.1,<7`
- Optional extras: AWS (`boto3`), Azure (`azure-identity`, `azure-keyvault-secrets`), SharePoint (`msgraph-sdk`), Delta (`deltalake`), Redshift (`redshift-connector`), OCR (`pytesseract`), Parquet (`pyarrow`), Excel (`openpyxl`), Tests (`pytest`, `pytest-cov`, `moto`).
- Lock file: `uv.lock` (not analysed in this pass).

## Automated Scans
| Tool | Result |
|------|--------|
| `pip-audit` / `safety` | ❌ Not executed (pip/ensurepip unavailable in sandbox). Add to CI in a networked environment. |
| `bandit` | ❌ Not available. Suggest running in CI to catch high-risk patterns (eval/exec, insecure tempfiles). |
| Secret scan | ✅ No obvious AWS keys or private keys (`rg 'AKIA...'`, `rg 'BEGIN RSA'`). |

## Manual Findings
- Secrets are sourced via providers (env, Azure Key Vault, AWS Secrets Manager). `AuthError` redacts values before logging.
- CLI advises running `fmf keys test --json` to validate secrets; ensure outputs stay redacted when new providers added.
- Third-party SDKs (SharePoint, boto3) should be pinned to secure versions—consider adding Dependabot or Renovate.
- Ensure recipes that write to S3/Delta enforce server-side encryption (configurable via exporter options).

## Recommendations
1. Enable dependency vulnerability scanning (pip-audit or safety) in CI once pip availability is restored.
2. Run `bandit -r src` in CI; pay special attention to network/retry modules.
3. Add a lightweight secrets baseline (detect-secrets or trufflehog) to guard against accidental key commits.
4. Document IAM least-privilege policies alongside `docs/DEPLOYMENT.md` for production roll-outs.

