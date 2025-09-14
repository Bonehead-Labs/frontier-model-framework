import os
import sys
import tempfile
import textwrap
import unittest


class TestProfilesConfig(unittest.TestCase):
    def setUp(self):
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

    def test_profiles_active_field(self):
        from fmf.config.loader import load_config

        yaml_path = self._write_yaml(
            """
            project: fmf
            artefacts_dir: artefacts
            profiles:
              active: aws_lambda
              aws_lambda:
                artefacts_dir: s3://bucket/fmf/artefacts
                export: { default_sink: s3_results }
            """
        )
        cfg = load_config(yaml_path)
        as_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg
        self.assertEqual(as_dict["artefacts_dir"], "s3://bucket/fmf/artefacts")
        self.assertEqual(as_dict["export"]["default_sink"], "s3_results")

    def test_profiles_env_FMF_PROFILE(self):
        from fmf.config.loader import load_config

        yaml_path = self._write_yaml(
            """
            project: fmf
            profiles:
              local:
                artefacts_dir: artefacts
              aws_batch:
                artefacts_dir: s3://bucket/fmf/artefacts
            """
        )
        os.environ["FMF_PROFILE"] = "aws_batch"
        cfg = load_config(yaml_path)
        as_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else cfg
        self.assertEqual(as_dict["artefacts_dir"], "s3://bucket/fmf/artefacts")


if __name__ == "__main__":
    unittest.main()

