import io
import os
import sys
import tempfile
import unittest


class TestProcessingLoaders(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_text_and_markdown_and_html(self):
        from fmf.processing.loaders import detect_type, load_document_from_bytes

        md = b"# Title\nSome text."
        d = load_document_from_bytes(source_uri="file:///a.md", filename="a.md", data=md, processing_cfg={"text": {"preserve_markdown": True}})
        self.assertIn("Title", d.text)
        self.assertIn("Some", d.text)

        html = b"<h1>Hello</h1><p>world</p>"
        d2 = load_document_from_bytes(source_uri="file:///a.html", filename="a.html", data=html, processing_cfg={})
        self.assertEqual(d2.metadata["detected_type"], "html")
        self.assertIn("Hello", d2.text)
        self.assertIn("world", d2.text)

    def test_csv_to_markdown(self):
        from fmf.processing.loaders import load_document_from_bytes

        csv_bytes = b"col1,col2\nA,B\nC,D\n"
        d = load_document_from_bytes(source_uri="file:///t.csv", filename="t.csv", data=csv_bytes, processing_cfg={"tables": {"to_markdown": True}})
        self.assertIn("| col1 | col2 |", d.text)
        self.assertIn("| A | B |", d.text)

    def test_xlsx_requires_openpyxl(self):
        from fmf.processing.loaders import load_document_from_bytes
        from fmf.processing.errors import ProcessingError

        # This environment may not have openpyxl; we assert the error message when missing
        with self.assertRaises(ProcessingError):
            load_document_from_bytes(source_uri="file:///t.xlsx", filename="t.xlsx", data=b"not-a-real-xlsx", processing_cfg={})

    def test_xlsx_to_markdown_with_mock(self):
        from fmf.processing.loaders import load_document_from_bytes
        import sys as _sys
        import types as _types

        # Mock openpyxl with a minimal interface
        saved = dict(_sys.modules)
        try:
            openpyxl = _types.ModuleType("openpyxl")

            class FakeSheet:
                def iter_rows(self, values_only=True):
                    return iter([
                        ("h1", "h2"),
                        ("a", "b"),
                    ])

            class WB:
                def __init__(self):
                    self.active = FakeSheet()

            def load_workbook(fp, read_only=True, data_only=True):
                return WB()

            openpyxl.load_workbook = load_workbook
            _sys.modules["openpyxl"] = openpyxl

            d = load_document_from_bytes(
                source_uri="file:///t.xlsx",
                filename="t.xlsx",
                data=b"ignored",
                processing_cfg={"tables": {"to_markdown": True}},
            )
            self.assertIn("| h1 | h2 |", d.text)
            self.assertIn("| a | b |", d.text)
        finally:
            _sys.modules.clear()
            _sys.modules.update(saved)

    def test_image_without_ocr_blob_only(self):
        from fmf.processing.loaders import load_document_from_bytes

        fake_png = b"\x89PNG\r\n\x1a\n" + b"0" * 10
        d = load_document_from_bytes(source_uri="file:///i.png", filename="i.png", data=fake_png, processing_cfg={"images": {"ocr": {"enabled": False}}})
        self.assertIsNone(d.text)
        self.assertIsNotNone(d.blobs)
        self.assertEqual(d.blobs[0].media_type, "image/png")


if __name__ == "__main__":
    unittest.main()
