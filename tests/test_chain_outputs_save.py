import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def complete(self, messages, **kwargs):
        user = [m for m in messages if m.role == "user"][0]
        return type("C", (), {"text": f"OUT:{user.content}", "prompt_tokens": 1, "completion_tokens": 1})()


class TestChainOutputsSave(unittest.TestCase):
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

    def test_outputs_save_writes_file_and_run_yaml_lists_it(self):
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
            """
        )

        chain_path = self._write_yaml(
            f"""
            name: t
            inputs: {{ connector: local_docs, select: ["**/*.md"] }}
            steps:
              - id: s1
                prompt: "inline: S1: {{ text }}"
                inputs: {{ text: "${{chunk.text}}" }}
                output: o1
            outputs:
              - save: {root}/custom/${{run_id}}/sel.jsonl
                from: o1
            """
        )

        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        from fmf.chain.runner import run_chain
        res = run_chain(chain_path, fmf_config_path=cfg_path)
        run_id = res["run_id"]
        saved_path = os.path.join(root, "custom", run_id, "sel.jsonl")
        self.assertTrue(os.path.exists(saved_path))
        # Validate run.yaml includes the saved path in artefacts
        import yaml as _yaml
        with open(os.path.join(res["run_dir"], "run.yaml"), "r", encoding="utf-8") as f:
            ry = _yaml.safe_load(f)
        self.assertIn(saved_path, ry.get("artefacts", []))

        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()

