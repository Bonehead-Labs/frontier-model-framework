from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional


try:  # Optional: Pydantic v2 if available at runtime
    from pydantic import BaseModel, Field
    from pydantic import ConfigDict as _ConfigDict  # type: ignore
except Exception:  # pragma: no cover - exercised when pydantic missing
    BaseModel = object  # type: ignore

    def Field(  # type: ignore
        default: Any = None,
        *,
        description: Optional[str] = None,
        alias: Optional[str] = None,
        default_factory: Any | None = None,
    ) -> Any:
        return default if default_factory is None else default_factory()

    _ConfigDict = dict  # type: ignore


AuthProvider = Literal["env", "azure_key_vault", "aws_secrets"]


class EnvAuth(BaseModel):
    file: Optional[str] = Field(default=None, description="Optional .env file path")

    model_config = _ConfigDict(extra="allow")


class AzureKeyVaultAuth(BaseModel):
    vault_url: str
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    secret_mapping: Dict[str, str] = Field(default_factory=dict)

    model_config = _ConfigDict(extra="allow")


class AwsSecretsAuth(BaseModel):
    region: str
    source: Literal["secretsmanager", "ssm"] = "secretsmanager"
    secret_mapping: Dict[str, str] = Field(default_factory=dict)

    model_config = _ConfigDict(extra="allow")


class AuthConfig(BaseModel):
    provider: AuthProvider
    env: Optional[EnvAuth] = None
    azure_key_vault: Optional[AzureKeyVaultAuth] = None
    aws_secrets: Optional[AwsSecretsAuth] = None

    model_config = _ConfigDict(extra="allow")


# Connectors
ConnectorType = Literal["local", "s3", "sharepoint"]


class BaseConnector(BaseModel):
    name: str
    type: ConnectorType

    model_config = _ConfigDict(extra="allow")


class LocalConnector(BaseConnector):
    type: Literal["local"]
    root: str
    include: List[str] | None = None
    exclude: List[str] | None = None


class S3Connector(BaseConnector):
    type: Literal["s3"]
    bucket: str
    prefix: str | None = None
    region: str | None = None
    kms_required: bool | None = None


class SharePointConnector(BaseConnector):
    type: Literal["sharepoint"]
    site_url: str
    drive: str
    root_path: str | None = None
    auth_profile: str | None = None


# Processing
class ProcessingTextChunking(BaseModel):
    strategy: Literal["recursive", "none"] = "recursive"
    max_tokens: int = 1000
    overlap: int = 150
    splitter: Literal["by_sentence", "by_paragraph", "none"] = "by_sentence"


class ProcessingText(BaseModel):
    normalize_whitespace: bool = True
    preserve_markdown: bool = True
    chunking: ProcessingTextChunking = Field(default_factory=ProcessingTextChunking)


class ProcessingTables(BaseModel):
    formats: List[Literal["csv", "xlsx", "parquet"]] = Field(default_factory=lambda: ["csv", "xlsx"])
    include_sheet_names: bool | None = None
    to_markdown: bool | None = None
    header_row: int | None = None
    treat_as_md_table: bool | None = None


class ProcessingImagesOcr(BaseModel):
    enabled: bool = False
    engine: str | None = None
    lang: str | None = None


class ProcessingImages(BaseModel):
    ocr: ProcessingImagesOcr = Field(default_factory=ProcessingImagesOcr)


class ProcessingMetadata(BaseModel):
    include_source_path: bool | None = None
    include_hash: Literal["sha256", "md5", "none"] | None = None


class ProcessingConfig(BaseModel):
    text: ProcessingText = Field(default_factory=ProcessingText)
    tables: ProcessingTables = Field(default_factory=ProcessingTables)
    images: ProcessingImages = Field(default_factory=ProcessingImages)
    metadata: ProcessingMetadata = Field(default_factory=ProcessingMetadata)
    hash_algo: Optional[Literal["blake2b", "xxh64"]] = None


class ExperimentalConfig(BaseModel):
    streaming: bool = False
    observability_otel: bool = False


class RetriesConfig(BaseModel):
    max_elapsed_s: Optional[float] = Field(default=None, ge=0)


# Inference
InferenceProvider = Literal["azure_openai", "aws_bedrock"]


class AzureOpenAIConfig(BaseModel):
    endpoint: str
    api_version: str
    deployment: str
    temperature: float | None = None
    max_tokens: int | None = None


class AwsBedrockConfig(BaseModel):
    region: str
    model_id: str
    temperature: float | None = None
    max_tokens: int | None = None


class InferenceConfig(BaseModel):
    provider: InferenceProvider
    azure_openai: Optional[AzureOpenAIConfig] = None
    aws_bedrock: Optional[AwsBedrockConfig] = None


# Prompt registry
class PromptRegistryConfig(BaseModel):
    backend: Literal["git_yaml", "local_yaml", "sqlite", "dynamodb", "azure_table"] = "git_yaml"
    path: Optional[str] = None
    index_file: Optional[str] = None


# Export sinks
class S3Sink(BaseModel):
    name: str
    type: Literal["s3"]
    bucket: str
    prefix: Optional[str] = None
    format: Literal["jsonl", "parquet", "csv", "delta"] | None = None
    compression: Literal["none", "gzip", "snappy"] | None = None
    partition_by: List[str] | None = None
    sse: Literal["s3", "kms", "none"] | None = None
    kms_key_id: Optional[str] = None
    mode: Literal["append", "upsert", "overwrite"] = "append"


class SharePointExcelSink(BaseModel):
    name: str
    type: Literal["sharepoint_excel"]
    site_url: str
    drive: str
    file_path: str
    sheet: str
    mode: Literal["append", "upsert", "overwrite"] = "append"
    key_fields: List[str] | None = None
    create_if_missing: bool | None = None


class DynamoDbSink(BaseModel):
    name: str
    type: Literal["dynamodb"]
    table: str
    region: str | None = None
    key_schema: Dict[str, str]
    ttl_attribute: Optional[str] = None
    mode: Literal["append", "upsert", "overwrite"] = "upsert"


class RedshiftSink(BaseModel):
    name: str
    type: Literal["redshift"]
    cluster_id: str
    database: str
    schema: str
    table: str
    unload_staging_s3: str
    copy_options: Dict[str, Any] | None = None
    mode: Literal["append", "upsert", "overwrite"] = "upsert"
    key_fields: List[str] | None = None


class DeltaSink(BaseModel):
    name: str
    type: Literal["delta"]
    storage: Literal["s3", "fabric"] | None = None
    path: str
    mode: Literal["append", "upsert", "overwrite"] = "append"


class FabricDeltaSink(BaseModel):
    name: str
    type: Literal["fabric_delta"]
    workspace: str
    lakehouse: str
    table: str
    mode: Literal["append", "upsert", "overwrite"] = "upsert"


ExportSink = S3Sink | SharePointExcelSink | DynamoDbSink | RedshiftSink | DeltaSink | FabricDeltaSink


class ExportConfig(BaseModel):
    default_sink: Optional[str] = None
    sinks: List[ExportSink] = Field(default_factory=list)


# Run
class RunInputs(BaseModel):
    connector: str
    select: List[str] | None = None


# RAG pipelines
class RagPipelineConfig(BaseModel):
    name: str
    connector: str
    select: Optional[List[str]] = None
    modalities: List[Literal["text", "image", "both"]] = Field(default_factory=lambda: ["text"])
    max_text_items: Optional[int] = None
    max_image_items: Optional[int] = None
    build_concurrency: Optional[int] = None

    model_config = _ConfigDict(extra="allow")


class RagConfig(BaseModel):
    pipelines: List[RagPipelineConfig] = Field(default_factory=list)

    model_config = _ConfigDict(extra="allow")


class RunConfig(BaseModel):
    chain_config: Optional[str] = None
    inputs: Optional[RunInputs] = None


class FmfConfig(BaseModel):
    project: str
    run_profile: str = "default"
    artefacts_dir: str = "artefacts"

    auth: Optional[AuthConfig] = None
    connectors: List[BaseConnector] | None = None
    processing: Optional[ProcessingConfig] = None
    inference: Optional[InferenceConfig] = None
    export: Optional[ExportConfig] = None
    prompt_registry: Optional[PromptRegistryConfig] = None
    run: Optional[RunConfig] = None
    rag: Optional[RagConfig] = None
    experimental: Optional[ExperimentalConfig] = None
    retries: Optional[RetriesConfig] = None

    # allow extra to keep forward-compatible
    model_config = _ConfigDict(extra="allow")


__all__ = [
    "FmfConfig",
    "AuthConfig",
    "EnvAuth",
    "AzureKeyVaultAuth",
    "AwsSecretsAuth",
    "BaseConnector",
    "LocalConnector",
    "S3Connector",
    "SharePointConnector",
    "ProcessingConfig",
    "ExperimentalConfig",
    "RetriesConfig",
    "InferenceConfig",
    "PromptRegistryConfig",
    "ExportConfig",
    "RunConfig",
    "RagConfig",
    "RagPipelineConfig",
]
