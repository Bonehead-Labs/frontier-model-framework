import io
import os
import sys
import tempfile
import textwrap
import unittest


class DummyClient:
    def __init__(self, behavior=None):
        self.behavior = behavior or {}
        self.last_kwargs = None

    def complete(self, messages, **kwargs):
        user = [m for m in messages if m.role == "user"][0]
        text = user.content
        if "RAISE" in text:
            raise RuntimeError("fail")
        # tag output for identification
        self.last_kwargs = kwargs
        return type("C", (), {"text": f"OUT:{text}", "prompt_tokens": 1, "completion_tokens": 1})()


class TestChainRunner(unittest.TestCase):
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

    def test_run_chain_e2e_no_network(self):
        from fmf.chain.runner import run_chain
        import fmf.chain.runner as runner_mod

        # Create temp data and config
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("# A\nHello one.")
        with open(os.path.join(root, "b.md"), "w", encoding="utf-8") as f:
            f.write("# B\nHello two.")

        cfg_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors:
              - name: local_docs
                type: local
                root: {root}
                include: ["**/*.md"]
            processing:
              text:
                chunking: {{ strategy: recursive, max_tokens: 50, overlap: 5, splitter: by_sentence }}
            inference:
              provider: azure_openai
              azure_openai: {{ endpoint: https://example, api_version: 2024-02-15-preview, deployment: x }}
            export:
              sinks:
                - name: s3_results
                  type: s3
                  bucket: b
                  prefix: fmf/outputs/${{run_id}}/
            """
        )

        # Prompt file
        prompts_dir = tempfile.TemporaryDirectory()
        pfile = os.path.join(prompts_dir.name, "sum.yaml")
        with open(pfile, "w", encoding="utf-8") as f:
            f.write(
                textwrap.dedent(
                    """
                    id: summarize
                    versions:
                      - version: v1
                        template: |
                          Summarize: {{ text }}
                    """
                )
            )

            chain_path = self._write_yaml(
            f"""
            name: summarize-markdown
            inputs:
              connector: local_docs
              select: ["**/*.md"]
            steps:
              - id: summarize_chunk
                prompt: {pfile}#v1
                inputs:
                  text: "${{chunk.text}}"
                output: chunk_summary
              - id: aggregate
                prompt: "inline: Aggregate: {{ summaries }}"
                inputs:
                  summaries: "${{all.chunk_summary}}"
                output: report
            concurrency: 2
            continue_on_error: true
            outputs:
              - export: s3_results
                from: report
            """
        )

        # Patch LLM client
        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore
        # patch boto3 for exporter s3
        import types as _types
        out = {"puts": []}

        class S3:
            def put_object(self, **kwargs):
                out["puts"].append(kwargs)

        sys.modules["boto3"] = _types.SimpleNamespace(client=lambda name: S3())  # type: ignore

        res = run_chain(chain_path, fmf_config_path=cfg_path)
        self.assertIn("run_id", res)
        # run.yaml exists
        run_yaml = os.path.join(res["run_dir"], "run.yaml")
        self.assertTrue(os.path.exists(run_yaml))
        import yaml as _yaml
        with open(run_yaml, "r", encoding="utf-8") as f:
            runrec = _yaml.safe_load(f)
        self.assertIn("prompts_used", runrec)
        self.assertIn("metrics", runrec)

        # outputs.jsonl exists with OUT: prefix (from DummyClient)
        outputs = os.path.join(res["run_dir"], "outputs.jsonl")
        self.assertTrue(os.path.exists(outputs))
        with open(outputs, "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
            self.assertTrue(any("OUT:" in line for line in lines))
        # ensure exporter attempted
        self.assertTrue(out["puts"])  # S3 export happened

        dtemp.cleanup()
        prompts_dir.cleanup()

    def test_continue_on_error(self):
        from fmf.chain.runner import run_chain
        import fmf.chain.runner as runner_mod

        # Files
        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("RAISE error.")
        with open(os.path.join(root, "b.md"), "w", encoding="utf-8") as f:
            f.write("OK doc.")

        cfg_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors:
              - name: local_docs
                type: local
                root: {root}
                include: ["**/*.md"]
            processing: {{ text: {{ chunking: {{ max_tokens: 10, overlap: 0, splitter: by_sentence }} }} }}
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )

        chain_path = self._write_yaml(
            """
            name: t
            inputs: { connector: local_docs, select: ["**/*.md"] }
            steps:
              - id: s
                prompt: "inline: {{ text }}"
                inputs: { text: "${chunk.text}" }
                output: o
            continue_on_error: true
            concurrency: 2
            """
        )

        runner_mod.build_llm_client = lambda cfg: DummyClient()  # type: ignore
        res = run_chain(chain_path, fmf_config_path=cfg_path)
        # Should finish even though one chunk failed
        self.assertIn("run_dir", res)

    def test_step_params_passed(self):
        from fmf.chain.runner import run_chain
        import fmf.chain.runner as runner_mod

        dtemp = tempfile.TemporaryDirectory()
        root = dtemp.name
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as f:
            f.write("Doc.")

        cfg_path = self._write_yaml(
            f"""
            project: fmf
            artefacts_dir: {root}
            connectors: [{{ name: local_docs, type: local, root: {root}, include: ["**/*.md"] }}]
            processing: {{ text: {{ chunking: {{ max_tokens: 50, overlap: 0, splitter: by_sentence }} }} }}
            inference: {{ provider: azure_openai, azure_openai: {{ endpoint: https://x, api_version: v, deployment: d }} }}
            """
        )
        chain_path = self._write_yaml(
            """
            name: t
            inputs: { connector: local_docs, select: ["**/*.md"] }
            steps:
              - id: s
                prompt: "inline: {{ text }}"
                inputs: { text: "${chunk.text}" }
                output: o
                params: { temperature: 0.3, max_tokens: 10 }
            """
        )

        dummy = DummyClient()
        runner_mod.build_llm_client = lambda cfg: dummy  # type: ignore
        run_chain(chain_path, fmf_config_path=cfg_path)
        self.assertIsNotNone(dummy.last_kwargs)
        self.assertEqual(dummy.last_kwargs.get("temperature"), 0.3)
        self.assertEqual(dummy.last_kwargs.get("max_tokens"), 10)


if __name__ == "__main__":
    unittest.main()
