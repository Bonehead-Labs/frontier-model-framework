import os
import sys
import unittest


@unittest.skipUnless(__import__("importlib").import_module("importlib").util.find_spec("moto") is not None, "moto not installed")
class TestS3ConnectorWithMoto(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_list_and_open_with_moto(self):
        from moto import mock_aws
        import boto3
        from fmf.connectors.s3 import S3Connector

        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            s3.put_object(Bucket="test-bucket", Key="raw/a.md", Body=b"hello")
            s3.put_object(Bucket="test-bucket", Key="raw/b.txt", Body=b"bye")

            c = S3Connector(name="s3_raw", bucket="test-bucket", prefix="raw/", region="us-east-1")
            refs = list(c.list(selector=["**/*.md"]))
            self.assertEqual(len(refs), 1)
            r = refs[0]
            with c.open(r) as f:
                self.assertEqual(f.read(), b"hello")


if __name__ == "__main__":
    unittest.main()

