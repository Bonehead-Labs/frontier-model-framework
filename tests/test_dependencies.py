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
        # Core dependency: Pydantic v2 pinned to <3
        self.assertTrue(any(d.startswith("pydantic") and ">=2" in d and "<3" in d for d in deps))
        # Core dependency: PyYAML pinned to <7
        self.assertTrue(any(d.lower().startswith("pyyaml") and ">=6" in d and "<7" in d for d in deps))

        optionals = project.get("optional-dependencies", {})
        for group in ("aws", "azure", "sharepoint", "ocr", "delta", "redshift", "excel"):
            self.assertIn(group, optionals)

        # Spot-check package names inside extras and that they are pinned with >= and <
        def has_pins(pkgs, name_substr):
            return any((name_substr in s) and (">=" in s) and ("<" in s) for s in pkgs)

        self.assertTrue(has_pins(optionals["aws"], "boto3"))
        self.assertTrue(has_pins(optionals["azure"], "azure-identity"))
        self.assertTrue(has_pins(optionals["azure"], "azure-keyvault-secrets"))
        # SharePoint via Microsoft Graph SDK
        self.assertTrue(has_pins(optionals["sharepoint"], "msgraph-sdk"))
        self.assertTrue(has_pins(optionals["ocr"], "pytesseract"))
        self.assertTrue(has_pins(optionals["delta"], "deltalake"))
        self.assertTrue(has_pins(optionals["redshift"], "redshift-connector"))
        self.assertTrue(has_pins(optionals["excel"], "openpyxl"))


if __name__ == "__main__":
    unittest.main()
