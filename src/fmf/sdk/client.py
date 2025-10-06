from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Literal

from ..chain.runner import run_chain_config
from ..config.loader import load_config
from ..config.models import InferenceProvider
from ..observability.logging import get_logger, log_config_fingerprint
from .types import RunResult
import yaml as _yaml


def _build_run_result(
    chain_result: Dict[str, Any],
    start_time: float,
    end_time: float,
    method_name: str,
    fmf_instance: "FMF",
    return_records: bool = False,
    save_csv: str | None = None,
    save_jsonl: str | None = None,
    save_json: str | None = None,
) -> RunResult:
    """Build a RunResult object from chain execution results."""
    run_id = chain_result.get("run_id", "unknown")
    run_dir = chain_result.get("run_dir")

    # Count records processed
    records_processed = 0
    if run_dir and os.path.exists(run_dir):
        outputs_path = os.path.join(run_dir, "outputs.jsonl")
        if os.path.exists(outputs_path):
            try:
                with open(outputs_path, 'r', encoding='utf-8') as f:
                    records_processed = sum(1 for _ in f)
            except Exception:
                pass

    # Build output paths
    output_paths = []
    csv_path = None
    jsonl_path = None
    json_path = None

    if run_dir and os.path.exists(run_dir):
        # Check for actual output files
        for filename in os.listdir(run_dir):
            if filename.endswith('.csv'):
                csv_path = os.path.join(run_dir, filename)
                output_paths.append(csv_path)
            elif filename.endswith('.jsonl'):
                jsonl_path = os.path.join(run_dir, filename)
                output_paths.append(jsonl_path)
            elif filename.endswith('.json'):
                json_path = os.path.join(run_dir, filename)
                output_paths.append(json_path)

    # Get configuration info
    effective_config = fmf_instance._get_effective_config()
    service_used = effective_config.get_inference_provider()
    rag_enabled = bool(fmf_instance._rag_override and fmf_instance._rag_override.get("enabled"))
    rag_pipeline = None
    if rag_enabled and fmf_instance._rag_override:
        rag_pipeline = fmf_instance._rag_override.get("pipeline")

    source_connector = fmf_instance._source_connector

    # Load data if requested
    data = None
    if return_records and jsonl_path and os.path.exists(jsonl_path):
        try:
            data = list(_read_jsonl(jsonl_path))
        except Exception:
            pass

    return RunResult(
        success=True,  # If we got here, execution succeeded
        run_id=run_id,
        records_processed=records_processed,
        records_returned=len(data) if data else 0,
        output_paths=output_paths,
        csv_path=csv_path,
        jsonl_path=jsonl_path,
        json_path=json_path,
        start_time=start_time,
        end_time=end_time,
        service_used=service_used,
        rag_enabled=rag_enabled,
        rag_pipeline=rag_pipeline,
        source_connector=source_connector,
        data=data,
        metadata={
            "method": method_name,
            "chain_result": chain_result,
        }
    )


class FMF:
    def __init__(self, *, config_path: Optional[str] = None) -> None:
        self._config_path = config_path or "fmf.yaml"
        self._cfg = None
        self._logger = get_logger("fmf.client")

        try:
            self._cfg = load_config(self._config_path)
            if self._cfg:
                # Log configuration fingerprint (disabled by default - too verbose)
                # config_dict = self._cfg.model_dump() if hasattr(self._cfg, 'model_dump') else self._cfg
                # log_config_fingerprint(config_dict)
                pass
                
                # Load AWS credentials from .env into os.environ early for boto3
                # This ensures S3 connector and other AWS services can access credentials
                self._load_aws_credentials_early()
        except Exception as e:
            self._logger.warning(f"Failed to load config from {self._config_path}: {e}")
            self._cfg = None

        # Fluent API state - these override config values
        self._fluent_overrides: Dict[str, Any] = {}
        self._service_override: Optional[str] = None
        self._rag_override: Optional[Dict[str, Any]] = None
        self._response_format: Optional[str] = None
        self._source_connector: Optional[str] = None
        self._source_kwargs: Dict[str, Any] = {}

    @classmethod
    def from_env(cls, config_path: str | None = None) -> "FMF":
        # If not provided, prefer fmf.yaml in CWD; otherwise allow SDK to run with minimal assumptions
        if config_path is None and os.path.exists("fmf.yaml"):
            config_path = "fmf.yaml"
        return cls(config_path=config_path)

    # --- CSV per-row analysis ---
    def csv_analyse(
        self,
        *,
        input: str,
        text_col: str,
        id_col: str,
        prompt: str,
        save_csv: str | None = None,
        save_jsonl: str | None = None,
        expects_json: bool = True,
        parse_retries: int = 1,
        return_records: bool = False,
        connector: str | None = None,
        rag_options: Dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> RunResult:
        self._logger.info("Starting CSV analysis",
                         input_file=input,
                         text_col=text_col,
                         id_col=id_col,
                         prompt_length=len(prompt))

        filename = os.path.basename(input)
        # Prefer an explicitly configured fluent source, then argument, then auto-detected
        c = connector or self._source_connector or self._auto_connector_name()
        save_csv = save_csv or "artefacts/${run_id}/analysis.csv"
        save_jsonl = save_jsonl or "artefacts/${run_id}/analysis.jsonl"

        self._logger.debug("CSV analysis configuration",
                          connector=c,
                          save_csv=save_csv,
                          save_jsonl=save_jsonl,
                          expects_json=expects_json)

        output_block: Any = "analysed"
        if expects_json:
            output_block = {
                "name": "analysed",
                "expects": "json",
                "parse_retries": parse_retries,
                "schema": {"type": "object", "required": ["id", "analysed"]},
            }

        rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_images")

        step = {
            "id": "analyse",
            "prompt": (
                "inline: Return a JSON object with fields 'id' and 'analysed'.\n"
                "Only output valid JSON, nothing else.\n\n"
                "ID: {{ id }}\n"
                "Comment:\n{{ text }}\n"
            ),
            "inputs": {"id": f"${{row.{id_col}}}", "text": "${row.text}"},
            "output": output_block,
            **({"rag": rag_cfg} if rag_cfg else {}),
        }
        if mode:
            step["infer"] = {"mode": mode}

        pass_through_cols = [id_col]
        if text_col not in pass_through_cols:
            pass_through_cols.append(text_col)

        chain = {
            "name": "csv-analyse",
            "inputs": {
                "connector": c,
                "select": [filename],
                "mode": "table_rows",
                "table": {"text_column": text_col, "pass_through": pass_through_cols},
            },
            "steps": [step],
            "outputs": [
                {"save": save_jsonl, "from": "analysed", "as": "jsonl"},
                {"save": save_csv, "from": "analysed", "as": "csv"},
            ],
            "concurrency": 4,
            "continue_on_error": False,
        }

        start_time = time.time()
        try:
            self._logger.debug("Executing CSV analysis chain")
            res = self._run_chain_with_effective_config(chain)
            end_time = time.time()

            duration_ms = (end_time - start_time) * 1000
            self._logger.info("CSV analysis completed successfully",
                             duration_ms=duration_ms,
                             run_id=res.get("run_id", "unknown"))

            return _build_run_result(
                chain_result=res,
                start_time=start_time,
                end_time=end_time,
                method_name="csv_analyse",
                fmf_instance=self,
                return_records=return_records,
                save_csv=save_csv,
                save_jsonl=save_jsonl,
            )
        except Exception as e:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            self._logger.error("CSV analysis failed",
                              error=str(e),
                              duration_ms=duration_ms)
            return RunResult(
                success=False,
                run_id="unknown",
                start_time=start_time,
                end_time=end_time,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
                metadata={"method": "csv_analyse"}
            )

    def text_files(
        self,
        *,
        prompt: str,
        connector: str | None = None,
        select: List[str] | None = None,
        save_jsonl: str | None = None,
        expects_json: bool = True,
        return_records: bool = False,
        rag_options: Dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> RunResult:
        c = connector or self._auto_connector_name()
        save_jsonl = save_jsonl or "artefacts/${run_id}/text_outputs.jsonl"
        chain = _build_text_chain(
            connector=c,
            select=select,
            prompt=prompt,
            save_jsonl=save_jsonl,
            expects_json=expects_json,
            rag_options=rag_options,
            mode=mode,
        )
        start_time = time.time()
        try:
            res = self._run_chain_with_effective_config(chain)
            end_time = time.time()

            return _build_run_result(
                chain_result=res,
                start_time=start_time,
                end_time=end_time,
                method_name="text_files",
                fmf_instance=self,
                return_records=return_records,
                save_jsonl=save_jsonl,
            )
        except Exception as e:
            end_time = time.time()
            return RunResult(
                success=False,
                run_id="unknown",
                start_time=start_time,
                end_time=end_time,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
                metadata={"method": "text_files"}
            )

    def images_analyse(
        self,
        *,
        prompt: str,
        connector: str | None = None,
        select: List[str] | None = None,
        save_jsonl: str | None = None,
        expects_json: bool = True,
        group_size: int | None = None,
        return_records: bool = False,
        rag_options: Dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> RunResult:
        c = connector or self._source_connector or self._auto_connector_name()
        save_jsonl = save_jsonl or "artefacts/${run_id}/image_outputs.jsonl"
        if group_size:
            chain = _build_images_group_chain(
                connector=c,
                select=select,
                prompt=prompt,
                save_jsonl=save_jsonl,
                expects_json=expects_json,
                group_size=group_size,
                rag_options=rag_options,
                mode=mode,
            )
        else:
            chain = _build_images_chain(
                connector=c,
                select=select,
                prompt=prompt,
                save_jsonl=save_jsonl,
                expects_json=expects_json,
                rag_options=rag_options,
                mode=mode,
            )
        start_time = time.time()
        try:
            res = self._run_chain_with_effective_config(chain)
            end_time = time.time()

            return _build_run_result(
                chain_result=res,
                start_time=start_time,
                end_time=end_time,
                method_name="images_analyse",
                fmf_instance=self,
                return_records=return_records,
                save_jsonl=save_jsonl,
            )
        except Exception as e:
            end_time = time.time()
            return RunResult(
                success=False,
                run_id="unknown",
                start_time=start_time,
                end_time=end_time,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
                metadata={"method": "images_analyse"}
            )

    def dataframe_analyse(
        self,
        *,
        df: "pd.DataFrame",
        text_col: str,
        id_col: str | None = None,
        prompt: str,
        expects_json: bool = True,
        parse_retries: int = 1,
        return_records: bool = False,
        save_csv: str | None = None,
        save_jsonl: str | None = None,
        rag_options: Dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> RunResult:
        """Analyze a pandas DataFrame using FMF inference.

        Args:
            df: pandas DataFrame to analyze
            text_col: Column name containing text to analyze
            id_col: Column name for unique identifiers (optional, will use index if not provided)
            prompt: Analysis prompt template
            expects_json: Whether to expect JSON output
            parse_retries: Number of retries for JSON parsing
            return_records: Whether to return processed records in result
            save_csv: Path to save CSV output (optional)
            save_jsonl: Path to save JSONL output (optional)
            rag_options: RAG configuration options
            mode: Inference mode (auto, regular, stream)

        Returns:
            RunResult with analysis results and metadata
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for DataFrame analysis. Install with: pip install pandas")

        if not isinstance(df, pd.DataFrame):
            raise ValueError("df must be a pandas DataFrame")

        if text_col not in df.columns:
            raise ValueError(f"Text column '{text_col}' not found in DataFrame. Available columns: {list(df.columns)}")

        # Use index as ID if no ID column specified
        if id_col is None:
            id_col = "index"
            df = df.copy()
            df[id_col] = df.index.astype(str)
        elif id_col not in df.columns:
            raise ValueError(f"ID column '{id_col}' not found in DataFrame. Available columns: {list(df.columns)}")

        self._logger.info("Starting DataFrame analysis",
                         rows=len(df),
                         text_col=text_col,
                         id_col=id_col,
                         prompt_length=len(prompt))

        # Convert DataFrame to rows format expected by chain runner
        rows = []
        for idx, row in df.iterrows():
            row_data = {
                "id": str(row[id_col]),
                "text": str(row[text_col]),
            }
            # Include all other columns as pass-through data
            for col in df.columns:
                if col not in [text_col, id_col]:
                    row_data[col] = row[col]
            rows.append(row_data)

        # Build chain configuration for DataFrame processing
        save_csv = save_csv or "artefacts/${run_id}/dataframe_analysis.csv"
        save_jsonl = save_jsonl or "artefacts/${run_id}/dataframe_analysis.jsonl"

        output_block: Any = "analysed"
        if expects_json:
            output_block = {
                "name": "analysed",
                "expects": "json",
                "parse_retries": parse_retries,
                "schema": {"type": "object", "required": ["id", "analysed"]},
            }

        rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_images")

        step = {
            "id": "analyse",
            "prompt": (
                "inline: Return a JSON object with fields 'id' and 'analysed'.\n"
                "Only output valid JSON, nothing else.\n\n"
                "ID: {{ id }}\n"
                "Text:\n{{ text }}\n"
            ),
            "inputs": {"id": "${row.id}", "text": "${row.text}"},
            "output": output_block,
            **({"rag": rag_cfg} if rag_cfg else {}),
        }
        if mode:
            step["infer"] = {"mode": mode}

        # Create a custom chain that processes DataFrame rows directly
        chain = {
            "name": "dataframe-analyse",
            "inputs": {
                "mode": "dataframe_rows",  # Custom mode for DataFrame processing
                "rows": rows,  # Pass rows directly
            },
            "steps": [step],
            "outputs": [
                {"save": save_jsonl, "from": "analysed", "as": "jsonl"},
                {"save": save_csv, "from": "analysed", "as": "csv"},
            ],
            "concurrency": 4,
            "continue_on_error": True,
        }

        start_time = time.time()
        try:
            self._logger.debug("Executing DataFrame analysis chain")
            res = self._run_chain_with_effective_config(chain)
            end_time = time.time()

            duration_ms = (end_time - start_time) * 1000
            self._logger.info("DataFrame analysis completed successfully",
                             duration_ms=duration_ms,
                             run_id=res.get("run_id", "unknown"))

            return _build_run_result(
                chain_result=res,
                start_time=start_time,
                end_time=end_time,
                method_name="dataframe_analyse",
                fmf_instance=self,
                return_records=return_records,
                save_csv=save_csv,
                save_jsonl=save_jsonl,
            )
        except Exception as e:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            self._logger.error("DataFrame analysis failed",
                              error=str(e),
                              duration_ms=duration_ms)
            return RunResult(
                success=False,
                run_id="unknown",
                start_time=start_time,
                end_time=end_time,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
                metadata={"method": "dataframe_analyse"}
            )

    # --- Recipe runner ---
    def run_recipe(
        self,
        path: str,
        *,
        rag_pipeline: str | None = None,
        rag_top_k_text: int | None = None,
        rag_top_k_images: int | None = None,
        use_recipe_rag: bool | None = None,
        mode: str | None = None,
    ) -> dict:
        """Run a high-level recipe YAML (csv_analyse | text_files | images_analyse).

        The recipe file is a minimal schema, e.g.:
          recipe: csv_analyse
          input: ./data/comments.csv
          id_col: ID
          text_col: Comment
          prompt: Summarise this comment
          save: { csv: artefacts/${run_id}/analysis.csv, jsonl: artefacts/${run_id}/analysis.jsonl }
        Optional RAG support can be declared in the recipe under `rag:` and toggled via
        `use_recipe_rag` or overridden with the explicit rag_* parameters.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = _yaml.safe_load(f) or {}
        rtype = (data.get("recipe") or "").strip()
        raw_rag_cfg = data.get("rag")
        rag_cfg = raw_rag_cfg if isinstance(raw_rag_cfg, dict) else {}

        rag_options: Dict[str, Any] | None = None
        if rag_pipeline:
            rag_options = dict(rag_cfg or {})
            rag_options["pipeline"] = rag_pipeline
        else:
            pipeline_name = rag_cfg.get("pipeline")
            want_recipe = True if use_recipe_rag is None else bool(use_recipe_rag)
            if pipeline_name and want_recipe:
                rag_options = dict(rag_cfg)

        if rag_options:
            if rag_top_k_text is not None:
                rag_options["top_k_text"] = rag_top_k_text
            if rag_top_k_images is not None:
                rag_options["top_k_images"] = rag_top_k_images

        effective_mode = mode or data.get("mode")

        if rtype == "csv_analyse":
            return {
                "result": self.csv_analyse(
                    input=data["input"],
                    text_col=data.get("text_col", "Comment"),
                    id_col=data.get("id_col", "ID"),
                    prompt=data.get("prompt", "Summarise"),
                    save_csv=(data.get("save") or {}).get("csv"),
                    save_jsonl=(data.get("save") or {}).get("jsonl"),
                    connector=data.get("connector"),
                    rag_options=rag_options,
                    mode=effective_mode,
                )
            }
        if rtype == "text_files":
            return {
                "result": self.text_files(
                    prompt=data.get("prompt", "Summarise"),
                    connector=data.get("connector"),
                    select=data.get("select"),
                    save_jsonl=(data.get("save") or {}).get("jsonl"),
                    expects_json=bool(data.get("expects_json", True)),
                    rag_options=rag_options,
                    mode=effective_mode,
                )
            }
        if rtype == "images_analyse":
            return {
                "result": self.images_analyse(
                    prompt=data.get("prompt", "Describe"),
                    connector=data.get("connector"),
                    select=data.get("select"),
                    save_jsonl=(data.get("save") or {}).get("jsonl"),
                    expects_json=bool(data.get("expects_json", True)),
                    group_size=int(data.get("group_size", 0) or 0) or None,
                    rag_options=rag_options,
                    mode=effective_mode,
                )
            }
        raise ValueError(f"Unsupported or missing recipe type: {rtype!r}")

    # --- Fluent Builder API ---
    def with_service(self, name: InferenceProvider) -> "FMF":
        """Configure the inference service provider.

        Args:
            name: Service name. Available options:
                - "azure_openai": Azure OpenAI service
                - "aws_bedrock": AWS Bedrock service

        Returns:
            Self for method chaining
        """
        self._service_override = name
        return self

    def with_rag(self, enabled: bool, pipeline: str | None = None) -> "FMF":
        """Configure RAG (Retrieval-Augmented Generation) settings.

        Args:
            enabled: Whether to enable RAG
            pipeline: Optional pipeline name for RAG retrieval

        Returns:
            Self for method chaining
        """
        if enabled and pipeline:
            self._rag_override = {
                "pipelines": [
                    {
                        "name": pipeline,
                        "connector": self._source_connector or "local_docs",
                        "select": ["**/*.md", "**/*.txt"],
                        "modalities": ["text"],
                        "max_text_items": 5
                    }
                ]
            }
        elif enabled:
            # Enable RAG with default pipeline
            self._rag_override = {
                "pipelines": [
                    {
                        "name": "default_rag",
                        "connector": self._source_connector or "local_docs",
                        "select": ["**/*.md", "**/*.txt"],
                        "modalities": ["text"],
                        "max_text_items": 5
                    }
                ]
            }
        else:
            # Disable RAG
            self._rag_override = None
        return self

    def with_response(self, kind: Literal["csv", "json", "text", "jsonl"]) -> "FMF":
        """Configure the response format.

        Args:
            kind: Response format type

        Returns:
            Self for method chaining
        """
        self._response_format = kind
        return self

    def with_source(self, connector: Literal["sharepoint", "s3", "local", "azure_blob"], **kwargs) -> "FMF":
        """Configure the data source connector.

        Args:
            connector: Connector type
            **kwargs: Connector-specific configuration

        Returns:
            Self for method chaining
        """
        # Generate a connector name if not provided
        connector_name = kwargs.pop('name', f"{connector}_docs")

        # Set default configurations based on connector type
        if connector == "local":
            default_config = {
                "type": "local",
                "root": kwargs.pop('root', './data'),
                "include": kwargs.pop('include', ["**/*.md", "**/*.txt", "**/*.csv", "**/*.{png,jpg,jpeg}"])
            }
        elif connector == "s3":
            default_config = {
                "type": "s3",
                "bucket": kwargs.pop('bucket', 'my-bucket'),
                "prefix": kwargs.pop('prefix', ''),
                "region": kwargs.pop('region', 'us-east-1'),
                "kms_required": kwargs.pop('kms_required', False)
            }
        elif connector == "sharepoint":
            default_config = {
                "type": "sharepoint",
                "site_url": kwargs.pop('site_url', 'https://contoso.sharepoint.com/sites/documents'),
                "drive": kwargs.pop('drive', 'Documents'),
                "root_path": kwargs.pop('root_path', ''),
                "auth_profile": kwargs.pop('auth_profile', 'default')
            }
        elif connector == "azure_blob":
            default_config = {
                "type": "azure_blob",
                "account_name": kwargs.pop('account_name', 'myaccount'),
                "container_name": kwargs.pop('container_name', 'data'),
                "prefix": kwargs.pop('prefix', ''),
                "auth_profile": kwargs.pop('auth_profile', 'default')
            }
        else:
            default_config = {"type": connector}

        # Merge with provided kwargs
        default_config.update(kwargs)

        self._source_connector = connector_name
        self._source_kwargs = default_config
        return self

    def run_inference(self, kind: Literal["csv", "text", "images"], method: str, **kwargs) -> Any:
        """Run inference using the configured settings.

        Args:
            kind: Type of inference to run
            method: Specific method to use
            **kwargs: Method-specific parameters

        Returns:
            Inference results
        """
        # Apply fluent configuration to kwargs
        if self._source_connector and 'connector' not in kwargs:
            kwargs['connector'] = self._source_connector

        if self._response_format:
            if self._response_format == "csv" and 'save_csv' not in kwargs:
                kwargs['save_csv'] = "artefacts/${run_id}/analysis.csv"
            elif self._response_format == "jsonl" and 'save_jsonl' not in kwargs:
                kwargs['save_jsonl'] = "artefacts/${run_id}/analysis.jsonl"

        # Apply RAG configuration if enabled
        if self._rag_override and 'rag_options' not in kwargs:
            # Extract RAG options from fluent configuration
            rag_options = {
                "pipeline": self._rag_override["pipelines"][0]["name"],
                "top_k_text": 2,
                "top_k_images": 2
            }
            kwargs['rag_options'] = rag_options

        # Delegate to appropriate method based on kind
        if kind == "csv":
            if method == "analyse":
                return self.csv_analyse(**kwargs)
            else:
                raise ValueError(f"Unknown CSV method: {method}")
        elif kind == "text":
            if method == "to_json":
                return self.text_to_json(**kwargs)
            elif method == "files":
                return self.text_files(**kwargs)
            else:
                raise ValueError(f"Unknown text method: {method}")
        elif kind == "images":
            if method == "analyse":
                return self.images_analyse(**kwargs)
            else:
                raise ValueError(f"Unknown images method: {method}")
        else:
            raise ValueError(f"Unknown inference kind: {kind}")

    # --- Helpers ---
    def _auto_connector_name(self) -> str:
        cfg = self._cfg
        if cfg is None:
            return "local_docs"
        connectors = getattr(cfg, "connectors", None) if not isinstance(cfg, dict) else cfg.get("connectors")
        if not connectors:
            return "local_docs"
        # Prefer first local connector, else first connector
        for c in connectors:
            t = getattr(c, "type", None) if not isinstance(c, dict) else c.get("type")
            if t == "local":
                return getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
        name = getattr(connectors[0], "name", None) if not isinstance(connectors[0], dict) else connectors[0].get("name")
        return name or "local_docs"

    def _load_aws_credentials_early(self) -> None:
        """Load AWS credentials from .env into os.environ early for boto3.
        
        This ensures S3 connector and other AWS services can access credentials
        before chain execution. Mirrors the logic in _prepare_environment.
        """
        try:
            from ..auth import build_auth_provider
            
            auth_cfg = getattr(self._cfg, "auth", None) if not isinstance(self._cfg, dict) else self._cfg.get("auth")
            if not auth_cfg:
                return
                
            try:
                auth_provider = build_auth_provider(auth_cfg)
            except Exception:
                return
                
            if not auth_provider:
                return
                
            # Load AWS credentials into os.environ
            try:
                _aws_keys = auth_provider.resolve(["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"])
                ak = _aws_keys.get("AWS_ACCESS_KEY_ID")
                sk = _aws_keys.get("AWS_SECRET_ACCESS_KEY")
                if ak and sk:
                    os.environ.setdefault("AWS_ACCESS_KEY_ID", ak)
                    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", sk)
            except Exception:
                pass
                
            try:
                _tok = auth_provider.resolve(["AWS_SESSION_TOKEN"])
                st = _tok.get("AWS_SESSION_TOKEN")
                if st:
                    os.environ.setdefault("AWS_SESSION_TOKEN", st)
            except Exception:
                pass
                
            # Load AWS region if configured
            try:
                _region = auth_provider.resolve(["AWS_REGION"])
                region = _region.get("AWS_REGION")
                if region:
                    os.environ.setdefault("AWS_REGION", region)
                    os.environ.setdefault("AWS_DEFAULT_REGION", region)
            except Exception:
                pass
        except Exception:
            # Silently fail - credentials may be available from other sources
            pass

    def _get_effective_config(self) -> "EffectiveConfig":
        """Get the effective configuration merging fluent overrides with base config."""
        from ..config.effective import EffectiveConfig

        # Build fluent overrides dict
        fluent_overrides = dict(self._fluent_overrides)

        # Apply specific fluent overrides
        if self._service_override:
            if 'inference' not in fluent_overrides:
                fluent_overrides['inference'] = {}
            fluent_overrides['inference']['provider'] = self._service_override

        if self._rag_override:
            fluent_overrides['rag'] = self._rag_override

        if self._response_format:
            if 'export' not in fluent_overrides:
                fluent_overrides['export'] = {}
            if 'sinks' not in fluent_overrides['export']:
                fluent_overrides['export']['sinks'] = []
            # Add response format to export sinks
            fluent_overrides['export']['sinks'].append({
                'name': 'fluent_response',
                'type': 's3',  # Default type
                'format': self._response_format
            })

        if self._source_connector:
            # Add or update connector configuration
            if 'connectors' not in fluent_overrides:
                fluent_overrides['connectors'] = []

            # Create connector config - _source_kwargs already has 'type' from with_source
            new_connector = {
                'name': self._source_connector,
                **self._source_kwargs
            }
            fluent_overrides['connectors'].append(new_connector)

        # Create effective config
        return EffectiveConfig.from_base_and_overrides(
            base_config=self._cfg,
            fluent_overrides=fluent_overrides
        )

    def _run_chain_with_effective_config(self, chain: Dict[str, Any]) -> Dict[str, Any]:
        """Run chain config with effective configuration that includes fluent overrides."""
        effective_config = self._get_effective_config()

        # Use the config object directly instead of temporary file
        return run_chain_config(chain, fmf_config=effective_config)

    # --- Fluent API Convenience Methods ---
    def text_to_json(
        self,
        *,
        prompt: str,
        connector: str | None = None,
        select: List[str] | None = None,
        save_jsonl: str | None = None,
        expects_json: bool = True,
        return_records: bool = False,
        rag_options: Dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> RunResult:
        """Convert text files to JSON using fluent API pattern.

        This is a convenience wrapper around text_files() that follows the fluent API naming.
        """
        return self.text_files(
            prompt=prompt,
            connector=connector,
            select=select,
            save_jsonl=save_jsonl,
            expects_json=expects_json,
            return_records=return_records,
            rag_options=rag_options,
            mode=mode,
        )


def _read_jsonl(path: str):
    import json

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


# --- Additional SDK operations ---
def _build_text_chain(
    *,
    connector: str,
    select: List[str] | None,
    prompt: str,
    save_jsonl: str | None,
    expects_json: bool,
    rag_options: Dict[str, Any] | None = None,
    mode: str | None = None,
) -> Dict[str, Any]:
    output_block: Any = "result"
    if expects_json:
        output_block = {"name": "result", "expects": "json", "parse_retries": 1}
    step = {
        "id": "s",
        "prompt": f"inline: {prompt}\n{{{{ text }}}}",
        "inputs": {"text": "${chunk.text}"},
        "output": output_block,
    }
    if mode:
        step["infer"] = {"mode": mode}
    rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_images")
    if rag_cfg:
        step["rag"] = rag_cfg
    return {
        "name": "text-files",
        "inputs": {"connector": connector, "select": select or ["**/*.{md,txt,html}"]},
        "steps": [step],
        "outputs": ([{"save": save_jsonl, "from": "result", "as": "jsonl"}] if save_jsonl else []),
    }


def _build_images_chain(
    *,
    connector: str,
    select: List[str] | None,
    prompt: str,
    save_jsonl: str | None,
    expects_json: bool,
    rag_options: Dict[str, Any] | None = None,
    mode: str | None = None,
) -> Dict[str, Any]:
    output_block: Any = "analysis"
    if expects_json:
        output_block = {"name": "analysis", "expects": "json", "parse_retries": 1}
    step = {
        "id": "vision",
        "mode": "multimodal",
        "prompt": f"inline: {prompt}",
        "inputs": {},
        "output": output_block,
    }
    if mode:
        step["infer"] = {"mode": mode}
    rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_samples")
    if rag_cfg:
        step["rag"] = rag_cfg
    return {
        "name": "images-analyse",
        "inputs": {"connector": connector, "select": select or ["**/*.{png,jpg,jpeg}"]},
        "steps": [step],
        "outputs": ([{"save": save_jsonl, "from": "analysis", "as": "jsonl"}] if save_jsonl else []),
    }


def _build_images_group_chain(
    *,
    connector: str,
    select: List[str] | None,
    prompt: str,
    save_jsonl: str | None,
    expects_json: bool,
    group_size: int,
    rag_options: Dict[str, Any] | None = None,
    mode: str | None = None,
) -> Dict[str, Any]:
    output_block: Any = "analysis"
    if expects_json:
        output_block = {"name": "analysis", "expects": "json", "parse_retries": 1}
    step = {
        "id": "vision",
        "mode": "multimodal",
        "prompt": f"inline: {prompt}",
        "inputs": {},
        "output": output_block,
    }
    if mode:
        step["infer"] = {"mode": mode}
    rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_samples")
    if rag_cfg:
        step["rag"] = rag_cfg
    return {
        "name": "images-analyse-group",
        "inputs": {"connector": connector, "select": select or ["**/*.{png,jpg,jpeg}"], "mode": "images_group", "images": {"group_size": group_size}},
        "steps": [step],
        "outputs": ([{"save": save_jsonl, "from": "analysis", "as": "jsonl"}] if save_jsonl else []),
    }


def _build_rag_block(
    rag_options: Dict[str, Any] | None,
    *,
    default_text_var: str | None = "rag_context",
    default_image_var: str | None = "rag_images",
) -> Dict[str, Any] | None:
    if not rag_options:
        return None
    pipeline = rag_options.get("pipeline")
    if not pipeline:
        return None

    cfg = dict(rag_options)
    cfg["pipeline"] = pipeline

    if "top_k_text" in cfg and cfg["top_k_text"] is not None:
        try:
            cfg["top_k_text"] = max(0, int(cfg["top_k_text"]))
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid top_k_text value: {cfg['top_k_text']!r}") from exc

    has_images = False
    if "top_k_images" in cfg and cfg["top_k_images"] is not None:
        try:
            cfg["top_k_images"] = max(0, int(cfg["top_k_images"]))
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid top_k_images value: {cfg['top_k_images']!r}") from exc
        has_images = cfg["top_k_images"] > 0
    else:
        cfg.pop("top_k_images", None)

    if "text_var" not in cfg and default_text_var:
        cfg["text_var"] = default_text_var

    if has_images:
        if "image_var" not in cfg and default_image_var:
            cfg["image_var"] = default_image_var
    else:
        cfg.pop("image_var", None)

    if "inject_prompt" not in cfg:
        cfg["inject_prompt"] = True

    return cfg


# Add ergonomics methods to FMF class
def _add_ergonomics_methods():
    """Add ergonomics methods to the FMF class."""

    def defaults(self, **kwargs) -> "FMF":
        """
        Set common default options in one call.

        Args:
            **kwargs: Common options including:
                - service: Service provider name
                - rag: Enable RAG (bool) or RAG config dict
                - response: Response format (csv, json, jsonl, text)
                - source: Source connector name or config
                - connector: Alias for source

        Returns:
            Self for method chaining

        Example:
            fmf = FMF.from_env("fmf.yaml").defaults(
                service="azure_openai",
                rag=True,
                response="csv"
            )
        """
        # Apply service if provided
        if "service" in kwargs:
            self = self.with_service(kwargs["service"])

        # Apply RAG if provided
        if "rag" in kwargs:
            rag_config = kwargs["rag"]
            if isinstance(rag_config, bool):
                if rag_config:
                    self = self.with_rag(enabled=True)
            elif isinstance(rag_config, dict):
                pipeline = rag_config.get("pipeline", "default_rag")
                self = self.with_rag(enabled=True, pipeline=pipeline)

        # Apply response format if provided
        if "response" in kwargs:
            self = self.with_response(kwargs["response"])

        # Apply source if provided
        if "source" in kwargs:
            source = kwargs["source"]
            if isinstance(source, str):
                self = self.with_source(source)
            elif isinstance(source, dict):
                connector_type = source.get("type", "local")
                self = self.with_source(connector_type, **source)
        elif "connector" in kwargs:
            self = self.with_source(kwargs["connector"])

        return self

    def __enter__(self) -> "FMF":
        """
        Context manager entry.

        Returns:
            Self for use in 'with' statements
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit.

        Performs cleanup of resources and connectors.
        """
        # Clean up any resources that need explicit cleanup
        # For now, this is a placeholder for future resource management
        pass

    def from_sharepoint(
        self,
        site_url: str,
        list_name: str,
        drive: str = "Documents",
        root_path: str | None = None,
        auth_profile: str | None = None,
        **kwargs: Any
    ) -> "FMF":
        """
        Configure SharePoint as the data source.

        Args:
            site_url: SharePoint site URL
            list_name: List or library name
            drive: Drive name (default: "Documents")
            root_path: Root path within the drive
            auth_profile: Authentication profile name
            **kwargs: Additional SharePoint configuration

        Returns:
            Self for method chaining
        """
        from .types import SourceConfig

        source_config = SourceConfig.for_sharepoint(
            site_url=site_url,
            list_name=list_name,
            drive=drive,
            root_path=root_path,
            auth_profile=auth_profile,
            **kwargs
        )

        return self.with_source("sharepoint", **source_config.config)

    def from_s3(
        self,
        bucket: str,
        prefix: str = "",
        region: str | None = None,
        kms_required: bool = False,
        **kwargs: Any
    ) -> "FMF":
        """
        Configure S3 as the data source.

        Args:
            bucket: S3 bucket name
            prefix: Key prefix for filtering objects
            region: AWS region
            kms_required: Whether KMS encryption is required
            **kwargs: Additional S3 configuration

        Returns:
            Self for method chaining
        """
        from .types import SourceConfig

        source_config = SourceConfig.for_s3(
            bucket=bucket,
            prefix=prefix,
            region=region,
            kms_required=kms_required,
            **kwargs
        )

        return self.with_source("s3", **source_config.config)

    def from_local(
        self,
        root_path: str,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        **kwargs: Any
    ) -> "FMF":
        """
        Configure local filesystem as the data source.

        Args:
            root_path: Root directory path
            include_patterns: File patterns to include (e.g., ["**/*.md", "**/*.txt"])
            exclude_patterns: File patterns to exclude (e.g., ["**/.git/**"])
            **kwargs: Additional local filesystem configuration

        Returns:
            Self for method chaining
        """
        from .types import SourceConfig

        source_config = SourceConfig.for_local(
            root_path=root_path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            **kwargs
        )

        return self.with_source("local", **source_config.config)

    # Add methods to FMF class
    FMF.defaults = defaults
    FMF.__enter__ = __enter__
    FMF.__exit__ = __exit__
    FMF.from_sharepoint = from_sharepoint
    FMF.from_s3 = from_s3
    FMF.from_local = from_local


# Apply ergonomics methods
_add_ergonomics_methods()
