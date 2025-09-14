import io
import os
import sys
import tempfile
import types
import unittest
import logging


class TestAuthProviders(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self._old_env = dict(os.environ)
        self._saved_modules = dict(sys.modules)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)
        sys.modules.clear()
        sys.modules.update(self._saved_modules)

    def test_env_provider_reads_env_and_dotenv(self):
        from fmf.auth import EnvSecretProvider

        os.environ["MY_SECRET"] = "shh"
        fd, path = tempfile.mkstemp()
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write("MY_SECRET2=wow\n# comment\nEMPTY=\n")

        provider = EnvSecretProvider({"file": path})

        # capture logs to ensure secrets are redacted
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        logger = logging.getLogger("fmf.auth.providers")
        # Use module-level logger in providers via root, ensure we capture debug
        logging.getLogger().handlers = []
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)

        resolved = provider.resolve(["MY_SECRET", "MY_SECRET2"])
        self.assertEqual(resolved["MY_SECRET"], "shh")
        self.assertEqual(resolved["MY_SECRET2"], "wow")

        logs = buf.getvalue()
        self.assertNotIn("shh", logs)
        self.assertNotIn("wow", logs)

    def _mock_azure_modules(self):
        # Create fake azure.identity.DefaultAzureCredential and SecretClient
        azure_pkg = types.ModuleType("azure")
        identity_pkg = types.ModuleType("azure.identity")
        keyvault_pkg = types.ModuleType("azure.keyvault")
        secrets_pkg = types.ModuleType("azure.keyvault.secrets")

        class DefaultAzureCredential:  # noqa: D401 - simple stub
            def __init__(self):
                pass

        class Secret:
            def __init__(self, value):
                self.value = value

        class SecretClient:
            def __init__(self, vault_url, credential):
                self._data = {"kv-name": "kv-value"}

            def get_secret(self, name):
                return Secret(self._data[name])

        identity_pkg.DefaultAzureCredential = DefaultAzureCredential
        secrets_pkg.SecretClient = SecretClient
        sys.modules["azure"] = azure_pkg
        sys.modules["azure.identity"] = identity_pkg
        sys.modules["azure.keyvault"] = keyvault_pkg
        sys.modules["azure.keyvault.secrets"] = secrets_pkg

    def test_azure_kv_provider_uses_mapping_and_redacts_logs(self):
        self._mock_azure_modules()

        from fmf.auth import AzureKeyVaultProvider

        provider = AzureKeyVaultProvider(
            {"vault_url": "https://fake.vault.azure.net/", "secret_mapping": {"OPENAI_API_KEY": "kv-name"}}
        )

        buf = io.StringIO()
        logging.getLogger().handlers = [logging.StreamHandler(buf)]
        logging.getLogger().setLevel(logging.DEBUG)

        res = provider.resolve(["OPENAI_API_KEY"])
        self.assertEqual(res["OPENAI_API_KEY"], "kv-value")
        logs = buf.getvalue()
        self.assertNotIn("kv-value", logs)
        self.assertIn("****", logs)

    def _mock_boto3(self, source="secretsmanager"):
        boto3 = types.ModuleType("boto3")

        class SMClient:
            def __init__(self, *args, **kwargs):
                pass

            def get_secret_value(self, SecretId):
                return {"SecretString": "sm-secret"}

        class SSMClient:
            def __init__(self, *args, **kwargs):
                pass

            def get_parameter(self, Name, WithDecryption):
                return {"Parameter": {"Value": "ssm-secret"}}

        def client(service, region_name=None):
            if service == "secretsmanager":
                return SMClient()
            if service == "ssm":
                return SSMClient()
            raise ValueError(service)

        boto3.client = client
        sys.modules["boto3"] = boto3

    def test_aws_provider_secretsmanager(self):
        self._mock_boto3()

        from fmf.auth import AwsSecretsProvider

        provider = AwsSecretsProvider({"region": "us-east-1", "source": "secretsmanager", "secret_mapping": {"A": "a/name"}})
        buf = io.StringIO()
        logging.getLogger().handlers = [logging.StreamHandler(buf)]
        logging.getLogger().setLevel(logging.DEBUG)

        res = provider.resolve(["A"])
        self.assertEqual(res["A"], "sm-secret")
        self.assertNotIn("sm-secret", buf.getvalue())

    def test_aws_provider_ssm(self):
        self._mock_boto3(source="ssm")

        from fmf.auth import AwsSecretsProvider

        provider = AwsSecretsProvider({"region": "us-east-1", "source": "ssm", "secret_mapping": {"B": "/params/b"}})
        buf = io.StringIO()
        logging.getLogger().handlers = [logging.StreamHandler(buf)]
        logging.getLogger().setLevel(logging.DEBUG)

        res = provider.resolve(["B"])
        self.assertEqual(res["B"], "ssm-secret")
        self.assertNotIn("ssm-secret", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
