import os
import sys
import tempfile
import textwrap
import unittest


class TestChainLoader(unittest.TestCase):
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

    def test_load_chain_schema(self):
        from fmf.chain.loader import load_chain

        chain_path = self._write_yaml(
            """
            name: test-chain
            inputs:
              connector: local_docs
              select: ["**/*.md"]
            steps:
              - id: summarize
                prompt: "inline: Summarize {{ text }}"
                inputs:
                  text: "${chunk.text}"
                output: summary
            concurrency: 2
            continue_on_error: true
            """
        )
        cfg = load_chain(chain_path)
        self.assertEqual(cfg.name, "test-chain")
        self.assertEqual(len(cfg.steps), 1)
        self.assertEqual(cfg.steps[0].id, "summarize")
        self.assertEqual(cfg.concurrency, 2)


if __name__ == "__main__":
    unittest.main()
