"""Bootstrap credential loading for accessing secret stores.

This module provides utilities for loading AWS credentials from .env files
before initializing auth providers that require AWS access (e.g., AWS Secrets Manager).

Design:
    Bootstrap credentials (AWS auth) → Application secrets (API keys)
    
    1. Load AWS credentials from .env file
    2. Set them in os.environ for boto3
    3. Build auth provider (can now access AWS Secrets Manager)
    4. Resolve application secrets (AZURE_OPENAI_API_KEY, etc.)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

_log = logging.getLogger(__name__)


def bootstrap_aws_credentials(auth_cfg: Any) -> None:
    """Load AWS credentials from .env into os.environ for boto3.
    
    This function implements the bootstrap phase of credential loading:
    - Loads .env file if configured
    - Extracts AWS credentials (access key, secret key, session token)
    - Sets them in os.environ so boto3 can find them
    
    This allows AWS-based auth providers (aws_secrets) to function, since
    they need AWS credentials to access AWS Secrets Manager.
    
    Args:
        auth_cfg: Auth configuration object or dict
        
    Design Pattern:
        .env file (bootstrap) → AWS Secrets Manager (application secrets)
        
    Example:
        # .env file contains:
        AWS_ACCESS_KEY_ID=AKIA...
        AWS_SECRET_ACCESS_KEY=...
        AWS_SESSION_TOKEN=...
        
        # After bootstrap, boto3 can access AWS Secrets Manager
        # to retrieve AZURE_OPENAI_API_KEY, etc.
    """
    if not auth_cfg:
        _log.debug("No auth config provided, skipping bootstrap")
        return
    
    # Extract .env file path from config
    env_cfg = None
    if isinstance(auth_cfg, dict):
        env_cfg = auth_cfg.get("env")
    else:
        env_cfg = getattr(auth_cfg, "env", None)
    
    if not env_cfg:
        _log.debug("No env config in auth, skipping .env bootstrap")
        return
    
    env_file = None
    if isinstance(env_cfg, dict):
        env_file = env_cfg.get("file")
    else:
        env_file = getattr(env_cfg, "file", None)
    
    if not env_file:
        _log.debug("No .env file configured, skipping bootstrap")
        return
    
    # Check if AWS credentials are already available (idempotent behavior)
    # Only log if we're actually loading new credentials
    already_loaded = []
    for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_REGION"]:
        if os.getenv(key):
            already_loaded.append(key)
    
    if len(already_loaded) >= 2:  # At least access key and secret key are needed
        _log.debug(f"AWS credentials already available: {', '.join(already_loaded)}")
        return
    
    # Load .env file using dotenv library
    try:
        from dotenv import load_dotenv
        _log.debug(f"Loading bootstrap credentials from {env_file}")
        load_dotenv(env_file)
    except ImportError:
        _log.warning("python-dotenv not installed, falling back to manual .env parsing")
        # Fall back to manual parsing if dotenv not available
        _load_env_file_manual(env_file)
    except Exception as e:
        _log.warning(f"Failed to load .env file {env_file}: {e}")
        return
    
    # Export AWS credentials to os.environ for boto3
    aws_keys = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_REGION", "AWS_DEFAULT_REGION"]
    loaded_keys = []
    
    for key in aws_keys:
        env_val = os.getenv(key)
        if env_val:
            # Use setdefault to not override existing environment variables
            os.environ.setdefault(key, env_val)
            loaded_keys.append(key)
    
    if loaded_keys:
        _log.info(f"Bootstrapped AWS credentials from .env: {', '.join(loaded_keys)}")
    else:
        _log.debug("No AWS credentials found in .env file")


def _load_env_file_manual(env_file: str) -> None:
    """Manually parse .env file if dotenv library not available.
    
    Simple parser that handles KEY=VALUE lines.
    """
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and val:
                    os.environ.setdefault(key, val)
    except FileNotFoundError:
        _log.warning(f".env file not found: {env_file}")
    except Exception as e:
        _log.warning(f"Failed to manually parse .env file: {e}")


def resolve_aws_credentials_from_provider(auth_provider: Any) -> Dict[str, str]:
    """Resolve AWS credentials from auth provider and export to os.environ.
    
    This is used when the auth provider itself can provide AWS credentials
    (e.g., when using 'env' provider with AWS keys in .env).
    
    Args:
        auth_provider: Auth provider instance with resolve() method
        
    Returns:
        Dict of resolved AWS credentials
        
    Note:
        This is separate from bootstrap because it's used when the auth
        provider is already built and we want to extract AWS creds from it.
    """
    if not auth_provider:
        return {}
    
    aws_creds = {}
    
    # Try to resolve AWS credentials
    try:
        resolved = auth_provider.resolve(["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"])
        ak = resolved.get("AWS_ACCESS_KEY_ID")
        sk = resolved.get("AWS_SECRET_ACCESS_KEY")
        if ak and sk:
            os.environ.setdefault("AWS_ACCESS_KEY_ID", ak)
            os.environ.setdefault("AWS_SECRET_ACCESS_KEY", sk)
            aws_creds["AWS_ACCESS_KEY_ID"] = ak
            aws_creds["AWS_SECRET_ACCESS_KEY"] = sk
            _log.debug("Resolved AWS access key and secret key from auth provider")
    except Exception as e:
        _log.debug(f"Could not resolve AWS access keys from auth provider: {e}")
    
    # Try to resolve session token (optional)
    try:
        token_resolved = auth_provider.resolve(["AWS_SESSION_TOKEN"])
        st = token_resolved.get("AWS_SESSION_TOKEN")
        if st:
            os.environ.setdefault("AWS_SESSION_TOKEN", st)
            aws_creds["AWS_SESSION_TOKEN"] = st
            _log.debug("Resolved AWS session token from auth provider")
    except Exception as e:
        _log.debug(f"Could not resolve AWS session token from auth provider: {e}")
    
    # Try to resolve region (optional)
    try:
        region_resolved = auth_provider.resolve(["AWS_REGION"])
        region = region_resolved.get("AWS_REGION")
        if region:
            os.environ.setdefault("AWS_REGION", region)
            os.environ.setdefault("AWS_DEFAULT_REGION", region)
            aws_creds["AWS_REGION"] = region
            _log.debug(f"Resolved AWS region from auth provider: {region}")
    except Exception as e:
        _log.debug(f"Could not resolve AWS region from auth provider: {e}")
    
    return aws_creds


__all__ = [
    "bootstrap_aws_credentials",
    "resolve_aws_credentials_from_provider",
]
