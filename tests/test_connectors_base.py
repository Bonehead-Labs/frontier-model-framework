import os
import sys
import unittest
import datetime as dt


class TestConnectorBaseTypes(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_resource_types_exist_and_have_fields(self):
        from fmf.connectors import ResourceRef, ResourceInfo

        r = ResourceRef(id="a/b.txt", uri="file:///tmp/a/b.txt", name="b.txt")
        self.assertEqual(r.id, "a/b.txt")
        self.assertTrue(r.uri.startswith("file://"))
        self.assertEqual(r.name, "b.txt")

        now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
        info = ResourceInfo(source_uri=r.uri, modified_at=now, etag="abcd", size=42, extra={"k": "v"})
        self.assertEqual(info.source_uri, r.uri)
        self.assertEqual(info.size, 42)
        self.assertEqual(info.etag, "abcd")
        self.assertIn("k", info.extra)


if __name__ == "__main__":
    unittest.main()

