import os
import sys
import tempfile
import textwrap
import unittest


class TestPromptRegistry(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def _write_file(self, dirpath: str, name: str, content: str) -> str:
        p = os.path.join(dirpath, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(content))
        return p

    def test_register_and_get(self):
        from fmf.prompts.registry import LocalYamlRegistry, PromptRegistryError

        with tempfile.TemporaryDirectory() as root:
            idx = os.path.join(root, "prompts", "index.yaml")
            os.makedirs(os.path.dirname(idx), exist_ok=True)
            reg = LocalYamlRegistry(root=root, index_file=idx)

            pfile = self._write_file(
                root,
                "sum.yaml",
                """
                id: summarize
                versions:
                  - version: v1
                    template: |
                      Summarize: {{ text }}
                    tests:
                      - name: t1
                        inputs: { text: "Hello" }
                        assertions: { contains: ["Hello"] }
                """,
            )

            pv = reg.register(pfile + "#v1")
            self.assertEqual(pv.id, "summarize")
            self.assertEqual(pv.version, "v1")
            self.assertTrue(len(pv.content_hash) == 64)

            pv2 = reg.get("summarize#v1")
            self.assertEqual(pv2.content_hash, pv.content_hash)


if __name__ == "__main__":
    unittest.main()

