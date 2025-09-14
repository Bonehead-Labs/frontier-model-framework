import os
import sys
import unittest


class TestDeployDocs(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_dockerfiles_exist(self):
        lam = os.path.join(self.repo_root, "docker", "Dockerfile.lambda")
        batch = os.path.join(self.repo_root, "docker", "Dockerfile.batch")
        self.assertTrue(os.path.exists(lam))
        self.assertTrue(os.path.exists(batch))
        with open(lam, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("public.ecr.aws/lambda/python:3.12", content)
        with open(batch, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("ENTRYPOINT [\"fmf\"]", content)

    def test_deployment_docs_and_iam_samples(self):
        dep = os.path.join(self.repo_root, "docs", "DEPLOYMENT.md")
        iam = os.path.join(self.repo_root, "docs", "IAM_POLICIES.md")
        self.assertTrue(os.path.exists(dep))
        self.assertTrue(os.path.exists(iam))
        with open(dep, "r", encoding="utf-8") as f:
            txt = f.read()
            self.assertIn("AWS Lambda", txt)
            self.assertIn("/tmp", txt)
            self.assertIn("AWS Batch", txt)
        with open(iam, "r", encoding="utf-8") as f:
            txt = f.read()
            self.assertIn("S3", txt)
            self.assertIn("DynamoDB", txt)
            self.assertIn("Redshift", txt)


if __name__ == "__main__":
    unittest.main()

