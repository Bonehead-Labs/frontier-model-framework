import json
import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def __init__(self, text):
        self._text = text

    def complete(self, messages, **kwargs):
        return type("C", (), {"text": self._text, "prompt_tokens": 1, "completion_tokens": 1})()


class TestChainJsonEnforcement(unittest.TestCase):
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

    def _common_cfg(self, root: str) -> str:
        return self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors:
              - name: local_docs
                type: local
                root: {root}
                include: ["**/*.md"]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

    def test_json_enforcement_success(self):
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("Doc")

        cfg_path = self._common_cfg(root)
        chain_path = self._write_yaml(
            """
            name: t
            inputs: { connector: local_docs, select: ["**/*.md"] }
            steps:
              - id: s
                prompt: "inline: {}"
                inputs: {}
                output: { name: o, expects: json, schema: { type: object, required: [a] } }
            """
        )

        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient('{"a":1}')  # type: ignore
        from fmf.chain.runner import run_chain
        res = run_chain(chain_path, fmf_config_path=cfg_path)
        with open(os.path.join(res["run_dir"], "outputs.jsonl"), "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        self.assertIsInstance(lines[0].get("output"), dict)
        self.assertEqual(lines[0]["output"].get("a"), 1)

        dtemp.cleanup()

    def test_json_enforcement_repair_and_metrics(self):
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("Doc")
        cfg_path = self._common_cfg(root)
        chain_path = self._write_yaml(
            """
            name: t
            inputs: { connector: local_docs, select: ["**/*.md"] }
            steps:
              - id: s
                prompt: "inline: {}"
                inputs: {}
                output: { name: o, expects: json, parse_retries: 1 }
            """
        )

        # Return fenced JSON to force repair path
        bad_json = """```json\n{\n  \"b\": 2\n}\n```"""
        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient(bad_json)  # type: ignore
        from fmf.chain.runner import run_chain
        res = run_chain(chain_path, fmf_config_path=cfg_path)
        with open(os.path.join(res["run_dir"], "outputs.jsonl"), "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(lines[0]["output"].get("b"), 2)
        # Metrics in run.yaml should include json_parse_failures.* only when failures occur; here repair succeeded, so none expected
        import yaml as _yaml
        with open(os.path.join(res["run_dir"], "run.yaml"), "r", encoding="utf-8") as f:
            runrec = _yaml.safe_load(f)
        metrics = runrec.get("metrics", {})
        # Allow zero or absence
        self.assertFalse(any(k.startswith("json_parse_failures") and metrics.get(k, 0) > 0 for k in metrics.keys()))

        dtemp.cleanup()

    def test_json_enforcement_failure_records_error_and_metrics(self):
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("Doc")
        cfg_path = self._common_cfg(root)
        chain_path = self._write_yaml(
            """
            name: t
            inputs: { connector: local_docs, select: ["**/*.md"] }
            continue_on_error: true
            steps:
              - id: s
                prompt: "inline: {}"
                inputs: {}
                output: { name: o, expects: json, parse_retries: 1, schema: { type: object, required: [c] } }
            """
        )

        # Unrepairable JSON
        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient("not json at all")  # type: ignore
        from fmf.chain.runner import run_chain
        res = run_chain(chain_path, fmf_config_path=cfg_path)
        with open(os.path.join(res["run_dir"], "outputs.jsonl"), "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        self.assertTrue(lines[0]["output"].get("parse_error"))
        self.assertIn("raw_text", lines[0]["output"])
        import yaml as _yaml
        with open(os.path.join(res["run_dir"], "run.yaml"), "r", encoding="utf-8") as f:
            runrec = _yaml.safe_load(f)
        metrics = runrec.get("metrics", {})
        # Should contain aggregated and per-step failure counters
        self.assertTrue(any(k == "json_parse_failures" and metrics.get(k, 0) >= 1 for k in metrics.keys()))
        self.assertTrue(any(k.startswith("json_parse_failures.s") for k in metrics.keys()))

        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()

