import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, **kwargs):
        self.calls += 1
        user = [m for m in messages if m.role == "user"][0]
        return type("C", (), {"text": f"OUT:{user.content}", "prompt_tokens": 1, "completion_tokens": 1})()


class TestRunnerProgrammatic(unittest.TestCase):
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

    def test_run_chain_config_dict(self):
        # Data and config
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("Hello.")

        cfg = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.md"] }}]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

        chain = {
            "name": "prog",
            "inputs": {"connector": "local_docs", "select": ["**/*.md"]},
            "steps": [
                {"id": "s", "prompt": "inline: {{ text }}", "inputs": {"text": "${chunk.text}"}, "output": "o"}
            ],
        }

        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore
        from fmf.chain.runner import run_chain_config

        res = run_chain_config(chain, fmf_config_path=cfg)
        self.assertIn("run_dir", res)
        self.assertTrue(os.path.exists(os.path.join(res["run_dir"], "outputs.jsonl")))

        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()

