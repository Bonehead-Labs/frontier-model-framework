import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def complete(self, messages, **kwargs):
        return type("C", (), {"text": "ok", "prompt_tokens": 1, "completion_tokens": 1})()


class TestCliSdkWrappers(unittest.TestCase):
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

    def test_cli_csv_analyse(self):
        import fmf.cli as cli
        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        csvp = os.path.join(root, "in.csv")
        with open(csvp, "w", encoding="utf-8") as f:
            f.write("ID,Comment\n1,Hello\n")

        cfg = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.csv"] }}]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

        rc = cli.main(["csv", "analyse", "--input", csvp, "--text-col", "Comment", "--id-col", "ID", "--prompt", "Summarise", "-c", cfg])
        self.assertEqual(rc, 0)
        dtemp.cleanup()

    def test_cli_text_infer(self):
        import fmf.cli as cli
        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        md = os.path.join(root, "a.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("# T\nHi")

        cfg = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.md"] }}]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )
        rc = cli.main(["text", "infer", "--select", "**/*.md", "--prompt", "Summarise", "-c", cfg])
        self.assertEqual(rc, 0)
        dtemp.cleanup()

    def test_cli_images_analyse(self):
        import fmf.cli as cli
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
        rc = cli.main(["images", "analyse", "--select", "**/*.png", "--prompt", "Describe", "-c", cfg])
        self.assertEqual(rc, 0)
        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()
