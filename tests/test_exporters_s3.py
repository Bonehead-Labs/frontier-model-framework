import os
import sys
import types
import unittest


class TestS3Exporter(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self._saved = dict(sys.modules)

        # Fake boto3
        boto3 = types.ModuleType("boto3")
        out = {"puts": []}

        class S3:
            def put_object(self, **kwargs):
                out["puts"].append(kwargs)

        def client(name):
            assert name == "s3"
            return S3()

        boto3.client = client
        sys.modules["boto3"] = boto3
        self._out = out

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._saved)

    def test_write_jsonl_gzip_with_run_id(self):
        from fmf.exporters.s3 import S3Exporter

        exp = S3Exporter(name="s3_results", bucket="b", prefix="fmf/outputs/${run_id}/", format="jsonl", compression="gzip", partition_by=["date"])
        payload = b"{\"a\":1}\n{\"a\":2}\n"
        res = exp.write(payload, context={"run_id": "r1"})
        self.assertTrue(self._out["puts"])
        put = self._out["puts"][0]
        self.assertEqual(put["Bucket"], "b")
        self.assertIn("fmf/outputs/r1/", put["Key"])
        self.assertTrue(put["Key"].endswith(".jsonl.gz"))
        self.assertTrue(res.paths[0].startswith("s3://b/"))


if __name__ == "__main__":
    unittest.main()

