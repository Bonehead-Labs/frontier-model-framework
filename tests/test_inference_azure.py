import os
import sys
import unittest


class TestAzureOpenAIClient(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_complete_and_stream_and_usage(self):
        from fmf.inference.azure_openai import AzureOpenAIClient
        from fmf.inference.base_client import Message

        def transport(payload):
            assert "messages" in payload
            return {
                "choices": [
                    {
                        "message": {"content": "Hello world"},
                        "finish_reason": "stop",
                    }
                ],
                "model": "gpt-4o-mini",
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            }

        def stream_transport(payload):
            yield {"choices": [{"delta": {"content": "Hello "}}]}
            yield {
                "choices": [{"delta": {"content": "world"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
                "model": "gpt-4o-mini",
            }

        client = AzureOpenAIClient(
            endpoint="https://example",
            api_version="2024-02-15-preview",
            deployment="x",
            transport=transport,
            stream_transport=stream_transport,
        )
        toks: list[str] = []
        comp = client.complete(
            [Message(role="system", content="s"), Message(role="user", content="u")],
            temperature=0.2,
            max_tokens=10,
            stream=True,
            on_token=toks.append,
        )
        self.assertEqual(comp.text, "Hello world")
        self.assertEqual(comp.model, "gpt-4o-mini")
        self.assertEqual(comp.prompt_tokens, 5)
        self.assertEqual(comp.completion_tokens, 2)
        self.assertEqual(toks, ["Hello ", "world"])


if __name__ == "__main__":
    unittest.main()
