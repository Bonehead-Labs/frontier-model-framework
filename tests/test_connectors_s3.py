import io
import os
import sys
import types
import unittest
import datetime as dt


class _FakeBody(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class TestS3Connector(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        self._saved_modules = dict(sys.modules)

        # Mock boto3 client
        boto3 = types.ModuleType("boto3")

        class FakeS3:
            def __init__(self):
                self._objects = {
                    "my-bucket": {
                        "raw/a.txt": b"A",
                        "raw/sub/b.md": b"BMD",
                        "other.txt": b"O",
                    }
                }

            def list_objects_v2(self, **kwargs):
                bucket = kwargs["Bucket"]
                prefix = kwargs.get("Prefix", "")
                keys = sorted([k for k in self._objects.get(bucket, {}) if k.startswith(prefix)])
                contents = [
                    {"Key": k, "Size": len(self._objects[bucket][k])} for k in keys
                ]
                return {"Contents": contents, "IsTruncated": False}

            def get_object(self, **kwargs):
                b = kwargs["Bucket"]
                k = kwargs["Key"]
                data = self._objects[b][k]
                return {"Body": _FakeBody(data)}

            def head_object(self, **kwargs):
                b = kwargs["Bucket"]
                k = kwargs["Key"]
                data = self._objects[b][k]
                return {
                    "ContentLength": len(data),
                    "LastModified": dt.datetime.now(dt.timezone.utc),
                    "ETag": "\"etag\"",
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": "alias/test",
                }

        def client(service, region_name=None):
            assert service == "s3"
            return FakeS3()

        boto3.client = client
        sys.modules["boto3"] = boto3

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._saved_modules)

    def test_list_filter_open_info(self):
        from fmf.connectors.s3 import S3Connector

        c = S3Connector(name="s3_raw", bucket="my-bucket", prefix="raw/")
        refs = list(c.list(selector=["**/*.md"]))
        self.assertEqual(len(refs), 1)
        r = refs[0]
        self.assertEqual(r.id, "sub/b.md")
        self.assertTrue(r.uri.startswith("s3://my-bucket/raw/"))

        # open
        with c.open(r) as f:
            self.assertEqual(f.read(), b"BMD")

        # info
        info = c.info(r)
        self.assertEqual(info.size, 3)
        self.assertEqual(info.etag, '"etag"')
        self.assertEqual(info.extra["sse"], "aws:kms")


if __name__ == "__main__":
    unittest.main()

