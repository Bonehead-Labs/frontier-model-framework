"""Illustrate append vs overwrite semantics for the S3 exporter using a stubbed boto3 client."""

from __future__ import annotations

import sys
import types

from fmf.core.interfaces import ExportSpec
from fmf.exporters.s3 import S3Exporter


def install_stub() -> list[str]:
    calls: list[str] = []

    class DummyClient:
        def put_object(self, **kwargs):
            calls.append(f"put:{kwargs['Key']}")

        def copy_object(self, **kwargs):
            calls.append(f"copy:{kwargs['Key']}")

        def delete_object(self, **kwargs):
            calls.append(f"delete:{kwargs['Key']}")

    sys.modules["boto3"] = types.SimpleNamespace(client=lambda *_args, **_kwargs: DummyClient())  # type: ignore
    return calls


def main() -> None:
    original = sys.modules.get("boto3")
    calls = install_stub()
    try:
        append_spec = ExportSpec(name="s3", type="s3", format="jsonl", write_mode="append", options={"bucket": "demo", "prefix": "runs/"})
        append_exporter = S3Exporter(spec=append_spec)
        append_exporter.write([{"row": 1}], context={"run_id": "r-001"})

        overwrite_spec = ExportSpec(name="s3", type="s3", format="jsonl", write_mode="overwrite", options={"bucket": "demo", "prefix": "runs/"})
        overwrite_exporter = S3Exporter(spec=overwrite_spec)
        overwrite_exporter.write([{"row": 1}], context={"run_id": "r-001", "filename": "latest"})
    finally:
        if original is None:
            sys.modules.pop("boto3", None)
        else:
            sys.modules["boto3"] = original

    for call in calls:
        print(call)


if __name__ == "__main__":
    main()
