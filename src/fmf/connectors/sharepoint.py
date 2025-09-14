from __future__ import annotations

import io
import time
import urllib.parse as _url
from typing import IO, Iterable, Optional

from .base import ConnectorError, ResourceInfo, ResourceRef


class SharePointConnector:
    """SharePoint connector using Microsoft Graph SDK.

    - Lists and downloads files from a given site + drive + root_path using Graph paths
    - Auth via azure-identity DefaultAzureCredential
    - Handles basic 429 throttling via exponential backoff
    """

    def __init__(
        self,
        *,
        name: str,
        site_url: str,
        drive: str,
        root_path: Optional[str] = None,
        auth_profile: Optional[str] = None,
    ) -> None:
        self.name = name
        self.site_url = site_url
        self.drive = drive
        self.root_path = (root_path or "").strip("/")
        self.auth_profile = auth_profile
        self._client = None

    def _client_or_raise(self):  # pragma: no cover - exercised via tests with monkeypatching
        if self._client is not None:
            return self._client
        try:
            from msgraph import GraphServiceClient  # type: ignore
            from azure.identity import DefaultAzureCredential  # type: ignore
        except Exception as e:
            raise ConnectorError(
                "msgraph SDK and azure-identity are required. Install extras: pip install 'msgraph-sdk azure-identity'"
            ) from e
        cred = DefaultAzureCredential()
        self._client = GraphServiceClient(credential=cred, scopes=["https://graph.microsoft.com/.default"])  # type: ignore[call-arg]
        return self._client

    def _retry(self, func, *args, **kwargs):
        delay = 0.5
        for _ in range(6):
            try:
                return func(*args, **kwargs)
            except Exception as e:  # naive throttling/backoff handler
                status = getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
                if status == 429:
                    time.sleep(delay)
                    delay = min(delay * 2, 8.0)
                    continue
                raise

    def _parse_site(self) -> tuple[str, str]:
        # https://contoso.sharepoint.com/sites/HR -> host, path
        u = _url.urlparse(self.site_url)
        host = u.hostname or ""
        path = u.path.lstrip("/")
        return host, path

    def _resolve_ids(self) -> tuple[str, str]:  # pragma: no cover - tests patch around
        client = self._client_or_raise()
        host, path = self._parse_site()
        # GET /sites/{host}:/{path}
        site = self._retry(lambda: client.api(f"/sites/{host}:/{path}").get())
        site_id = site.get("id") if isinstance(site, dict) else getattr(site, "id", None)
        if not site_id:
            raise ConnectorError("Failed to resolve site id")
        drives = self._retry(lambda: client.api(f"/sites/{site_id}/drives").get())
        values = drives.get("value") if isinstance(drives, dict) else getattr(drives, "value", [])
        drive_id = None
        for d in values or []:
            name = d.get("name") if isinstance(d, dict) else getattr(d, "name", None)
            if name == self.drive:
                drive_id = d.get("id") if isinstance(d, dict) else getattr(d, "id", None)
                break
        if not drive_id:
            raise ConnectorError(f"Drive {self.drive!r} not found")
        return site_id, drive_id

    def _graph_list_children(self, site_id: str, drive_id: str, rel_path: str) -> list[dict]:  # pragma: no cover - tests patch
        client = self._client_or_raise()
        if rel_path:
            resp = self._retry(lambda: client.api(f"/sites/{site_id}/drives/{drive_id}/root:/{rel_path}:/children").get())
        else:
            resp = self._retry(lambda: client.api(f"/sites/{site_id}/drives/{drive_id}/root/children").get())
        return resp.get("value") if isinstance(resp, dict) else getattr(resp, "value", [])

    def _graph_download(self, site_id: str, drive_id: str, rel_path: str):  # pragma: no cover - tests patch
        client = self._client_or_raise()
        return self._retry(lambda: client.api(f"/sites/{site_id}/drives/{drive_id}/root:/{rel_path}:/content").get())

    def _graph_item_props(self, site_id: str, drive_id: str, rel_path: str):  # pragma: no cover - tests patch
        client = self._client_or_raise()
        return self._retry(lambda: client.api(f"/sites/{site_id}/drives/{drive_id}/root:/{rel_path}").get())

    def list(self, selector: list[str] | None = None) -> Iterable[ResourceRef]:
        import fnmatch

        site_id, drive_id = self._resolve_ids()
        patterns = selector or ["**/*"]

        stack = [self.root_path]
        while stack:
            cur = stack.pop()
            children = self._graph_list_children(site_id, drive_id, cur)
            for item in children or []:
                name = item.get("name")
                is_folder = "folder" in item
                rel = f"{cur}/{name}".strip("/") if cur else name
                if is_folder:
                    stack.append(rel)
                    continue
                within = rel[len(self.root_path) + 1 :] if self.root_path and rel.startswith(self.root_path + "/") else rel
                if not any(
                    fnmatch.fnmatchcase(within, pat) or (pat.startswith("**/") and fnmatch.fnmatchcase(within, pat[3:]))
                    for pat in patterns
                ):
                    continue
                yield ResourceRef(id=within, uri=f"sharepoint:/sites/{site_id}/drives/{drive_id}/root:/{rel}", name=name)

    def open(self, ref: ResourceRef, mode: str = "rb") -> IO[bytes]:
        if "r" not in mode:
            raise ConnectorError("SharePointConnector only supports reading")
        site_id, drive_id = self._resolve_ids()
        rel = (self.root_path + "/" + ref.id).strip("/") if self.root_path else ref.id
        data = self._graph_download(site_id, drive_id, rel)
        if isinstance(data, (bytes, bytearray)):
            return io.BytesIO(data)
        return data

    def info(self, ref: ResourceRef) -> ResourceInfo:
        import datetime as dt

        site_id, drive_id = self._resolve_ids()
        rel = (self.root_path + "/" + ref.id).strip("/") if self.root_path else ref.id
        props = self._graph_item_props(site_id, drive_id, rel) or {}
        size = props.get("size") if isinstance(props, dict) else getattr(props, "size", None)
        lm = props.get("lastModifiedDateTime") if isinstance(props, dict) else getattr(props, "lastModifiedDateTime", None)
        etag = props.get("eTag") if isinstance(props, dict) else getattr(props, "eTag", None)
        modified_at = None
        if isinstance(lm, str):
            try:
                modified_at = dt.datetime.fromisoformat(lm.replace("Z", "+00:00"))
            except Exception:
                modified_at = None
        return ResourceInfo(
            source_uri=f"sharepoint:/sites/{site_id}/drives/{drive_id}/root:/{rel}",
            modified_at=modified_at,
            etag=etag,
            size=size,
        )


__all__ = ["SharePointConnector"]
