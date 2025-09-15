import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def complete(self, messages, **kwargs):
        # Return simple text response
        return type("C", (), {"text": "ok", "prompt_tokens": 1, "completion_tokens": 1})()


class TestSdkTextAndImages(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def _write_yaml(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_text_files(self):
        from fmf.sdk import FMF
        import fmf.chain.runner as runner_mod

        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        md = os.path.join(root, "a.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("# Title\nHello.")

        cfg = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.md"] }}]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

        fmf = FMF.from_env(cfg)
        recs = fmf.text_files(prompt="Summarise", save_jsonl=f"{root}/text/${{run_id}}/out.jsonl", return_records=True)
        self.assertTrue(isinstance(recs, list))
        dtemp.cleanup()

    def test_images_analyse(self):
        from fmf.sdk import FMF
        import fmf.chain.runner as runner_mod

        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        img = os.path.join(root, "i.png")
        with open(img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00")

        cfg = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.png"] }}]
            processing: {{ images: {{ ocr: {{ enabled: false }} }} }}
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

        fmf = FMF.from_env(cfg)
        recs = fmf.images_analyse(prompt="Describe", save_jsonl=f"{root}/img/${{run_id}}/out.jsonl", return_records=True)
        self.assertTrue(isinstance(recs, list))
        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()

