import os
import sys
import unittest
import yaml


class TestExamplesDocs(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_example_fmf_yaml_loads(self):
        path = os.path.join(self.repo_root, "examples", "fmf.example.yaml")
        self.assertTrue(os.path.exists(path))
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # spot-check key sections
        self.assertIn("connectors", data)
        self.assertIn("processing", data)
        self.assertIn("inference", data)
        self.assertIn("export", data)

    def test_example_prompts_and_chain(self):
        prompts = os.path.join(self.repo_root, "examples", "prompts", "summarize.yaml")
        chain = os.path.join(self.repo_root, "examples", "chains", "sample.yaml")
        self.assertTrue(os.path.exists(prompts))
        self.assertTrue(os.path.exists(chain))
        with open(prompts, "r", encoding="utf-8") as f:
            p = yaml.safe_load(f)
            self.assertEqual(p.get("id"), "summarize")
            self.assertTrue(any(v.get("version") == "v1" for v in p.get("versions", [])))
        with open(chain, "r", encoding="utf-8") as f:
            c = yaml.safe_load(f)
            self.assertEqual(c.get("name"), "summarize-markdown")
            self.assertTrue(any(s.get("id") == "summarize_chunk" for s in c.get("steps", [])))

    def test_readme_links(self):
        readme = os.path.join(self.repo_root, "README.md")
        self.assertTrue(os.path.exists(readme))
        with open(readme, "r", encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("AGENTS.md", txt)
        self.assertIn("BUILD_PLAN.md", txt)
        self.assertIn("examples/", txt)


if __name__ == "__main__":
    unittest.main()

