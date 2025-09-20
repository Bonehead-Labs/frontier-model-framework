"""Demonstrate streaming token emission using the experimental flag.

This recipe wires a stub transport into ``AzureOpenAIClient`` so it can run without
external services. Set ``FMF_EXPERIMENTAL_STREAMING=1`` to enable chunked delivery.
"""

from __future__ import annotations

import os

from fmf.inference.azure_openai import AzureOpenAIClient
from fmf.inference.base_client import Message


def main() -> None:
    os.environ.setdefault("FMF_EXPERIMENTAL_STREAMING", "1")

    def transport(_payload):
        return {
            "choices": [
                {"message": {"content": "fallback"}, "finish_reason": "stop"}
            ],
            "model": "demo",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

    def stream_transport(_payload):
        yield {"choices": [{"delta": {"content": "Hello "}}]}
        yield {"choices": [{"delta": {"content": "world"}, "finish_reason": "stop"}]}

    client = AzureOpenAIClient(
        endpoint="https://example",
        api_version="2024-02-15-preview",
        deployment="demo",
        transport=transport,
        stream_transport=stream_transport,
    )
    tokens: list[str] = []
    completion = client.complete(
        [Message(role="user", content="Say hello")],
        stream=True,
        on_token=tokens.append,
    )
    print("streamed tokens:", tokens)
    print("completion:", completion.text)


if __name__ == "__main__":
    main()
