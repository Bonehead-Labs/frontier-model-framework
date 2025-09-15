import base64
import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def __init__(self):
        self.last_messages = None

    def complete(self, messages, **kwargs):
        self.last_messages = messages
        return type("C", (), {"text": "ok", "prompt_tokens": 1, "completion_tokens": 1})()


class TestChainMultimodalRunner(unittest.TestCase):
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

    def test_multimodal_step_collects_images(self):
        from fmf.chain.runner import run_chain
        import fmf.chain.runner as runner_mod

        # write a fake 'png' file
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        img_path = os.path.join(root, "img.png")
        with open(img_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00")

        cfg_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors:
              - name: local_images
                type: local
                root: {root}
                include: ["**/*.png"]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            processing: {{ images: {{ ocr: {{ enabled: false }} }} }}
            """
        )

        chain_path = self._write_yaml(
            """
            name: multimodal
            inputs: { connector: local_images, select: ["**/*.png"] }
            steps:
              - id: vision
                mode: multimodal
                prompt: "inline: Describe the image"
                inputs: {}
                output: o
            """
        )

        dummy = DummyClient()
        runner_mod.build_llm_client = lambda cfg: dummy  # type: ignore
        res = run_chain(chain_path, fmf_config_path=cfg_path)
        self.assertTrue(os.path.exists(os.path.join(res["run_dir"], "outputs.jsonl")))
        # check messages contained image part
        msgs = dummy.last_messages
        self.assertIsNotNone(msgs)
        user = [m for m in msgs if m.role == "user"][0]
        self.assertIsInstance(user.content, list)
        types = [p.get("type") for p in user.content if isinstance(user.content, list)]
        self.assertIn("image_url", types)
        # Ensure data URL prefix present
        img_parts = [p for p in user.content if isinstance(p, dict) and p.get("type") == "image_url"]
        self.assertTrue(any(p.get("url", "").startswith("data:image/png;base64,") for p in img_parts))

        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()

