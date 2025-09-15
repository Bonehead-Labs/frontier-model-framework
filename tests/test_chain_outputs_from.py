import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def complete(self, messages, **kwargs):
        user = [m for m in messages if m.role == "user"][0]
        return type("C", (), {"text": f"OUT:{user.content}", "prompt_tokens": 1, "completion_tokens": 1})()


class TestChainOutputsFrom(unittest.TestCase):
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

    def test_outputs_from_selects_first_step(self):
        # Prepare temp files and config
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("Hello one.")

        cfg_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors:
              - name: local_docs
                type: local
                root: {root}
                include: ["**/*.md"]
            processing: {{ text: {{ chunking: {{ max_tokens: 50, overlap: 0, splitter: by_sentence }} }} }}
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            export:
              sinks:
                - name: s3_results
                  type: s3
                  bucket: b
                  prefix: fmf/outputs/${{run_id}}/
            """
        )

        chain_path = self._write_yaml(
            """
            name: t
            inputs: { connector: local_docs, select: ["**/*.md"] }
            steps:
              - id: s1
                prompt: "inline: S1: {{ text }}"
                inputs: { text: "${chunk.text}" }
                output: o1
              - id: s2
                prompt: "inline: S2: {{ prev }}"
                inputs: { prev: "${all.o1}" }
                output: o2
            outputs:
              - export: s3_results
                from: o1
            """
        )

        # Patch LLM and boto3
        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        out = {"puts": []}

        class S3:
            def put_object(self, **kwargs):
                out["puts"].append(kwargs)

        import types as _types
        sys.modules["boto3"] = _types.SimpleNamespace(client=lambda name: S3())  # type: ignore

        from fmf.chain.runner import run_chain

        res = run_chain(chain_path, fmf_config_path=cfg_path)
        # Ensure export happened and payload corresponds to step 'o1'
        self.assertTrue(out["puts"])
        body = out["puts"][0].get("Body")
        self.assertIsInstance(body, (bytes, bytearray))
        text = body.decode("utf-8")
        # Should contain OUT:S1: and not OUT:S2:
        self.assertIn("OUT:S1:", text)
        self.assertNotIn("OUT:S2:", text)

        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()
