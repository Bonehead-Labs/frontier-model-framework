import os
import sys
import unittest


class TestProcessingText(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_html_to_text_and_normalize(self):
        from fmf.processing.text import html_to_text, normalize_text

        t = html_to_text("<h1> A  Title </h1>\n<p> Body </p>")
        self.assertIn("Title", t)
        n = normalize_text("Hello\n\n  world\t\t!  ")
        self.assertEqual(n, "Hello world !")


if __name__ == "__main__":
    unittest.main()

