# Example 1 – Fabric Comment Summaries

This walkthrough shows exactly what you need to run `scripts/fabric_comments.py` and
produce a Parquet file for the `Test_Table_1` table in Microsoft Fabric.

## 1. Create `fmf.yaml`

1. Copy the example config shipped with the repo:
   ```bash
   cp examples/fmf.example.yaml fmf.yaml
   ```
2. Open `fmf.yaml` and:
   - Update the `auth` section to match your secret source (usually `provider: env`).
   - Set the Azure OpenAI (or preferred provider) settings under `inference:`.
   - Add the connector for your Fabric export (see below).

## 2. Configure the Fabric Connector

Fabric lakehouse tables surface as Delta/Parquet folders in OneLake. Point the
connector to that location (adjust the path for your environment):

```yaml
connectors:
  - name: fabric_comments
    type: local
    root: "C:/Users/<you>/AppData/Local/Microsoft/OneLake/<workspace>/<lakehouse>/Tables/Test_Table_1"
    include: ["**/*.parquet"]
```

If you prefer env overrides instead of editing `fmf.yaml`, set:
```bash
export FMF_CONNECTORS__0__NAME=fabric_comments
export FMF_CONNECTORS__0__TYPE=local
export FMF_CONNECTORS__0__ROOT="C:/Users/<you>/AppData/.../Test_Table_1"
export FMF_CONNECTORS__0__INCLUDE='["**/*.parquet"]'
```
(Adjust for Windows `set` syntax if necessary.)

## 3. Provider Credentials

Set the keys your provider requires. For Azure OpenAI:
```bash
export AZURE_OPENAI_API_KEY="<your-key>"
export FMF_INFERENCE__AZURE_OPENAI__ENDPOINT="https://<resource>.openai.azure.com/"
export FMF_INFERENCE__AZURE_OPENAI__DEPLOYMENT="<deployment-name>"
export FMF_INFERENCE__AZURE_OPENAI__API_VERSION="2024-02-15-preview"
```

If you use a different provider, update `fmf.yaml` accordingly.

## 4. Output Folder

Ensure the local directory exists before running the script:
```bash
mkdir -p "C:/Documents/Test_Folder"
```

## 5. Install Dependencies

Activate your environment and install FMF with extras that include Parquet support
(`pyarrow` comes with the `delta` extra):
```bash
uv venv
source .venv/bin/activate
uv sync -E azure -E delta
```

## 6. Run the Recipe

Execute the helper script (optional flags shown):
```bash
python scripts/fabric_comments.py -c fmf.yaml --json
```

Results:
- Parquet file written to `C:/Documents/Test_Folder/comments_summary.parquet`.
- Standard FMF artefacts under `artefacts/<run_id>/` for auditability.

Troubleshooting:
- `fmf keys test` helps verify secrets (`uv run fmf keys test AZURE_OPENAI_API_KEY -c fmf.yaml`).
- Use `uv run fmf connect ls fabric_comments --select "**/*.parquet" -c fmf.yaml` to confirm the
  connector sees your exported table files.
