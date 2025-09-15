import unittest


class TestBedrockMultimodal(unittest.TestCase):
    def test_payload_maps_parts(self):
        from fmf.inference.bedrock import BedrockClient
        from fmf.inference.base_client import Message

        captured = {}

        def transport(payload: dict) -> dict:
            captured["payload"] = payload
            return {"output": {"text": "ok"}, "usage": {"input_tokens": 1, "output_tokens": 1}}

        client = BedrockClient(region="us-east-1", model_id="anthropic", transport=transport)
        messages = [
            Message(role="system", content="You are helpful"),
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
        self.assertEqual(content[1]["type"], "image")
        self.assertEqual(content[1]["source"]["type"], "base64")


if __name__ == "__main__":
    unittest.main()

