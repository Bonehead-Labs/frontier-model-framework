import os
import sys
import unittest


@unittest.skip("smoke only; exporters not implemented in test env")
class TestOtherExporters(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_builders(self):
        from fmf.exporters import build_exporter

        sharepoint = build_exporter({"type": "sharepoint_excel", "name": "sp", "site_url": "https://x", "drive": "Documents", "file_path": "a.xlsx", "sheet": "s"})
        redshift = build_exporter({"type": "redshift", "name": "rs", "cluster_id": "c", "database": "d", "schema": "s", "table": "t", "unload_staging_s3": "s3://b/p"})
        delta = build_exporter({"type": "delta", "name": "dl", "storage": "s3", "path": "s3://b/t"})
        fabric = build_exporter({"type": "fabric_delta", "name": "fd", "workspace": "w", "lakehouse": "l", "table": "t"})


if __name__ == "__main__":
    unittest.main()

