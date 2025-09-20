from __future__ import annotations

import unittest


class TestProviderRegistry(unittest.TestCase):
    def test_registered_providers(self) -> None:
        from fmf.inference import registry
        from fmf.inference.azure_openai import AzureOpenAIClient

        providers = registry.available_providers()
        self.assertIn("azure_openai", providers)
        client = registry.build_provider("azure_openai", {"endpoint": "https://unit", "api_version": "2024-02-15-preview", "deployment": "demo"})
        self.assertIsInstance(client, AzureOpenAIClient)

    def test_unknown_provider(self) -> None:
        from fmf.inference import registry

        with self.assertRaises(ValueError):
            registry.build_provider("does-not-exist", {})


if __name__ == "__main__":
    unittest.main()
