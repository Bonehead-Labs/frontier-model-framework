import json
import os
import sys
import tempfile
import textwrap
import types
import unittest


class TestCliExportRecords(unittest.TestCase):
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

    def test_cli_export_to_dynamodb_from_jsonl(self):
        import fmf.cli as cli

        # mock boto3 used by exporters.dynamodb
        out = {"batches": []}

        class DDB:
            def batch_write_item(self, **kwargs):
                out["batches"].append(kwargs)
                return {"UnprocessedItems": {}}

        sys.modules["boto3"] = types.SimpleNamespace(client=lambda name, region_name=None: DDB())  # type: ignore

        tmpdir = tempfile.TemporaryDirectory()
        run_id = "r123"
        run_dir = os.path.join(tmpdir.name, run_id)
        os.makedirs(run_dir, exist_ok=True)
        input_path = os.path.join(run_dir, "outputs.jsonl")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"id": 1, "v": "a"}) + "\n")
            f.write(json.dumps({"id": 2, "v": "b"}) + "\n")

        cfg = self._write_yaml(
            """
            project: fmf
            export:
              sinks:
                - name: ddb
                  type: dynamodb
                  table: tbl
                  region: us-east-1
            """
        )

        rc = cli.main(["export", "--sink", "ddb", "--input", input_path, "-c", cfg])
        self.assertEqual(rc, 0)
        self.assertTrue(out["batches"])  # batches sent

        tmpdir.cleanup()

    def test_cli_export_parquet_input_without_pyarrow(self):
        import fmf.cli as cli

        # Create a dummy parquet path (we won't write a real parquet file)
        tmpdir = tempfile.TemporaryDirectory()
        input_path = os.path.join(tmpdir.name, "data.parquet")
        with open(input_path, "wb") as f:
            f.write(b"not-a-real-parquet")

        cfg = self._write_yaml(
            """
            project: fmf
            export:
              sinks:
                - name: ddb
                  type: dynamodb
                  table: tbl
            """
        )

        # Remove pyarrow if present to force the error path
        sys.modules.pop("pyarrow", None)
        sys.modules.pop("pyarrow.parquet", None)

        rc = 0
        try:
            rc = cli.main(["export", "--sink", "ddb", "--input", input_path, "-c", cfg])
        except SystemExit as e:
            rc = e.code
        self.assertNotEqual(rc, 0)

        tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()

