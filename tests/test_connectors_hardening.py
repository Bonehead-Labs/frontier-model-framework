from __future__ import annotations

import os
import sys
import types
import unittest


class TestConnectorHardening(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_local_connector_uses_run_context(self) -> None:
        from fmf.connectors.local import LocalConnector
        from fmf.core.interfaces import RunContext

        ctx = RunContext(run_id="test-run")
        conn = LocalConnector(name="local", root=".")
        # Should iterate without raising even when selector provided via context (unused)
        refs = list(conn.list(selector=["**/*.py"], context=ctx))
        self.assertIsInstance(refs, list)

    def test_s3_open_wraps_body_with_context_manager(self) -> None:
        from fmf.connectors.s3 import S3Connector

        class DummyBody:
            def __init__(self) -> None:
                self.closed = False

            def read(self, *_, **__):
                return b"data"

            def close(self):
                self.closed = True

        class DummyClient:
            def __init__(self) -> None:
                self.calls = {"list": 0, "get": 0, "head": 0}

            def list_objects_v2(self, **kwargs):
                self.calls["list"] += 1
                return {"Contents": [{"Key": "foo.txt"}]}

            def get_object(self, **kwargs):
                self.calls["get"] += 1
                return {"Body": DummyBody()}

            def head_object(self, **kwargs):
                self.calls["head"] += 1
                return {"ContentLength": 4, "LastModified": None, "ETag": "etag"}

        # Stub boto3 client
        module = types.SimpleNamespace(client=lambda service, region_name=None: DummyClient())
        original_boto3 = sys.modules.get("boto3")
        sys.modules["boto3"] = module  # type: ignore
        try:
            conn = S3Connector(name="s3", bucket="b")
            ref = next(iter(conn.list()))
            stream = conn.open(ref)
            with stream as handle:
                self.assertEqual(handle.read(), b"data")
            self.assertTrue(stream._body.closed)  # type: ignore[attr-defined]
        finally:
            if original_boto3 is None:
                sys.modules.pop("boto3", None)
            else:
                sys.modules["boto3"] = original_boto3


if __name__ == "__main__":
        unittest.main()
