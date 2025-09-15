import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def complete(self, messages, **kwargs):
        user = [m for m in messages if m.role == "user"][0]
        return type("C", (), {"text": f"OUT:{user.content}", "prompt_tokens": 1, "completion_tokens": 1})()


class TestChainRowMode(unittest.TestCase):
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

    def test_row_mode_outputs_and_rows_artefact(self):
        # Prepare temp CSV and config
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "data.csv"), "w", encoding="utf-8") as f:
            f.write("id,message\n1,First\n2,Second\n")

        cfg_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors:
              - name: local_docs
                type: local
                root: {root}
                include: ["**/*.csv"]
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

        chain_path = self._write_yaml(
            """
            name: per-row
            inputs: { connector: local_docs, select: ["**/*.csv"], mode: table_rows, table: { text_column: message } }
            steps:
              - id: s
                prompt: "inline: ECHO {{ text }}"
                inputs: { text: "${row.text}" }
                output: o
            outputs:
              - save: ${ART}/out/${run_id}/sel.jsonl
                from: o
            """
        ).replace("${ART}", root)

        import fmf.chain.runner as runner_mod
        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore

        from fmf.chain.runner import run_chain
        res = run_chain(chain_path, fmf_config_path=cfg_path)

        # outputs.jsonl exists and contains 2 lines
        out_file = os.path.join(res["run_dir"], "outputs.jsonl")
        self.assertTrue(os.path.exists(out_file))
        with open(out_file, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)

        # rows.jsonl exists and is recorded in run.yaml artefacts
        rows_file = os.path.join(res["run_dir"], "rows.jsonl")
        self.assertTrue(os.path.exists(rows_file))
        import yaml as _yaml
        with open(os.path.join(res["run_dir"], "run.yaml"), "r", encoding="utf-8") as f:
            ry = _yaml.safe_load(f)
        self.assertIn(rows_file, ry.get("artefacts", []))

        dtemp.cleanup()


if __name__ == "__main__":
    unittest.main()

