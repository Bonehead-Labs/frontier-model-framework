from __future__ import annotations

from typing import Any

from .azure_openai import AzureOpenAIClient
from .bedrock import BedrockClient


def build_llm_client(cfg: Any):
    provider = getattr(cfg, "provider", None) if not isinstance(cfg, dict) else cfg.get("provider")
    if provider == "azure_openai":
        acfg = getattr(cfg, "azure_openai", None) if not isinstance(cfg, dict) else cfg.get("azure_openai")
        endpoint = getattr(acfg, "endpoint", None) if not isinstance(acfg, dict) else acfg.get("endpoint")
        api_version = getattr(acfg, "api_version", None) if not isinstance(acfg, dict) else acfg.get("api_version")
        deployment = getattr(acfg, "deployment", None) if not isinstance(acfg, dict) else acfg.get("deployment")
        return AzureOpenAIClient(endpoint=endpoint, api_version=api_version, deployment=deployment)
    if provider == "aws_bedrock":
        bcfg = getattr(cfg, "aws_bedrock", None) if not isinstance(cfg, dict) else cfg.get("aws_bedrock")
        region = getattr(bcfg, "region", None) if not isinstance(bcfg, dict) else bcfg.get("region")
        model_id = getattr(bcfg, "model_id", None) if not isinstance(bcfg, dict) else bcfg.get("model_id")
        return BedrockClient(region=region, model_id=model_id)
    raise ValueError(f"Unsupported inference provider: {provider}")


__all__ = ["build_llm_client"]

