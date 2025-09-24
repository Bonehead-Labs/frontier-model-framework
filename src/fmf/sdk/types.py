"""Enhanced types for FMF SDK ergonomics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RunResult:
    """
    Rich result object containing execution details, paths, counts, and timings.

    This provides a much more useful return type than raw data, giving users
    access to metadata about their FMF operations.
    """

    # Core execution results
    success: bool
    run_id: str
    records_processed: int = 0
    records_returned: int = 0

    # File paths and outputs
    output_paths: List[str] = field(default_factory=list)
    csv_path: Optional[str] = None
    jsonl_path: Optional[str] = None
    json_path: Optional[str] = None

    # Timing information
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None

    # Configuration used
    service_used: Optional[str] = None
    rag_enabled: bool = False
    rag_pipeline: Optional[str] = None
    source_connector: Optional[str] = None

    # Raw data (if requested)
    data: Optional[List[Dict[str, Any]]] = None

    # Error information
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate duration if start and end times are provided."""
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time) * 1000

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        return self.duration_ms / 1000 if self.duration_ms else None

    @property
    def has_outputs(self) -> bool:
        """Check if any output files were created."""
        return len(self.output_paths) > 0

    @property
    def primary_output_path(self) -> Optional[str]:
        """Get the primary output path (CSV preferred, then JSONL, then first available)."""
        if self.csv_path:
            return self.csv_path
        elif self.jsonl_path:
            return self.jsonl_path
        elif self.json_path:
            return self.json_path
        elif self.output_paths:
            return self.output_paths[0]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "run_id": self.run_id,
            "records_processed": self.records_processed,
            "records_returned": self.records_returned,
            "output_paths": self.output_paths,
            "csv_path": self.csv_path,
            "jsonl_path": self.jsonl_path,
            "json_path": self.json_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "service_used": self.service_used,
            "rag_enabled": self.rag_enabled,
            "rag_pipeline": self.rag_pipeline,
            "source_connector": self.source_connector,
            "error": self.error,
            "error_details": self.error_details,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation for easy debugging."""
        status = "✅ Success" if self.success else "❌ Failed"
        duration = f"{self.duration_ms:.1f}ms" if self.duration_ms else "unknown"

        parts = [
            f"{status} (Run: {self.run_id})",
            f"Records: {self.records_processed} processed, {self.records_returned} returned",
            f"Duration: {duration}",
        ]

        if self.primary_output_path:
            parts.append(f"Output: {self.primary_output_path}")

        if self.service_used:
            parts.append(f"Service: {self.service_used}")

        if self.rag_enabled:
            parts.append(f"RAG: {self.rag_pipeline or 'enabled'}")

        if self.error:
            parts.append(f"Error: {self.error}")

        return " | ".join(parts)


@dataclass
class SourceConfig:
    """Configuration for data source connectors."""

    connector_type: str
    name: str
    config: Dict[str, Any]

    @classmethod
    def for_sharepoint(
        cls,
        site_url: str,
        list_name: str,
        drive: str = "Documents",
        root_path: Optional[str] = None,
        auth_profile: Optional[str] = None,
        **kwargs: Any
    ) -> "SourceConfig":
        """Create SharePoint source configuration."""
        config = {
            "site_url": site_url,
            "list_name": list_name,
            "drive": drive,
            **kwargs
        }
        if root_path:
            config["root_path"] = root_path
        if auth_profile:
            config["auth_profile"] = auth_profile

        return cls(
            connector_type="sharepoint",
            name=f"sharepoint_{list_name}",
            config=config
        )

    @classmethod
    def for_s3(
        cls,
        bucket: str,
        prefix: str = "",
        region: Optional[str] = None,
        kms_required: bool = False,
        **kwargs: Any
    ) -> "SourceConfig":
        """Create S3 source configuration."""
        config = {
            "bucket": bucket,
            "prefix": prefix,
            **kwargs
        }
        if region:
            config["region"] = region
        if kms_required:
            config["kms_required"] = kms_required

        return cls(
            connector_type="s3",
            name=f"s3_{bucket}_{prefix.replace('/', '_')}",
            config=config
        )

    @classmethod
    def for_local(
        cls,
        root_path: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        **kwargs: Any
    ) -> "SourceConfig":
        """Create local filesystem source configuration."""
        config = {
            "root": root_path,
            **kwargs
        }
        if include_patterns:
            config["include"] = include_patterns
        if exclude_patterns:
            config["exclude"] = exclude_patterns

        return cls(
            connector_type="local",
            name=f"local_{Path(root_path).name}",
            config=config
        )
