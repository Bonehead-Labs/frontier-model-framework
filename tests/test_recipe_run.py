import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def complete(self, messages, **kwargs):
        return type("C", (), {"text": "ok", "prompt_tokens": 1, "completion_tokens": 1})()


class TestRecipeRun(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def _write_file(self, path: str, content: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))

    def test_run_csv_recipe(self):
        from fmf.sdk import FMF
        import fmf.chain.runner as runner_mod

        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        csvp = os.path.join(root, "in.csv")
        self._write_file(csvp, "ID,Comment\n1,Hello\n")
        cfgp = os.path.join(root, "fmf.yaml")
        self._write_file(cfgp, f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.csv"] }}]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
        """)

        rxp = os.path.join(root, "recipe.yaml")
        self._write_file(rxp, f"""
            recipe: csv_analyse
            input: {csvp}
            id_col: ID
            text_col: Comment
            prompt: Summarise
            save:
              csv: {root}/analysis/${{run_id}}/analysis.csv
              jsonl: {root}/analysis/${{run_id}}/analysis.jsonl
        """)

        f = FMF.from_env(cfgp)
        res = f.run_recipe(rxp)
        self.assertIsInstance(res, dict)
        # Ensure files created
        self.assertTrue(os.path.isdir(os.path.join(root, "analysis")))
        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()

