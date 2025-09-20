from __future__ import annotations

import sys
import types
import unittest
from typing import Any

from fmf.core.interfaces import ExportSpec


class TestExportWriteModes(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_boto3 = sys.modules.get("boto3")

    def tearDown(self) -> None:
        if self._orig_boto3 is None:
            sys.modules.pop("boto3", None)
        else:
            sys.modules["boto3"] = self._orig_boto3

    def _install_stub(self) -> tuple[list[tuple[str, dict[str, str]]], Any]:
        calls: list[tuple[str, dict[str, str]]] = []

        class DummyClient:
            def __init__(self) -> None:
                self.storage: dict[str, dict[str, Any]] = {}

            def put_object(self, **kwargs):
                calls.append(("put", kwargs))
                key = kwargs["Key"]
                self.storage[key] = {
                    "Body": kwargs["Body"],
                    "Metadata": kwargs.get("Metadata", {}),
                }

            def copy_object(self, **kwargs):
                calls.append(("copy", kwargs))
                src_key = kwargs["CopySource"]["Key"]
                dest_key = kwargs["Key"]
                self.storage[dest_key] = self.storage[src_key]

            def delete_object(self, **kwargs):
                calls.append(("delete", kwargs))
                self.storage.pop(kwargs["Key"], None)

            def head_object(self, **kwargs):
                key = kwargs["Key"]
                payload = self.storage.get(key, {})
                return {
                    "ContentLength": len(payload.get("Body", b"")),
                    "Metadata": payload.get("Metadata", {}),
                }

        client = DummyClient()
        sys.modules["boto3"] = types.SimpleNamespace(client=lambda *_args, **_kwargs: client)  # type: ignore
        return calls, client

    def test_append_mode_generates_unique_keys(self) -> None:
        calls, client = self._install_stub()
        from fmf.exporters.s3 import S3Exporter

        spec = ExportSpec(
            name="s3",
            type="s3",
            format="jsonl",
            write_mode="append",
            options={"bucket": "demo", "prefix": "runs/"},
        )
        exporter = S3Exporter(spec=spec)
        exporter.write([{"a": 1}], context={"run_id": "r1"})
        put_calls = [c for c in calls if c[0] == "put"]
        self.assertTrue(any(c[1]["Key"].startswith("runs/") for c in put_calls))
        self.assertTrue(all("ContentMD5" in c[1] for c in put_calls))

    def test_overwrite_mode_uses_copy(self) -> None:
        calls, client = self._install_stub()
        from fmf.exporters.s3 import S3Exporter

        spec = ExportSpec(
            name="s3",
            type="s3",
            format="jsonl",
            write_mode="overwrite",
            options={"bucket": "demo", "prefix": "runs/"},
        )
        exporter = S3Exporter(spec=spec)
        exporter.write([{"a": 1}], context={"run_id": "r1", "filename": "results"})
        put_temp = [c for c in calls if c[0] == "put"]
        copy_calls = [c for c in calls if c[0] == "copy"]
        delete_calls = [c for c in calls if c[0] == "delete"]
        self.assertTrue(any(".tmp-" in c[1]["Key"] for c in put_temp))
        self.assertTrue(copy_calls)
        self.assertTrue(delete_calls)
        self.assertTrue(all("ContentMD5" in c[1] if c[0] == "put" else True for c in calls))
        self.assertTrue(all("CopySourceIfMatch" in c[1] for c in copy_calls))
        # simulate head verification
        head = client.head_object(Bucket="demo", Key="runs/results.jsonl")
        final_blob = client.storage["runs/results.jsonl"]["Body"]
        self.assertEqual(head["ContentLength"], len(final_blob))
        self.assertIn("fmf-sha256", head["Metadata"])

    def test_upsert_not_supported(self) -> None:
        self._install_stub()
        from fmf.exporters.s3 import S3Exporter

        spec = ExportSpec(
            name="s3",
            type="s3",
            format="jsonl",
            write_mode="upsert",
            options={"bucket": "demo"},
        )
        exporter = S3Exporter(spec=spec)
        with self.assertRaises(Exception):
            exporter.write([{"a": 1}])


if __name__ == "__main__":
    unittest.main()
