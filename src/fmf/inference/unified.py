from __future__ import annotations

from typing import Any

from .registry import build_provider, available_providers
from .azure_openai import AzureOpenAIClient
from .bedrock import BedrockClient


def _subconfig(cfg: Any, key: str) -> Any:
    if isinstance(cfg, dict):
        return cfg.get(key)
    return getattr(cfg, key, None)


def build_llm_client(cfg: Any):
    provider = getattr(cfg, "provider", None) if not isinstance(cfg, dict) else cfg.get("provider")
    if provider is None:
        raise ValueError("Inference provider not specified in configuration")

    subcfg = _subconfig(cfg, provider)
    try:
        return build_provider(provider, subcfg)
    except ValueError:
        pass

    if provider == "azure_openai":
        endpoint = getattr(subcfg, "endpoint", None) if not isinstance(subcfg, dict) else subcfg.get("endpoint")
        api_version = getattr(subcfg, "api_version", None) if not isinstance(subcfg, dict) else subcfg.get("api_version")
        deployment = getattr(subcfg, "deployment", None) if not isinstance(subcfg, dict) else subcfg.get("deployment")
        return AzureOpenAIClient(endpoint=endpoint, api_version=api_version, deployment=deployment)
    if provider == "aws_bedrock":
        region = getattr(subcfg, "region", None) if not isinstance(subcfg, dict) else subcfg.get("region")
        model_id = getattr(subcfg, "model_id", None) if not isinstance(subcfg, dict) else subcfg.get("model_id")
        return BedrockClient(region=region, model_id=model_id)
    raise ValueError(f"Unsupported inference provider: {provider}. Known providers: {', '.join(available_providers())}")


__all__ = ["build_llm_client"]
