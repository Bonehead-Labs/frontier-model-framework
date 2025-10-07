"""Secret providers and auth backends."""

from .providers import (
    AuthError,
    SecretProvider,
    EnvSecretProvider,
    AzureKeyVaultProvider,
    AwsSecretsProvider,
    build_provider,
)
from .bootstrap import (
    bootstrap_aws_credentials,
    resolve_aws_credentials_from_provider,
)

__all__ = [
    "AuthError",
    "SecretProvider",
    "EnvSecretProvider",
    "AzureKeyVaultProvider",
    "AwsSecretsProvider",
    "build_provider",
    "bootstrap_aws_credentials",
    "resolve_aws_credentials_from_provider",
]
