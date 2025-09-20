from __future__ import annotations

import os
import unittest

from fmf.core.interfaces import BaseProvider, CompletionRequest, CompletionResponse, ModelSpec
from fmf.inference.azure_openai import AzureOpenAIClient
from fmf.inference.bedrock import BedrockClient
from fmf.inference.base_client import Message


class TestStreamingAdapters(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("FMF_EXPERIMENTAL_STREAMING", None)

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

    def test_azure_streaming_flag_enabled(self) -> None:
        os.environ["FMF_EXPERIMENTAL_STREAMING"] = "true"

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
        response = client.complete(
            [Message(role="user", content="hi")],
            stream=True,
            on_token=tokens.append,
        )
        self.assertEqual(tokens, ["A", "B"])
        self.assertEqual(response.text, "AB")

    def test_bedrock_streaming_flag_disabled(self) -> None:
        os.environ.pop("FMF_EXPERIMENTAL_STREAMING", None)
        tokens: list[str] = []

        client = BedrockClient(
            region="us-east-1",
            model_id="anthropic.test",
            transport=lambda payload: {
                "output": {"text": "complete"},
                "usage": {"input_tokens": 2, "output_tokens": 1},
            },
            stream_transport=lambda payload: [{"content": "ignored"}],
        )
        response = client.complete(
            [Message(role="user", content="hi")],
            stream=True,
            on_token=tokens.append,
        )
        self.assertEqual(tokens, ["complete"])
        self.assertEqual(response.text, "complete")


if __name__ == "__main__":
    unittest.main()
