import os
import sys
import unittest


class TestProcessingChunking(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_chunking_by_sentence_with_overlap(self):
        from fmf.processing.chunking import chunk_text

        text = " ".join([f"Sentence {i}." for i in range(1, 21)])
        chunks = chunk_text(doc_id="d1", text=text, max_tokens=5, overlap=2, splitter="by_sentence")
        self.assertGreater(len(chunks), 1)
        # ensure overlap words appear at the start of subsequent chunk
        if len(chunks) >= 2:
            first_words = chunks[0].text.split()
            second_words = chunks[1].text.split()
            self.assertEqual(first_words[-2:], second_words[:2])
        # token estimates are positive
        self.assertTrue(all(c.tokens_estimate > 0 for c in chunks))


if __name__ == "__main__":
    unittest.main()

