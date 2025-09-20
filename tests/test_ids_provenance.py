from __future__ import annotations

import os
import sys
import unittest


class TestIdsAndProvenance(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_document_id_stable(self) -> None:
        from fmf.processing.loaders import load_document_from_bytes

        payload = b"hello world"
        doc1 = load_document_from_bytes(
            source_uri="file:///tmp/doc.txt",
            filename="doc.txt",
            data=payload,
            processing_cfg={},
        )
        doc2 = load_document_from_bytes(
            source_uri="file:///tmp/doc.txt",
            filename="doc.txt",
            data=payload,
            processing_cfg={},
        )
        self.assertEqual(doc1.id, doc2.id)
        self.assertIn("created_at", doc1.provenance)
        self.assertEqual(doc1.provenance["source_uri"], "file:///tmp/doc.txt")

    def test_normalize_handles_windows_newlines(self) -> None:
        from fmf.core.ids import normalize_text, document_id

        unix = "Line1\nLine2"
        windows = "Line1\r\nLine2"
        mac = "Line1\rLine2"
        base = normalize_text(unix)
        self.assertEqual(base, normalize_text(windows))
        self.assertEqual(base, normalize_text(mac))

        doc_a = document_id(source_uri="mem://x", payload=normalize_text(unix))
        doc_b = document_id(source_uri="mem://x", payload=normalize_text(windows))
        self.assertEqual(doc_a, doc_b)

    def test_chunk_id_stable(self) -> None:
        from fmf.processing.chunking import chunk_text

        chunks_a = chunk_text(doc_id="doc_abcd", text="One. Two. Three.")
        chunks_b = chunk_text(doc_id="doc_abcd", text="One. Two. Three.")
        self.assertEqual([c.id for c in chunks_a], [c.id for c in chunks_b])
        self.assertTrue(all("index" in c.provenance for c in chunks_a))


if __name__ == "__main__":
    unittest.main()
