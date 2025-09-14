import os
import sys
import types
import unittest


class TestDynamoDBExporter(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self._saved = dict(sys.modules)

        # Fake boto3
        boto3 = types.ModuleType("boto3")
        out = {"batches": []}

        class DDB:
            def batch_write_item(self, **kwargs):
                out["batches"].append(kwargs)
                return {"UnprocessedItems": {}}

        def client(name, region_name=None):
            assert name == "dynamodb"
            return DDB()

        boto3.client = client
        sys.modules["boto3"] = boto3
        self._out = out

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._saved)

    def test_write_items_batches(self):
        from fmf.exporters.dynamodb import DynamoDBExporter

        exp = DynamoDBExporter(name="ddb", table="tbl", region="us-east-1")
        records = [{"id": i, "value": f"v{i}"} for i in range(30)]
        res = exp.write(records)
        # Should have processed in two batches (25 + 5)
        self.assertGreaterEqual(len(self._out["batches"]), 2)
        self.assertEqual(res.count, 30)


if __name__ == "__main__":
    unittest.main()

