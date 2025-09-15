import unittest


class TestAzureMultimodal(unittest.TestCase):
    def test_payload_maps_parts(self):
        from fmf.inference.azure_openai import AzureOpenAIClient
        from fmf.inference.base_client import Message

        captured = {}

        def transport(payload: dict) -> dict:
            captured["payload"] = payload
            # minimal valid response shape
            return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}, "model": "x"}

        client = AzureOpenAIClient(endpoint="https://e", api_version="2024-02-15-preview", deployment="d", transport=transport)
        messages = [
            Message(role="user", content=[
                {"type": "text", "text": "describe"},
                {"type": "image_url", "url": "data:image/png;base64,AAA="},
            ])
        ]
        client.complete(messages)
        p = captured["payload"]
        self.assertIn("messages", p)
        content = p["messages"][0]["content"]
        self.assertIsInstance(content, list)
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")
        self.assertIn("image_url", content[1])


if __name__ == "__main__":
    unittest.main()

