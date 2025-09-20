# FMF Environment Variable Checklist

Copy the keys you need into your `.env` (or export them directly). Leave unused
sections blank if you are not using that provider/connector.

## Core / FMF Overrides
- `FMF_PROFILE=`
- `FMF_INFERENCE__PROVIDER=`
- `FMF_CONNECTORS__0__ROOT=` (override Fabric path if desired)

## Azure OpenAI
- `AZURE_OPENAI_API_KEY=`
- `FMF_INFERENCE__AZURE_OPENAI__ENDPOINT=`
- `FMF_INFERENCE__AZURE_OPENAI__DEPLOYMENT=`
- `FMF_INFERENCE__AZURE_OPENAI__API_VERSION=`

## AWS (S3 & Bedrock)
- `AWS_ACCESS_KEY_ID=`
- `AWS_SECRET_ACCESS_KEY=`
- `AWS_SESSION_TOKEN=`           # optional if using temporary creds
- `AWS_REGION=`
- `FMF_INFERENCE__AWS_BEDROCK__REGION=`
- `BEDROCK_API_KEY=`             # optional depending on your auth flow

## SharePoint / Graph (Connectors & Excel Export)
- `FMF_SHAREPOINT__TENANT_ID=`
- `FMF_SHAREPOINT__CLIENT_ID=`
- `FMF_SHAREPOINT__CLIENT_SECRET=`
- `FMF_SHAREPOINT__USERNAME=`    # if using delegated auth
- `FMF_SHAREPOINT__PASSWORD=`    # if using delegated auth

## Optional: Local Secrets File
If you prefer an `.env` file, set in `fmf.yaml`:
```
auth:
  provider: env
  env:
    file: .env
```

Then place the variables above inside that `.env` file.
