"""Effective configuration model for merging base, recipe, and fluent overrides."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator

from .models import FmfConfig, BaseConnector, InferenceProvider


class EffectiveConfig(BaseModel):
    """
    Effective configuration that merges base YAML, recipe (optional), and fluent overrides.
    
    Precedence order (highest to lowest):
    1. Fluent overrides (passed via constructor)
    2. Recipe configuration (optional)
    3. Base configuration (lowest)
    
    This model handles type coercion and validation during the merge process.
    """
    
    # Core fields
    project: str = "frontier-model-framework"
    run_profile: str = "default"
    artefacts_dir: str = "artefacts"
    
    # Optional sections
    auth: Optional[Dict[str, Any]] = None
    connectors: List[Dict[str, Any]] = Field(default_factory=list)
    processing: Optional[Dict[str, Any]] = None
    inference: Optional[Dict[str, Any]] = None
    export: Optional[Dict[str, Any]] = None
    prompt_registry: Optional[Dict[str, Any]] = None
    run: Optional[Dict[str, Any]] = None
    rag: Optional[Dict[str, Any]] = None
    experimental: Optional[Dict[str, Any]] = None
    retries: Optional[Dict[str, Any]] = None
    
    # Fluent overrides (not part of base config)
    fluent_overrides: Dict[str, Any] = Field(default_factory=dict, exclude=True)
    
    model_config = {"extra": "allow"}
    
    @classmethod
    def from_base_and_overrides(
        cls,
        base_config: Union[FmfConfig, Dict[str, Any]],
        recipe_config: Optional[Dict[str, Any]] = None,
        fluent_overrides: Optional[Dict[str, Any]] = None,
    ) -> "EffectiveConfig":
        """
        Create effective config by merging base, recipe, and fluent overrides.
        
        Args:
            base_config: Base configuration (FmfConfig or dict)
            recipe_config: Optional recipe configuration to merge
            fluent_overrides: Optional fluent API overrides
            
        Returns:
            EffectiveConfig with merged values
        """
        # Convert base config to dict
        if isinstance(base_config, FmfConfig):
            base_dict = base_config.model_dump(exclude_none=True)
        else:
            base_dict = dict(base_config) if base_config else {}
        
        # Start with base config
        effective_dict = dict(base_dict)
        
        # Apply recipe config if provided
        if recipe_config:
            effective_dict = cls._merge_dicts(effective_dict, recipe_config)
        
        # Apply fluent overrides if provided
        if fluent_overrides:
            effective_dict = cls._merge_dicts(effective_dict, fluent_overrides)
        
        # Store fluent overrides for reference
        effective_dict["fluent_overrides"] = fluent_overrides or {}
        
        return cls(**effective_dict)
    
    @staticmethod
    def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, with override taking precedence.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
        """
        result = dict(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = EffectiveConfig._merge_dicts(result[key], value)
            else:
                # Override takes precedence
                result[key] = value
        
        return result
    
    def get_inference_provider(self) -> Optional[str]:
        """Get the effective inference provider."""
        if not self.inference:
            return None
        return self.inference.get("provider")
    
    def get_connector_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get connector configuration by name."""
        for connector in self.connectors:
            if connector.get("name") == name:
                return connector
        return None
    
    def add_or_update_connector(self, connector_config: Dict[str, Any]) -> None:
        """Add or update a connector configuration."""
        name = connector_config.get("name")
        if not name:
            return
        
        # Find existing connector
        for i, existing in enumerate(self.connectors):
            if existing.get("name") == name:
                # Update existing
                self.connectors[i] = connector_config
                return
        
        # Add new connector
        self.connectors.append(connector_config)
    
    def get_rag_pipeline(self, pipeline_name: str) -> Optional[Dict[str, Any]]:
        """Get RAG pipeline configuration by name."""
        if not self.rag or "pipelines" not in self.rag:
            return None
        
        for pipeline in self.rag["pipelines"]:
            if pipeline.get("name") == pipeline_name:
                return pipeline
        return None
    
    def to_fmf_config(self) -> FmfConfig:
        """Convert to FmfConfig model for compatibility."""
        # Remove fluent_overrides before conversion
        config_dict = self.model_dump(exclude={"fluent_overrides"})
        return FmfConfig(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding fluent_overrides."""
        return self.model_dump(exclude={"fluent_overrides"})
