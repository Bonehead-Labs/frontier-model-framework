import os
import sys
import types
import unittest


class _S3Out:
    def __init__(self):
        self.puts = []


class _S3:
    def __init__(self, out):
        self._out = out

    def put_object(self, **kwargs):
        self._out.puts.append(kwargs)


class TestS3ExporterFormats(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        # Mock boto3
        self._saved = dict(sys.modules)
        self._out = _S3Out()
        boto3 = types.ModuleType("boto3")
        boto3.client = lambda name: _S3(self._out)
        sys.modules["boto3"] = boto3

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._saved)

    def test_csv_from_records(self):
        from fmf.exporters.s3 import S3Exporter

        exp = S3Exporter(name="s3", bucket="b", prefix="p/${run_id}/", format="csv")
        recs = [{"a": 1, "b": 2}, {"a": 3}]
        res = exp.write(recs, context={"run_id": "r1"})
        self.assertTrue(self._out.puts)
        put = self._out.puts[0]
        self.assertTrue(put["Key"].endswith(".csv"))
        body = put["Body"].decode("utf-8")
        lines = [l for l in body.splitlines() if l]
        header = lines[0]
        self.assertIn("a", header)
        self.assertIn("b", header)
        self.assertGreaterEqual(len(lines), 3)  # header + 2 rows

    def test_csv_from_jsonl_bytes(self):
        from fmf.exporters.s3 import S3Exporter

        exp = S3Exporter(name="s3", bucket="b", prefix="p/${run_id}/", format="csv")
        payload = b'{"a":1}\n{"a":2,"b":3}\n'
        res = exp.write(payload, context={"run_id": "r1"})
        put = self._out.puts[-1]
        body = put["Body"].decode("utf-8")
        self.assertIn("a", body.splitlines()[0])
        self.assertIn("b", body.splitlines()[0])

    def test_parquet_with_fake_pyarrow(self):
        # Provide a fake pyarrow to exercise the parquet branch without dependency
        class FakePA(types.ModuleType):
            def __init__(self):
                super().__init__("pyarrow")

            class Table:
                @staticmethod
                def from_pylist(rows):
                    return rows

        class FakePQ(types.ModuleType):
            def __init__(self):
                super().__init__("pyarrow.parquet")

            @staticmethod
            def write_table(table, bio):
                bio.write(b"PARQUET")

        sys.modules["pyarrow"] = FakePA()
        sys.modules["pyarrow.parquet"] = FakePQ()

        from fmf.exporters.s3 import S3Exporter

        exp = S3Exporter(name="s3", bucket="b", prefix="p/${run_id}/", format="parquet")
        recs = [{"a": 1}, {"a": 2}]
        res = exp.write(recs, context={"run_id": "r1"})
        put = self._out.puts[-1]
        self.assertTrue(put["Key"].endswith(".parquet"))
        self.assertIn(b"PARQUET", put["Body"])  # body written by fake writer


if __name__ == "__main__":
    unittest.main()

