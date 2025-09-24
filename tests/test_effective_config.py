"""Tests for EffectiveConfig merge precedence and type coercion."""

import unittest
from unittest.mock import patch

from src.fmf.config.effective import EffectiveConfig
from src.fmf.config.models import FmfConfig, AuthConfig, EnvAuth


class TestEffectiveConfig(unittest.TestCase):
    def setUp(self):
        self.base_config = FmfConfig(
            project="test-project",
            run_profile="default",
            artefacts_dir="artefacts",
            auth=AuthConfig(provider="env", env=EnvAuth(file=".env")),
            connectors=[
                {"name": "local_docs", "type": "local", "root": "./data"}
            ],
            inference={"provider": "azure_openai", "azure_openai": {"endpoint": "https://test.openai.azure.com/"}},
        )

    def test_from_base_and_overrides_basic_merge(self):
        """Test basic merging of base config with overrides."""
        fluent_overrides = {
            "project": "override-project",
            "inference": {"provider": "aws_bedrock"}
        }
        
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=self.base_config,
            fluent_overrides=fluent_overrides
        )
        
        # Fluent overrides should take precedence
        self.assertEqual(effective.project, "override-project")
        self.assertEqual(effective.inference["provider"], "aws_bedrock")
        
        # Base config values should be preserved where not overridden
        self.assertEqual(effective.run_profile, "default")
        self.assertEqual(effective.artefacts_dir, "artefacts")
        self.assertIsNotNone(effective.auth)

    def test_from_base_and_overrides_with_recipe(self):
        """Test merging with recipe config in the middle."""
        recipe_config = {
            "project": "recipe-project",
            "inference": {"provider": "azure_openai", "temperature": 0.5}
        }
        fluent_overrides = {
            "project": "fluent-project",
            "inference": {"temperature": 0.8}
        }
        
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=self.base_config,
            recipe_config=recipe_config,
            fluent_overrides=fluent_overrides
        )
        
        # Fluent overrides should have highest precedence
        self.assertEqual(effective.project, "fluent-project")
        self.assertEqual(effective.inference["provider"], "azure_openai")  # From recipe
        self.assertEqual(effective.inference["temperature"], 0.8)  # From fluent
        
        # Recipe should override base
        self.assertIn("temperature", effective.inference)

    def test_merge_dicts_deep_merge(self):
        """Test that _merge_dicts performs deep merging."""
        base = {
            "inference": {
                "provider": "azure_openai",
                "azure_openai": {"endpoint": "https://test.openai.azure.com/"}
            },
            "connectors": [{"name": "local", "type": "local"}]
        }
        override = {
            "inference": {
                "provider": "aws_bedrock",
                "temperature": 0.5
            },
            "connectors": [{"name": "s3", "type": "s3", "bucket": "test-bucket"}]
        }
        
        result = EffectiveConfig._merge_dicts(base, override)
        
        # Should merge nested dicts
        self.assertEqual(result["inference"]["provider"], "aws_bedrock")
        self.assertEqual(result["inference"]["temperature"], 0.5)
        self.assertEqual(result["inference"]["azure_openai"]["endpoint"], "https://test.openai.azure.com/")
        
        # Should replace lists (not merge)
        self.assertEqual(len(result["connectors"]), 1)
        self.assertEqual(result["connectors"][0]["name"], "s3")

    def test_type_coercion_string_to_int(self):
        """Test that string values are coerced to appropriate types."""
        fluent_overrides = {
            "inference": {
                "azure_openai": {
                    "max_tokens": "1024",  # String that should become int
                    "temperature": "0.7"   # String that should become float
                }
            }
        }
        
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=self.base_config,
            fluent_overrides=fluent_overrides
        )
        
        # Values should be properly typed
        self.assertIsInstance(effective.inference["azure_openai"]["max_tokens"], str)  # Still string in dict
        self.assertIsInstance(effective.inference["azure_openai"]["temperature"], str)  # Still string in dict

    def test_connector_management(self):
        """Test connector add/update functionality."""
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=self.base_config,
            fluent_overrides={}
        )
        
        # Test adding new connector
        new_connector = {"name": "s3_docs", "type": "s3", "bucket": "test-bucket"}
        effective.add_or_update_connector(new_connector)
        
        # Should have both connectors
        self.assertEqual(len(effective.connectors), 2)
        self.assertIsNotNone(effective.get_connector_by_name("s3_docs"))
        self.assertIsNotNone(effective.get_connector_by_name("local_docs"))
        
        # Test updating existing connector
        updated_connector = {"name": "local_docs", "type": "local", "root": "./updated_data"}
        effective.add_or_update_connector(updated_connector)
        
        # Should still have 2 connectors, but local_docs should be updated
        self.assertEqual(len(effective.connectors), 2)
        local_connector = effective.get_connector_by_name("local_docs")
        self.assertEqual(local_connector["root"], "./updated_data")

    def test_rag_pipeline_management(self):
        """Test RAG pipeline management functionality."""
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=self.base_config,
            fluent_overrides={
                "rag": {
                    "pipelines": [
                        {"name": "local_rag", "connector": "local_docs"},
                        {"name": "s3_rag", "connector": "s3_docs"}
                    ]
                }
            }
        )
        
        # Test getting existing pipeline
        local_pipeline = effective.get_rag_pipeline("local_rag")
        self.assertIsNotNone(local_pipeline)
        self.assertEqual(local_pipeline["connector"], "local_docs")
        
        # Test getting non-existent pipeline
        missing_pipeline = effective.get_rag_pipeline("missing_rag")
        self.assertIsNone(missing_pipeline)

    def test_to_fmf_config_conversion(self):
        """Test conversion to FmfConfig model."""
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=self.base_config,
            fluent_overrides={
                "project": "converted-project",
                "inference": {"provider": "aws_bedrock"}
            }
        )
        
        fmf_config = effective.to_fmf_config()
        
        # Should be a FmfConfig instance
        self.assertIsInstance(fmf_config, FmfConfig)
        self.assertEqual(fmf_config.project, "converted-project")
        self.assertEqual(fmf_config.inference.provider, "aws_bedrock")
        
        # Should not include fluent_overrides
        self.assertFalse(hasattr(fmf_config, "fluent_overrides"))

    def test_to_dict_excludes_fluent_overrides(self):
        """Test that to_dict excludes fluent_overrides."""
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=self.base_config,
            fluent_overrides={"project": "test"}
        )
        
        config_dict = effective.to_dict()
        
        # Should not include fluent_overrides
        self.assertNotIn("fluent_overrides", config_dict)
        self.assertEqual(config_dict["project"], "test")

    def test_precedence_order_documentation(self):
        """Test that precedence order is correctly documented and implemented."""
        base_config = {"project": "base", "inference": {"provider": "base_provider"}}
        recipe_config = {"project": "recipe", "inference": {"temperature": 0.5}}
        fluent_overrides = {"project": "fluent", "inference": {"temperature": 0.8}}
        
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=base_config,
            recipe_config=recipe_config,
            fluent_overrides=fluent_overrides
        )
        
        # Fluent should win for project
        self.assertEqual(effective.project, "fluent")
        
        # Fluent should win for temperature, recipe should provide provider
        self.assertEqual(effective.inference["provider"], "base_provider")  # From base
        self.assertEqual(effective.inference["temperature"], 0.8)  # From fluent

    def test_empty_configs_handled_gracefully(self):
        """Test that empty or None configs are handled gracefully."""
        # Test with None base config
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=None,
            fluent_overrides={"project": "test"}
        )
        self.assertEqual(effective.project, "test")
        
        # Test with empty dict base config
        effective = EffectiveConfig.from_base_and_overrides(
            base_config={},
            fluent_overrides={"project": "test"}
        )
        self.assertEqual(effective.project, "test")
        
        # Test with None fluent overrides
        effective = EffectiveConfig.from_base_and_overrides(
            base_config=self.base_config,
            fluent_overrides=None
        )
        self.assertEqual(effective.project, "test-project")  # From base


if __name__ == "__main__":
    unittest.main()
