import base64
import json
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


class TestChainRagIntegration(unittest.TestCase):
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

    def test_multimodal_step_receives_rag_context(self):
        from fmf.chain.runner import run_chain
        import fmf.chain.runner as runner_mod

        data_dir = tempfile.TemporaryDirectory()
        root = data_dir.name

        # primary input document
        main_path = os.path.join(root, "main.txt")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write("Assess the cat in the provided materials.")

        # RAG text
        rag_txt = os.path.join(root, "facts.txt")
        with open(rag_txt, "w", encoding="utf-8") as f:
            f.write("Cat facts: the cat is agile and has keen senses.")

        # RAG image
        rag_img = os.path.join(root, "cat_sample.png")
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAESQF/qYzDrwAAAABJRU5ErkJggg=="
        )
        with open(rag_img, "wb") as f:
            f.write(png_bytes)

        cfg_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors:
              - name: primary_docs
                type: local
                root: {root}
                include: ["main.txt"]
              - name: rag_docs
                type: local
                root: {root}
                include: ["facts.txt", "cat_sample.png"]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            rag:
              pipelines:
                - name: kb
                  connector: rag_docs
                  modalities: ["text", "image"]
                  max_text_items: 5
                  max_image_items: 5
            """
        )

        chain_path = self._write_yaml(
            """
            name: rag-test
            inputs: { connector: primary_docs, select: ["main.txt"] }
            steps:
              - id: analyse
                mode: multimodal
                prompt: "inline: Analyse request: {{ chunk_text }}"
                inputs:
                  chunk_text: "${chunk.text}"
                output: result
                rag:
                  pipeline: kb
                  query: "${chunk.text}"
                  top_k_text: 2
                  top_k_images: 1
                  text_var: rag_context
                  image_var: rag_samples
            """
        )

        dummy = DummyClient()
        runner_mod.build_llm_client = lambda cfg: dummy  # type: ignore
        res = run_chain(chain_path, fmf_config_path=cfg_path)

        # Ensure rag artefact persisted
        rag_path = os.path.join(res["run_dir"], "rag", "kb.jsonl")
        self.assertTrue(os.path.exists(rag_path))
        with open(rag_path, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f]
        self.assertTrue(any("cat" in t["content"].lower() for rec in data for t in rec.get("texts", [])))

        # Validate messages contain RAG context and image
        self.assertIsNotNone(dummy.last_messages)
        user = [m for m in dummy.last_messages if m.role == "user"][0]
        self.assertIsInstance(user.content, list)
        text_part = next(p for p in user.content if isinstance(p, dict) and p.get("type") == "text")
        self.assertIn("Retrieved context", text_part.get("text", ""))
        image_parts = [p for p in user.content if isinstance(p, dict) and p.get("type") == "image_url"]
        self.assertTrue(any(part.get("url", "").startswith("data:image/png;base64,") for part in image_parts))

        data_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
