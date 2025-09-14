from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable

from .base import ExportError, ExportResult


class DynamoDBExporter:
    def __init__(self, *, name: str, table: str, region: str | None = None, key_fields: list[str] | None = None) -> None:
        self.name = name
        self.table = table
        self.region = region
        self.key_fields = key_fields or []
        self._client = None

    def _ddb(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore
        except Exception as e:
            raise ExportError("boto3 not installed. Install extras: pip install '.[aws]'") from e
        self._client = boto3.client("dynamodb", region_name=self.region)
        return self._client

    def _to_ddb_item(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        item: Dict[str, Any] = {}
        for k, v in rec.items():
            if v is None:
                continue
            if isinstance(v, (int, float)):
                item[k] = {"N": str(v)}
            elif isinstance(v, bool):
                item[k] = {"BOOL": v}
            else:
                item[k] = {"S": json.dumps(v) if isinstance(v, (dict, list)) else str(v)}
        return item

    def write(
        self,
        records: Iterable[Dict[str, Any]] | bytes | str,
        *,
        schema: dict[str, Any] | None = None,
        mode: str = "upsert",
        key_fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ExportResult:
        if not isinstance(records, (bytes, str)):
            # batch write in chunks of 25
            items = list(records)
            total = 0
            for i in range(0, len(items), 25):
                batch = items[i : i + 25]
                req = {
                    self.table: [
                        {"PutRequest": {"Item": self._to_ddb_item(rec)}} for rec in batch
                    ]
                }
                resp = self._ddb().batch_write_item(RequestItems=req)
                unprocessed = resp.get("UnprocessedItems", {}).get(self.table, [])
                backoff = 0.2
                while unprocessed:
                    time.sleep(backoff)
                    resp = self._ddb().batch_write_item(RequestItems={self.table: unprocessed})
                    unprocessed = resp.get("UnprocessedItems", {}).get(self.table, [])
                    backoff = min(backoff * 2, 2.0)
                total += len(batch)
            return ExportResult(count=total, paths=[f"dynamodb://{self.table}"])
        else:
            raise ExportError("DynamoDB exporter expects iterable of dict records, not bytes/str")

    def finalize(self) -> None:
        return None


__all__ = ["DynamoDBExporter"]

