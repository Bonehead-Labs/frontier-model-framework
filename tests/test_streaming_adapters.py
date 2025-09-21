from __future__ import annotations

import unittest

from fmf.core.interfaces import BaseProvider, CompletionRequest, CompletionResponse, ModelSpec
from fmf.core.errors import ProviderError
from fmf.inference.azure_openai import AzureOpenAIClient
from fmf.inference.bedrock import BedrockClient
from fmf.inference.base_client import Message
from fmf.inference.runtime import invoke_with_mode


class TestStreamingAdapters(unittest.TestCase):

    def test_iter_tokens_default_returns_completion(self) -> None:
        from fmf.core.interfaces import BaseProvider, CompletionRequest, CompletionResponse, ModelSpec

        class EchoProvider(BaseProvider):
            def __init__(self) -> None:
                super().__init__(ModelSpec(provider="echo", model="m"))

            def complete(self, request: CompletionRequest) -> CompletionResponse:
                payload = "".join(part if isinstance(part, str) else str(part) for part in request.messages)
                return CompletionResponse(text=payload)

        provider = EchoProvider()
        tokens: list[str] = []
        response = provider.stream(
            CompletionRequest(messages=[{"role": "user", "content": "hello"}]),
            on_token=tokens.append,
        )
        self.assertEqual(len(tokens), 1)
        self.assertIn("user", tokens[0])
        self.assertIn("hello", tokens[0])
        self.assertEqual(response.text, tokens[0])

    def test_azure_streaming_mode_auto(self) -> None:
        tokens: list[str] = []
        def stream_transport(payload):
            yield {"choices": [{"delta": {"content": "A"}}]}
            yield {"choices": [{"delta": {"content": "B"}, "finish_reason": "stop"}]}

        client = AzureOpenAIClient(
            endpoint="https://example",
            api_version="2024-02-15-preview",
            deployment="demo",
            transport=lambda payload: {
                "choices": [{"message": {"content": "fallback"}, "finish_reason": "stop"}],
                "usage": {},
                "model": "demo",
            },
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
        completion_stream, telemetry_stream = invoke_with_mode(
            client,
            [Message(role="user", content="hi")],
            mode="stream",
            provider_name="azure_openai",
        )
        self.assertTrue(telemetry_stream.streaming)
        self.assertEqual(completion_stream.text, "AB")

    def test_bedrock_streaming_unsupported_fallback(self) -> None:
        client = BedrockClient(
            region="us-east-1",
            model_id="anthropic.test",
            transport=lambda payload: {
                "output": {"text": "complete"},
                "usage": {"input_tokens": 2, "output_tokens": 1},
            },
            stream_transport=None,
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
        self.assertEqual(completion.text, "complete")
        self.assertEqual(telemetry.fallback_reason, "streaming_unsupported")


if __name__ == "__main__":
    unittest.main()
