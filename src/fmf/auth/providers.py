from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Protocol

# Accept either Pydantic models or dict-like configs to avoid hard dependency at import time
from ..config.models import AuthConfig  # type: ignore


class AuthError(Exception):
    """Raised when secret resolution fails or a provider is unavailable."""


def _redact(_: str | None) -> str:
    return "****"


class SecretProvider(Protocol):
    def resolve(self, logical_names: Iterable[str]) -> Dict[str, str]:
        ...


def _parse_dotenv(path: str) -> Dict[str, str]:
    """Very small .env parser: KEY=VALUE per line; ignores comments/blank lines."""
    result: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" not in s:
                    continue
                key, val = s.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    result[key] = val
    except FileNotFoundError:
        return {}
    return result


def _cfg_get(cfg: object | None, key: str, default=None):
    if cfg is None:
        return default
    if isinstance(cfg, dict):
        return cfg.get(key, default)
    return getattr(cfg, key, default)


@dataclass
class EnvSecretProvider:
    cfg: object | None
    env: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        self._log = logging.getLogger(__name__)
        self._env = dict(os.environ)
        if self.env is not None:
            self._env.update(self.env)
        self._dotenv = {}
        file = _cfg_get(self.cfg, "file")
        if file:
            self._dotenv = _parse_dotenv(file)
        self._cache: Dict[str, str] = {}

    def resolve(self, logical_names: Iterable[str]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        missing: list[str] = []
        for name in logical_names:
            if name in self._cache:
                out[name] = self._cache[name]
                continue
            if name in self._env:
                val = self._env[name]
            elif name in self._dotenv:
                val = self._dotenv[name]
            else:
                missing.append(name)
                continue
            self._cache[name] = val
            out[name] = val
            self._log.debug("Resolved env secret %s=%s", name, _redact(val))
        if missing:
            raise AuthError(f"Missing required environment secrets: {', '.join(missing)}")
        return out


@dataclass
class AzureKeyVaultProvider:
    cfg: object

    def __post_init__(self) -> None:
        self._log = logging.getLogger(__name__)
        self._cache: Dict[str, str] = {}

    def _client(self):
        try:
            from azure.identity import DefaultAzureCredential  # type: ignore
            from azure.keyvault.secrets import SecretClient  # type: ignore
        except Exception as e:  # pragma: no cover - exercised via tests mocking import
            raise AuthError(
                "Azure dependencies not installed. Install extras: pip install '.[azure]'"
            ) from e

        credential = DefaultAzureCredential()
        vault_url = _cfg_get(self.cfg, "vault_url")
        return SecretClient(vault_url=vault_url, credential=credential)

    def resolve(self, logical_names: Iterable[str]) -> Dict[str, str]:
        mapping = _cfg_get(self.cfg, "secret_mapping", {}) or {}
        names = list(logical_names)
        client = self._client()
        out: Dict[str, str] = {}
        missing: list[str] = []
        for logical in names:
            if logical in self._cache:
                out[logical] = self._cache[logical]
                continue
            secret_name = mapping.get(logical, logical)
            try:
                secret = client.get_secret(secret_name)
                val = getattr(secret, "value", None)
                if val is None:
                    raise AuthError(f"Secret {secret_name!r} has no value")
            except Exception as e:  # pragma: no cover - error paths
                self._log.debug("Failed to resolve Azure KV secret %s: %s", secret_name, e)
                missing.append(logical)
                continue
            self._cache[logical] = val
            out[logical] = val
            self._log.debug(
                "Resolved Azure KV secret %s (logical %s)=%s",
                secret_name,
                logical,
                _redact(val),
            )
        if missing:
            raise AuthError(f"Missing Azure secrets for: {', '.join(missing)}")
        return out


@dataclass
class AwsSecretsProvider:
    cfg: object

    def __post_init__(self) -> None:
        self._log = logging.getLogger(__name__)
        self._cache: Dict[str, str] = {}

    def _client(self, service: str):
        try:
            import boto3  # type: ignore
        except Exception as e:  # pragma: no cover - exercised via tests mocking import
            raise AuthError(
                "AWS boto3 dependency not installed. Install extras: pip install '.[aws]'"
            ) from e
        region = _cfg_get(self.cfg, "region")
        return boto3.client(service, region_name=region)

    def resolve(self, logical_names: Iterable[str]) -> Dict[str, str]:
        mapping = _cfg_get(self.cfg, "secret_mapping", {}) or {}
        names = list(logical_names)
        out: Dict[str, str] = {}
        missing: list[str] = []

        source = (_cfg_get(self.cfg, "source") or "secretsmanager").lower()
        if source == "secretsmanager":
            client = self._client("secretsmanager")
            for logical in names:
                if logical in self._cache:
                    out[logical] = self._cache[logical]
                    continue
                secret_id = mapping.get(logical, logical)
                try:
                    resp = client.get_secret_value(SecretId=secret_id)
                    val = resp.get("SecretString")
                    if val is None:
                        # binary not supported here; user must store strings
                        raise AuthError(f"Secret {secret_id!r} has no string value")
                except Exception as e:  # pragma: no cover - error paths
                    self._log.debug("Failed to resolve AWS secret %s: %s", secret_id, e)
                    missing.append(logical)
                    continue
                self._cache[logical] = val
                out[logical] = val
                self._log.debug(
                    "Resolved AWS SM secret %s (logical %s)=%s",
                    secret_id,
                    logical,
                    _redact(val),
                )
        elif source == "ssm":
            client = self._client("ssm")
            for logical in names:
                if logical in self._cache:
                    out[logical] = self._cache[logical]
                    continue
                param_name = mapping.get(logical, logical)
                try:
                    resp = client.get_parameter(Name=param_name, WithDecryption=True)
                    val = resp.get("Parameter", {}).get("Value")
                    if val is None:
                        raise AuthError(f"Parameter {param_name!r} has no value")
                except Exception as e:  # pragma: no cover - error paths
                    self._log.debug("Failed to resolve AWS SSM param %s: %s", param_name, e)
                    missing.append(logical)
                    continue
                self._cache[logical] = val
                out[logical] = val
                self._log.debug(
                    "Resolved AWS SSM param %s (logical %s)=%s",
                    param_name,
                    logical,
                    _redact(val),
                )
        else:  # pragma: no cover - invalid config is not typical path
            raise AuthError(f"Unsupported AWS secret source: {_cfg_get(self.cfg, 'source')!r}")

        if missing:
            raise AuthError(f"Missing AWS secrets for: {', '.join(missing)}")
        return out


def build_provider(auth: AuthConfig | dict, *, env: Mapping[str, str] | None = None) -> SecretProvider:
    prov = getattr(auth, "provider", None)
    if prov is None and isinstance(auth, dict):
        prov = auth.get("provider")

    if prov == "env":
        env_cfg = getattr(auth, "env", None) if not isinstance(auth, dict) else auth.get("env")
        return EnvSecretProvider(env_cfg, env)
    if prov == "azure_key_vault":
        akv_cfg = getattr(auth, "azure_key_vault", None) if not isinstance(auth, dict) else auth.get("azure_key_vault")
        if not akv_cfg:
            raise AuthError("azure_key_vault provider requires azure_key_vault config block")
        return AzureKeyVaultProvider(akv_cfg)
    if prov == "aws_secrets":
        aws_cfg = getattr(auth, "aws_secrets", None) if not isinstance(auth, dict) else auth.get("aws_secrets")
        if not aws_cfg:
            raise AuthError("aws_secrets provider requires aws_secrets config block")
        return AwsSecretsProvider(aws_cfg)
    raise AuthError(f"Unsupported auth provider: {prov}")


__all__ = [
    "AuthError",
    "SecretProvider",
    "EnvSecretProvider",
    "AzureKeyVaultProvider",
    "AwsSecretsProvider",
    "build_provider",
]
