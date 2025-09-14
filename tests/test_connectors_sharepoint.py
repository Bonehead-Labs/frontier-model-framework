import io
import os
import sys
import unittest


class TestSharePointConnector(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_list_open_info_with_fake_graph(self):
        from fmf.connectors import sharepoint as sp_mod
        from fmf.connectors.sharepoint import SharePointConnector

        fake_fs = {
            "Policies/file1.txt": b"abc",
            "Policies/sub/file2.md": b"md",
        }

        c = SharePointConnector(
            name="sp_policies",
            site_url="https://contoso.sharepoint.com/sites/Policies",
            drive="Documents",
            root_path="Policies",
        )

        # Patch Graph resolution and operations
        c._resolve_ids = lambda: ("site123", "drive456")

        def list_children(site_id, drive_id, rel):
            rel = rel.strip("/")
            # return folder/file entries for Graph shape
            children = []
            if not rel or rel == "Policies":
                children.append({"name": "file1.txt", "file": {}})
                children.append({"name": "sub", "folder": {}})
            if rel == "Policies/sub":
                children.append({"name": "file2.md", "file": {}})
            return children

        def download(site_id, drive_id, rel):
            path = rel.strip("/")
            return io.BytesIO(fake_fs[path])

        def props(site_id, drive_id, rel):
            path = rel.strip("/")
            return {"size": len(fake_fs[path]), "lastModifiedDateTime": "2025-09-14T10:00:00Z", "eTag": "etag"}

        c._graph_list_children = list_children
        c._graph_download = download
        c._graph_item_props = props

        refs = list(c.list(selector=["**/*.md"]))
        self.assertEqual(len(refs), 1)
        r = refs[0]
        self.assertEqual(r.id, "sub/file2.md")
        self.assertTrue(r.uri.startswith("sharepoint:"))

        with c.open(r) as f:
            self.assertEqual(f.read(), b"md")

        info = c.info(r)
        self.assertEqual(info.size, 2)


if __name__ == "__main__":
    unittest.main()
