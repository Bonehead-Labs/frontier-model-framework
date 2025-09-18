import base64
import os
import sys
import tempfile
import unittest


class TestRagPipeline(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_build_and_retrieve(self):
        from fmf.rag import build_rag_pipelines

        tmpdir = tempfile.TemporaryDirectory()
        root = tmpdir.name
        text_path = os.path.join(root, "note.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("Cat care instructions and grooming tips.")

        img_path = os.path.join(root, "cat.png")
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAESQF/qYzDrwAAAABJRU5ErkJggg=="
        )
        with open(img_path, "wb") as f:
            f.write(png_bytes)

        connectors_cfg = [
            {
                "name": "local_kb",
                "type": "local",
                "root": root,
                "include": ["**/*"],
            }
        ]
        rag_cfg = {
            "pipelines": [
                {
                    "name": "kb",
                    "connector": "local_kb",
                    "modalities": ["text", "image"],
                    "build_concurrency": 2,
                }
            ]
        }

        pipelines = build_rag_pipelines(rag_cfg, connectors=connectors_cfg, processing_cfg=None)
        self.assertIn("kb", pipelines)
        pipeline = pipelines["kb"]

        result = pipeline.retrieve("cat grooming", top_k_text=1, top_k_images=1)
        self.assertLessEqual(len(result.texts), 1)
        self.assertLessEqual(len(result.images), 1)
        # text retrieval should match note content
        self.assertTrue(any("grooming" in item.content for item in result.texts))
        if result.images:
            # ensure data URLs can be produced without error
            urls = pipeline.image_data_urls(result.images)
            self.assertTrue(all(url.startswith("data:image/png;base64,") for url in urls))

        tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
