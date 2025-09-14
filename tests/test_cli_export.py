import io
import os
import sys
import tempfile
import textwrap
import types
import unittest


class TestCliExport(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def _write_yaml(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_cli_export_to_s3(self):
        import fmf.cli as cli

        # mock boto3 used by exporters.s3
        out = {"puts": []}

        class S3:
            def put_object(self, **kwargs):
                out["puts"].append(kwargs)

        sys.modules["boto3"] = types.SimpleNamespace(client=lambda name: S3())  # type: ignore

        tmpdir = tempfile.TemporaryDirectory()
        run_id = "r123"
        run_dir = os.path.join(tmpdir.name, run_id)
        os.makedirs(run_dir, exist_ok=True)
        input_path = os.path.join(run_dir, "outputs.jsonl")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write("{\"x\":1}\n")

        cfg = self._write_yaml(
            """
            project: fmf
            export:
              sinks:
                - name: s3_results
                  type: s3
                  bucket: b
                  prefix: fmf/outputs/${run_id}/
                  format: jsonl
                  compression: gzip
            """
        )

        rc = cli.main(["export", "--sink", "s3_results", "--input", input_path, "-c", cfg])
        self.assertEqual(rc, 0)
        self.assertTrue(out["puts"])  # put to S3 happened


if __name__ == "__main__":
    unittest.main()
