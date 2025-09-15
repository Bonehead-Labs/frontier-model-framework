import json
import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def __init__(self):
        self.calls = []

    def complete(self, messages, **kwargs):
        user = [m for m in messages if m.role == "user"][0]
        self.calls.append(user.content)
        # echo back the content for visibility
        text = user.content if isinstance(user.content, str) else json.dumps(user.content)
        return type("C", (), {"text": text, "prompt_tokens": 1, "completion_tokens": 1})()


class TestChainJoinInterpolation(unittest.TestCase):
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

    def test_join_function_and_default_all_join(self):
        from fmf.chain.runner import run_chain
        import fmf.chain.runner as runner_mod

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("One.")
        with open(os.path.join(root, "b.md"), "w", encoding="utf-8") as f:
            f.write("Two.")

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
            """
            name: join-test
            inputs: { connector: local_docs, select: ["**/*.md"] }
            steps:
              - id: s1
                prompt: "inline: {{ text }}"
                inputs: { text: "${chunk.text}" }
                output: o1
              - id: s2
                prompt: "inline: Aggregate default:\n{{ agg1 }}\n\nAggregate join fn:\n{{ agg2 }}"
                inputs:
                  agg1: '${all.o1}'
                  agg2: '${join(all.o1, "|")}'
                output: o2
            """
        )

        dummy = DummyClient()
        runner_mod.build_llm_client = lambda cfg: dummy  # type: ignore
        res = run_chain(chain_path, fmf_config_path=cfg_path)
        with open(os.path.join(res["run_dir"], "outputs.jsonl"), "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        out = lines[-1]["output"]
        self.assertIn("Aggregate default:", out)
        self.assertIn("Aggregate join fn:", out)
        # The join function should have '|' between items
        self.assertIn("|", out)

        dtemp.cleanup()

    def test_aggregation_limits(self):
        from fmf.chain.runner import run_chain
        import fmf.chain.runner as runner_mod
        import os

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("A.")
        with open(os.path.join(root, "b.md"), "w", encoding="utf-8") as f:
            f.write("B.")

        cfg_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.md"] }}]
            processing: {{ text: {{ chunking: {{ max_tokens: 5, overlap: 0, splitter: by_sentence }} }} }}
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

        chain_path = self._write_yaml(
            """
            name: join-limits
            inputs: { connector: local_docs, select: ["**/*.md"] }
            steps:
              - id: s1
                prompt: "inline: {{ text }}"
                inputs: { text: "${chunk.text}" }
                output: o1
              - id: s2
                prompt: "inline: {{ agg }}"
                inputs:
                  agg: '${join(all.o1, "\n")}'
                output: o2
            """
        )

        # Set tight char limit
        os.environ["FMF_JOIN_MAX_CHARS"] = "3"
        dummy = DummyClient()
        runner_mod.build_llm_client = lambda cfg: dummy  # type: ignore
        res = run_chain(chain_path, fmf_config_path=cfg_path)
        with open(os.path.join(res["run_dir"], "outputs.jsonl"), "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        out = lines[-1]["output"]
        self.assertIn("truncated", out)
        # cleanup env var
        os.environ.pop("FMF_JOIN_MAX_CHARS", None)

        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()
