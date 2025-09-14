import os
import sys
import unittest


class TestProcessingTypes(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_document_chunk_blob_serialization(self):
        from fmf.types import Blob, Document, Chunk

        b = Blob(id="b1", media_type="image/png", data=b"1234", metadata={"k": "v"})
        d = Document(id="d1", source_uri="file:///x", text="hello", blobs=[b], metadata={"m": 1})
        c = Chunk(id="c1", doc_id="d1", text="hello", tokens_estimate=5, metadata={"i": 2})

        sb = b.to_serializable()
        self.assertIn("sha256", sb)
        self.assertEqual(sb["size_bytes"], 4)

        sd = d.to_serializable()
        self.assertEqual(sd["id"], "d1")
        self.assertEqual(sd["text"], "hello")
        self.assertEqual(sd["blobs"][0]["media_type"], "image/png")

        sc = c.to_serializable()
        self.assertEqual(sc["tokens_estimate"], 5)


if __name__ == "__main__":
    unittest.main()

