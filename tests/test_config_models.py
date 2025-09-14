import os
import sys
import tempfile
import textwrap
import unittest


class TestConfigModels(unittest.TestCase):
    def setUp(self):
        # Allow importing from src without installation
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self._old_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)

    def _write_yaml(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_load_basic_yaml(self):
        from fmf.config.loader import load_config

        yaml_path = self._write_yaml(
            """
            project: frontier-model-framework
            run_profile: default
            artefacts_dir: artefacts
            auth:
              provider: env
            connectors:
              - name: local_docs
                type: local
                root: ./data
            inference:
              provider: azure_openai
              azure_openai:
                endpoint: https://example.openai.azure.com/
                api_version: 2024-02-15-preview
                deployment: gpt-4o-mini
                temperature: 0.2
            """
        )

        cfg = load_config(yaml_path)
        # Whether cfg is a Pydantic model or dict, support attribute/dict access test compatibly
        as_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg

        self.assertEqual(as_dict["project"], "frontier-model-framework")
        self.assertEqual(as_dict["auth"]["provider"], "env")
        self.assertEqual(as_dict["inference"]["provider"], "azure_openai")
        self.assertIn("azure_openai", as_dict["inference"])  # nested provider block present

    def test_env_override_with_double_underscore(self):
        from fmf.config.loader import load_config

        yaml_path = self._write_yaml(
            """
            project: frontier-model-framework
            inference:
              provider: azure_openai
              azure_openai:
                endpoint: https://example
                api_version: 2024
                deployment: d
                temperature: 0.1
            """
        )

        os.environ["FMF_INFERENCE__AZURE_OPENAI__TEMPERATURE"] = "0.5"
        cfg = load_config(yaml_path)
        as_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg
        self.assertAlmostEqual(as_dict["inference"]["azure_openai"]["temperature"], 0.5)


if __name__ == "__main__":
    unittest.main()
