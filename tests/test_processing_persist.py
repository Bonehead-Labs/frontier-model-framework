import io
import json
import os
import sys
import tempfile
import unittest


class TestProcessingPersist(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_persist_docs_and_chunks(self):
        from fmf.types import Document, Chunk
        from fmf.processing.persist import persist_artefacts

        with tempfile.TemporaryDirectory() as tmp:
            docs = [Document(id="d1", source_uri="file:///a", text="hello", blobs=None, metadata={})]
            chunks = [Chunk(id="c1", doc_id="d1", text="hello", tokens_estimate=2)]
            paths = persist_artefacts(artefacts_dir=tmp, run_id="run123", documents=docs, chunks=chunks)
            self.assertTrue(os.path.exists(paths["docs"]))
            self.assertTrue(os.path.exists(paths["chunks"]))
            self.assertTrue(os.path.exists(paths["manifest"]))
            with open(paths["docs"], "r", encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
                obj = json.loads(lines[0])
                self.assertEqual(obj["id"], "d1")
                self.assertEqual(obj["text"], "hello")
            with open(paths["manifest"], "r", encoding="utf-8") as f:
                manifest = json.load(f)
                self.assertEqual(manifest["run_id"], "run123")
                self.assertEqual(manifest["documents"][0]["id"], "d1")


if __name__ == "__main__":
    unittest.main()
