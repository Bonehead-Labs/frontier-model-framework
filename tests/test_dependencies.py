import os
import sys
import tomllib
import unittest


class TestDependenciesSpec(unittest.TestCase):
    def test_pyproject_contains_core_and_optionals(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        pyproject_path = os.path.join(repo_root, "pyproject.toml")
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})
        self.assertIn("dependencies", project)
        deps = project["dependencies"]
        # Core dependency: Pydantic v2
        self.assertTrue(any(d.startswith("pydantic") and ">=2" in d for d in deps))

        optionals = project.get("optional-dependencies", {})
        for group in ("aws", "azure", "sharepoint", "ocr", "delta", "redshift", "excel"):
            self.assertIn(group, optionals)

        # Spot-check package names inside extras
        self.assertTrue(any(s.startswith("boto3") for s in optionals["aws"]))
        self.assertTrue(any(s.startswith("azure-identity") for s in optionals["azure"]))
        self.assertTrue(any(s.startswith("azure-keyvault-secrets") for s in optionals["azure"]))
        self.assertTrue(any("Office365-REST-Python-Client" in s for s in optionals["sharepoint"]))
        self.assertTrue(any(s.startswith("pytesseract") for s in optionals["ocr"]))
        self.assertTrue(any(s.startswith("deltalake") for s in optionals["delta"]))
        self.assertTrue(any(s.startswith("redshift-connector") for s in optionals["redshift"]))
        self.assertTrue(any(s.startswith("openpyxl") for s in optionals["excel"]))


if __name__ == "__main__":
    unittest.main()

