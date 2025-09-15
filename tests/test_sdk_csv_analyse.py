import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def complete(self, messages, **kwargs):
        user = [m for m in messages if m.role == "user"][0]
        # Always return a minimal JSON
        import json as _json
        return type("C", (), {"text": _json.dumps({"id": "1", "analysed": "ok"}), "prompt_tokens": 1, "completion_tokens": 1})()


class TestSdkCsvAnalyse(unittest.TestCase):
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

    def test_csv_analyse_writes_outputs_and_returns_records(self):
        from fmf.sdk import FMF
        import fmf.chain.runner as runner_mod

        # Patch LLM client
        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        csv_path = os.path.join(root, "comments.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("ID,Comment\n1,Great product!\n")

        cfg = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.csv"] }}]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

        fmf = FMF.from_env(cfg)
        records = fmf.csv_analyse(
            input=csv_path,
            text_col="Comment",
            id_col="ID",
            prompt="Summarise",
            save_csv=f"{root}/analysis/${{run_id}}/analysis.csv",
            save_jsonl=f"{root}/analysis/${{run_id}}/analysis.jsonl",
            return_records=True,
        )
        self.assertIsInstance(records, list)
        # Ensure save paths are materialised using run_id
        self.assertTrue(any(os.path.exists(os.path.join(root, "analysis", p, "analysis.csv")) for p in os.listdir(os.path.join(root, "analysis"))))
        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()

