from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Literal

import typer
from typer import Option, Argument

from .sdk import FMF
from .config.loader import load_config
from .auth import build_provider, AuthError
from .observability.logging import get_logger, set_verbose
from .observability.tracing import enable_tracing

# Create Typer app
app = typer.Typer(
    name="fmf",
    help="Frontier Model Framework - Unified CLI for LLM workflows",
    no_args_is_help=True,
    add_completion=False,
)


# Common options are inlined in each command


# CSV Analysis Command
@app.command("csv")
def csv_analyse(
    input_file: str = Argument(..., help="Path to input CSV file"),
    text_col: str = Argument(..., help="Name of the text column to analyze"),
    id_col: str = Argument(..., help="Name of the ID column"),
    prompt: str = Argument(..., help="Analysis prompt"),
    # Fluent API options
    service: Optional[Literal["azure_openai", "aws_bedrock"]] = Option(None, "--service", help="Inference service provider"),
    rag: bool = Option(False, "--rag", help="Enable RAG (Retrieval-Augmented Generation)"),
    rag_pipeline: Optional[str] = Option(None, "--rag-pipeline", help="RAG pipeline name"),
    response: Optional[Literal["csv", "jsonl", "both"]] = Option("both", "--response", help="Response format"),
    source: Optional[Literal["local", "s3", "sharepoint", "azure_blob"]] = Option(None, "--source", help="Data source connector"),
    # Output options
    output_csv: Optional[str] = Option(None, "--output-csv", help="Path for CSV output"),
    output_jsonl: Optional[str] = Option(None, "--output-jsonl", help="Path for JSONL output"),
    # Inference options
    mode: Optional[Literal["auto", "regular", "stream"]] = Option(None, "--mode", help="Inference mode"),
    expects_json: bool = Option(True, "--expects-json/--no-expects-json", help="Expect JSON output from LLM"),
    # Common options
    config: str = Option("fmf.yaml", "-c", "--config", help="Path to FMF config file"),
    verbose: bool = Option(False, "-v", "--verbose", help="Enable verbose output"),
    dry_run: bool = Option(False, "--dry-run", help="Show what would be done without executing"),
    tracing: bool = Option(False, "--tracing", help="Enable OpenTelemetry tracing"),
) -> None:
    """Analyze CSV files using FMF fluent API."""
    # Set up logging and tracing
    set_verbose(verbose)
    logger = get_logger("fmf.csv_analyse", verbose)
    
    if tracing:
        enable_tracing("fmf-csv-analyse")
    
    if not Path(input_file).exists():
        logger.error(f"Input file not found: {input_file}")
        typer.echo(f"Error: Input file '{input_file}' not found.", err=True)
        raise typer.Exit(1)
    
    try:
        # Build FMF instance with fluent API
        logger.info("Initializing FMF client", config_file=config)
        fmf = FMF.from_env(config)
        
        # Apply fluent configuration
        logger.debug("Applying fluent configuration")
        if service:
            logger.info(f"Setting service provider: {service}")
            fmf = fmf.with_service(service)
        
        if rag:
            pipeline = rag_pipeline or "default_rag"
            logger.info(f"Enabling RAG with pipeline: {pipeline}")
            fmf = fmf.with_rag(enabled=True, pipeline=pipeline)
        
        if response:
            logger.info(f"Setting response format: {response}")
            fmf = fmf.with_response(response)
        
        if source:
            logger.info(f"Setting source connector: {source}")
            fmf = fmf.with_source(source)
        
        # Prepare RAG options
        rag_options = None
        if rag:
            rag_options = {
                "pipeline": rag_pipeline or "default_rag",
                "top_k_text": 2,
                "top_k_images": 2,
            }
            logger.debug("RAG options configured", rag_options=rag_options)

        # Prepare parsed text_col (support comma-separated list)
        parsed_text_col = text_col
        if "," in text_col:
            parts = [c.strip() for c in text_col.split(",") if c.strip()]
            if parts:
                parsed_text_col = parts

        # Optional dry run
        if dry_run:
            logger.info("Dry run mode - showing configuration")
            typer.echo(f"Would analyze CSV: {input_file}")
            typer.echo(f"  Text column: {parsed_text_col}")
            typer.echo(f"  ID column: {id_col}")
            typer.echo(f"  Prompt: {prompt}")
            if service:
                typer.echo(f"  Service: {service}")
            if rag:
                typer.echo(f"  RAG: enabled (pipeline: {rag_pipeline or 'default_rag'})")
            if response:
                typer.echo(f"  Response format: {response}")
            if source:
                typer.echo(f"  Source: {source}")
            return

        # Start analysis
        logger.info("Starting CSV analysis",
                    input_file=input_file,
                    text_col=parsed_text_col,
                    id_col=id_col,
                    prompt_length=len(prompt))

        with logger.operation("csv_analyse",
                              input_file=input_file,
                              text_col=parsed_text_col,
                              id_col=id_col):
            records = fmf.csv_analyse(
                input=input_file,
                text_col=parsed_text_col,
                id_col=id_col,
                prompt=prompt,
                save_csv=output_csv,
                save_jsonl=output_jsonl,
                expects_json=expects_json,
                rag_options=rag_options,
                mode=mode,
                return_records=True
            )
        
        if records:
            logger.info("CSV analysis completed successfully", 
                       records_processed=len(records),
                       input_file=input_file)
            typer.echo(f"✓ Processed {len(records)} records from {input_file}")
            if output_csv:
                typer.echo(f"  CSV output: {output_csv}")
            if output_jsonl:
                typer.echo(f"  JSONL output: {output_jsonl}")
        else:
            logger.warning("No records processed", input_file=input_file)
            typer.echo("⚠ No records processed")
            
    except Exception as e:
        logger.error("CSV analysis failed", error=str(e), input_file=input_file)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# Text to JSON Command
@app.command("text")
def text_to_json(
    input_pattern: str = Argument(..., help="Path to input text file(s) or glob pattern"),
    prompt: str = Argument(..., help="Processing prompt"),
    # Fluent API options
    service: Optional[Literal["azure_openai", "aws_bedrock"]] = Option(None, "--service", help="Inference service provider"),
    rag: bool = Option(False, "--rag", help="Enable RAG (Retrieval-Augmented Generation)"),
    rag_pipeline: Optional[str] = Option(None, "--rag-pipeline", help="RAG pipeline name"),
    response: Optional[Literal["jsonl", "json"]] = Option("jsonl", "--response", help="Response format"),
    source: Optional[Literal["local", "s3", "sharepoint", "azure_blob"]] = Option(None, "--source", help="Data source connector"),
    # Output options
    output: Optional[str] = Option(None, "--output", help="Path for output file"),
    # Inference options
    mode: Optional[Literal["auto", "regular", "stream"]] = Option(None, "--mode", help="Inference mode"),
    expects_json: bool = Option(True, "--expects-json/--no-expects-json", help="Expect JSON output from LLM"),
    # Common options
    config: str = Option("fmf.yaml", "-c", "--config", help="Path to FMF config file"),
    verbose: bool = Option(False, "-v", "--verbose", help="Enable verbose output"),
    dry_run: bool = Option(False, "--dry-run", help="Show what would be done without executing"),
    tracing: bool = Option(False, "--tracing", help="Enable OpenTelemetry tracing"),
) -> None:
    """Convert text files to JSON using FMF fluent API."""
    # Set up logging and tracing
    set_verbose(verbose)
    logger = get_logger("fmf.text_to_json", verbose)
    
    if tracing:
        enable_tracing("fmf-text-to-json")
    
    if not Path(input_pattern).exists() and "*" not in input_pattern:
        logger.error(f"Input file not found: {input_pattern}")
        typer.echo(f"Error: Input file '{input_pattern}' not found.", err=True)
        raise typer.Exit(1)
    
    try:
        # Build FMF instance with fluent API
        logger.info("Initializing FMF client", config_file=config)
        fmf = FMF.from_env(config)
        
        # Apply fluent configuration
        if service:
            fmf = fmf.with_service(service)
        
        if rag:
            pipeline = rag_pipeline or "default_rag"
            fmf = fmf.with_rag(enabled=True, pipeline=pipeline)
        
        if response:
            fmf = fmf.with_response(response)
        
        if source:
            fmf = fmf.with_source(source)
        
        # Prepare RAG options
        rag_options = None
        if rag:
            rag_options = {
                "pipeline": rag_pipeline or "default_rag",
                "top_k_text": 2,
                "top_k_images": 2,
            }
        
        if dry_run:
            typer.echo(f"Would process text: {input_pattern}")
            typer.echo(f"  Prompt: {prompt}")
            if service:
                typer.echo(f"  Service: {service}")
            if rag:
                typer.echo(f"  RAG: enabled (pipeline: {rag_pipeline or 'default_rag'})")
            if response:
                typer.echo(f"  Response format: {response}")
            if source:
                typer.echo(f"  Source: {source}")
            return
        
        # Determine select pattern
        if "*" in input_pattern:
            select_pattern = [input_pattern]
        else:
            select_pattern = [input_pattern]
        
        # Run text to JSON conversion
        records = fmf.text_to_json(
            prompt=prompt,
            select=select_pattern,
            save_jsonl=output,
            expects_json=expects_json,
            rag_options=rag_options,
            mode=mode,
            return_records=True
        )
        
        if records:
            typer.echo(f"✓ Processed {len(records)} text chunks from {input_pattern}")
            if output:
                typer.echo(f"  Output: {output}")
        else:
            typer.echo("⚠ No text chunks processed")
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# Images Analysis Command
@app.command("images")
def images_analyse(
    input_pattern: str = Argument(..., help="Path to input image file(s) or glob pattern"),
    prompt: str = Argument(..., help="Analysis prompt"),
    # Fluent API options
    service: Optional[Literal["azure_openai", "aws_bedrock"]] = Option(None, "--service", help="Inference service provider"),
    rag: bool = Option(False, "--rag", help="Enable RAG (Retrieval-Augmented Generation)"),
    rag_pipeline: Optional[str] = Option(None, "--rag-pipeline", help="RAG pipeline name"),
    response: Optional[Literal["jsonl", "json"]] = Option("jsonl", "--response", help="Response format"),
    source: Optional[Literal["local", "s3", "sharepoint", "azure_blob"]] = Option(None, "--source", help="Data source connector"),
    # Output options
    output: Optional[str] = Option(None, "--output", help="Path for output file"),
    group_size: Optional[int] = Option(None, "--group-size", help="Number of images to process together"),
    # Inference options
    mode: Optional[Literal["auto", "regular", "stream"]] = Option(None, "--mode", help="Inference mode"),
    expects_json: bool = Option(True, "--expects-json/--no-expects-json", help="Expect JSON output from LLM"),
    # Common options
    config: str = Option("fmf.yaml", "-c", "--config", help="Path to FMF config file"),
    verbose: bool = Option(False, "-v", "--verbose", help="Enable verbose output"),
    dry_run: bool = Option(False, "--dry-run", help="Show what would be done without executing"),
) -> None:
    """Analyze images using FMF fluent API."""
    if not Path(input_pattern).exists() and "*" not in input_pattern:
        typer.echo(f"Error: Input file '{input_pattern}' not found.", err=True)
        raise typer.Exit(1)
    
    try:
        # Build FMF instance with fluent API
        fmf = FMF.from_env(config)
        
        # Apply fluent configuration
        if service:
            fmf = fmf.with_service(service)
        
        if rag:
            pipeline = rag_pipeline or "default_rag"
            fmf = fmf.with_rag(enabled=True, pipeline=pipeline)
        
        if response:
            fmf = fmf.with_response(response)
        
        if source:
            fmf = fmf.with_source(source)
        
        # Prepare RAG options
        rag_options = None
        if rag:
            rag_options = {
                "pipeline": rag_pipeline or "default_rag",
                "top_k_text": 2,
                "top_k_images": 2,
            }
        
        if dry_run:
            typer.echo(f"Would analyze images: {input_pattern}")
            typer.echo(f"  Prompt: {prompt}")
            if service:
                typer.echo(f"  Service: {service}")
            if rag:
                typer.echo(f"  RAG: enabled (pipeline: {rag_pipeline or 'default_rag'})")
            if response:
                typer.echo(f"  Response format: {response}")
            if source:
                typer.echo(f"  Source: {source}")
            if group_size:
                typer.echo(f"  Group size: {group_size}")
            return
        
        # Determine select pattern
        if "*" in input_pattern:
            select_pattern = [input_pattern]
        else:
            select_pattern = [input_pattern]
        
        # Run images analysis
        records = fmf.images_analyse(
            prompt=prompt,
            select=select_pattern,
            save_jsonl=output,
            expects_json=expects_json,
            group_size=group_size,
            rag_options=rag_options,
            mode=mode,
            return_records=True
        )
        
        if records:
            typer.echo(f"✓ Processed {len(records)} image chunks from {input_pattern}")
            if output:
                typer.echo(f"  Output: {output}")
        else:
            typer.echo("⚠ No image chunks processed")
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# Legacy commands (kept for backward compatibility)
@app.command("keys")
def keys_test(
    names: List[str] = Argument([], help="Logical secret names to resolve"),
    config: str = Option("fmf.yaml", "-c", "--config", help="Path to config YAML"),
    set_overrides: List[str] = Option([], "--set", help="Override config values: key.path=value"),
    json_output: bool = Option(False, "--json", help="Emit machine-readable JSON output"),
) -> None:
    """Test secret resolution (legacy command)."""
    set_verbose(False)
    cfg = load_config(config, set_overrides=set_overrides)
    auth_cfg = getattr(cfg, "auth", None)
    if auth_cfg is None and isinstance(cfg, dict):
        auth_cfg = cfg.get("auth")
    if not auth_cfg:
        typer.echo("No 'auth' configuration found in config file.", err=True)
        raise typer.Exit(2)

    if not names:
        # Try to derive from secret_mapping when present
        prov = getattr(auth_cfg, "provider", None)
        mapping_cfg = None
        if prov == "azure_key_vault":
            mapping_cfg = getattr(auth_cfg, "azure_key_vault", None)
        elif prov == "aws_secrets":
            mapping_cfg = getattr(auth_cfg, "aws_secrets", None)
        if mapping_cfg is not None:
            mapping_dict = getattr(mapping_cfg, "secret_mapping", None) or {}
            names = list(mapping_dict.keys())

    if not names:
        typer.echo("No secret names provided and none derivable from config. Provide names after 'keys test'.", err=True)
        raise typer.Exit(2)

    try:
        provider = build_provider(auth_cfg)
        resolved = provider.resolve(names)
    except AuthError as e:
        typer.echo(f"Secret resolution failed: {e}", err=True)
        raise typer.Exit(1)

    secrets_output: list[dict[str, str]] = []
    if not json_output:
        typer.echo("Secrets:")
    for n in names:
        status = "OK" if n in resolved else "MISSING"
        if json_output:
            secrets_output.append({"name": n, "status": status})
        else:
            typer.echo(f"{n}=**** {status}")

    # Additional diagnostics would go here...
    if json_output:
        payload = {"secrets": secrets_output}
        typer.echo(json.dumps(payload, indent=2))


# Main entry point
def main() -> None:
    """Main entry point for the FMF CLI."""
    app()


# Version command
@app.callback(invoke_without_command=True)
def version_callback(
    ctx: typer.Context,
    version: bool = Option(False, "-v", "--version", help="Show version and exit"),
) -> None:
    """FMF CLI - Unified interface for LLM workflows."""
    if version:
        try:
            import importlib.metadata as importlib_metadata
        except Exception:  # pragma: no cover
            import importlib_metadata  # type: ignore

        try:
            version_str = importlib_metadata.version("frontier-model-framework")
        except importlib_metadata.PackageNotFoundError:
            version_str = "0.0.0+local"
        typer.echo(version_str)
        raise typer.Exit(0)
    
    if ctx.invoked_subcommand is None:
        typer.echo("FMF CLI - Unified interface for LLM workflows")
        typer.echo("Use 'fmf --help' to see available commands.")
        typer.echo("")
        typer.echo("Quick start:")
        typer.echo("  fmf csv analyse --input data.csv --text-col Comment --id-col ID --prompt 'Analyze this'")
        typer.echo("  fmf text --input *.txt --prompt 'Summarize'")
        typer.echo("  fmf images --input *.png --prompt 'Describe'")


if __name__ == "__main__":
    main()
