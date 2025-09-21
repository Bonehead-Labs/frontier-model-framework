import os
import sys
import unittest

from fmf.core.errors import ProviderError
from fmf.inference.azure_openai import AzureOpenAIClient
from fmf.inference.bedrock import BedrockClient
from fmf.inference.base_client import Message
from fmf.inference.runtime import invoke_with_mode


class TestInferenceMode(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_streaming_success_auto_mode(self) -> None:
        def transport(payload):
            return {
                "choices": [{"message": {"content": "fallback"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
                "model": "demo",
            }

        def stream_transport(payload):
            yield {"choices": [{"delta": {"content": "A"}}]}
            yield {
                "choices": [{"delta": {"content": "B"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            }

        client = AzureOpenAIClient(
            endpoint="https://example",
            api_version="2024-02-15-preview",
            deployment="demo",
            transport=transport,
            stream_transport=stream_transport,
        )

        completion, telemetry = invoke_with_mode(
            client,
            [Message(role="user", content="hi")],
            mode="auto",
            provider_name="azure_openai",
        )
        self.assertTrue(telemetry.streaming)
        self.assertEqual(completion.text, "AB")
        self.assertEqual(telemetry.chunk_count, 2)
        self.assertIsNone(telemetry.fallback_reason)

    def test_streaming_failure_auto_fallback(self) -> None:
        def transport(payload):
            return {
                "choices": [{"message": {"content": "fallback"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "model": "demo",
            }

        def failing_stream(payload):
            raise RuntimeError("stream unavailable")

        client = AzureOpenAIClient(
            endpoint="https://example",
            api_version="2024-02-15-preview",
            deployment="demo",
            transport=transport,
            stream_transport=failing_stream,
        )

        completion, telemetry = invoke_with_mode(
            client,
            [Message(role="user", content="hi")],
            mode="auto",
            provider_name="azure_openai",
        )
        self.assertFalse(telemetry.streaming)
        self.assertEqual(completion.text, "fallback")
        self.assertIsNotNone(telemetry.fallback_reason)
        self.assertTrue(telemetry.fallback_reason.startswith("stream_error"))

    def test_streaming_unsupported_raises(self) -> None:
        client = BedrockClient(
            region="us-east-1",
            model_id="anthropic.test",
            transport=lambda payload: {
                "output": {"text": "bedrock"},
                "usage": {"input_tokens": 2, "output_tokens": 2},
            },
        )

        with self.assertRaises(ProviderError):
            invoke_with_mode(
                client,
                [Message(role="user", content="hi")],
                mode="stream",
                provider_name="aws_bedrock",
            )

        completion, telemetry = invoke_with_mode(
            client,
            [Message(role="user", content="hi")],
            mode="auto",
            provider_name="aws_bedrock",
        )
        self.assertFalse(telemetry.streaming)
        self.assertEqual(telemetry.fallback_reason, "streaming_unsupported")
        self.assertEqual(completion.text, "bedrock")


if __name__ == "__main__":
    unittest.main()
