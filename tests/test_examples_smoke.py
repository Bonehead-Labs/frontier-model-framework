from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
for candidate in (str(SRC_PATH), str(REPO_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from fmf.core.interfaces import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    ConnectorSpec,
    DocumentModel,
    ModelSpec,
)
from fmf.inference.base_client import Completion


FIXTURES = Path(__file__).parent / "fixtures"


class ExampleFixtureTests(unittest.TestCase):
    def test_fixture_inventory(self) -> None:
        self.assertTrue((FIXTURES / "csv" / "sample_comments.csv").exists())
        self.assertTrue((FIXTURES / "text" / "sample_note.txt").exists())
        self.assertTrue((FIXTURES / "images" / "sample_pixel.png").exists())
        self.assertTrue((FIXTURES / "parquet" / "sample_comments.parquet").exists())

    def test_model_and_connector_spec_defaults(self) -> None:
        spec = ModelSpec(provider="unit-test", model="mock", modality="text")
        self.assertFalse(spec.streaming.enabled)
        self.assertEqual(spec.default_params, {})
        connector_spec = ConnectorSpec(name="local_docs", type="local")
        self.assertEqual(connector_spec.selectors.include, [])

    def test_completion_response_helper_roundtrip(self) -> None:
        completion = Completion(text="ok", model="mock", stop_reason="stop")
        response = CompletionResponse.from_completion(completion)
        self.assertEqual(response.text, "ok")
        self.assertEqual(response.model, "mock")

    def test_example_recipe_modules_importable(self) -> None:
        from examples.recipes import csv_quickstart, multimodal_walkthrough

        csv_plan = csv_quickstart.build_recipe("tests/fixtures/csv/sample_comments.csv", "Summarise")
        self.assertEqual(csv_plan["prompt"], "Summarise")

        mm_plan = multimodal_walkthrough.build_recipe()
        self.assertIn("**/*.{png,jpg,jpeg}", mm_plan["select"])


class _DummyProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(ModelSpec(provider="dummy", model="stub"))

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        text = request.messages[-1].content if request.messages else ""
        completion = Completion(text=str(text))
        return CompletionResponse.from_completion(completion)


class ProviderContractTests(unittest.TestCase):
    def test_dummy_provider_roundtrip(self) -> None:
        provider = _DummyProvider()
        document = DocumentModel(source_uri="tests://sample", text="hello world")
        request = CompletionRequest(messages=[{"role": "user", "content": document.text}])
        response = provider.complete(request)
        self.assertEqual(response.text, "hello world")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
