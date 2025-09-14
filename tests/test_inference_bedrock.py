import os
import sys
import unittest


class TestBedrockClient(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_complete_and_error_mapping(self):
        from fmf.inference.bedrock import BedrockClient
        from fmf.inference.base_client import Message, InferenceError

        calls = {"n": 0}

        class E(Exception):
            def __init__(self, status_code):
                super().__init__("err")
                self.status_code = status_code

        def transport(payload):
            calls["n"] += 1
            if calls["n"] == 1:
                raise E(429)
            return {"output": {"text": "OK"}, "usage": {"input_tokens": 3, "output_tokens": 1}}

        client = BedrockClient(region="us-east-1", model_id="anthropic.claude-3-haiku", transport=transport)
        comp = client.complete([Message(role="user", content="Hi")])
        self.assertEqual(comp.text, "OK")
        self.assertEqual(comp.prompt_tokens, 3)
        self.assertEqual(comp.completion_tokens, 1)

        # error mapping
        def bad(payload):
            raise E(500)

        client2 = BedrockClient(region="us-east-1", model_id="model", transport=bad)
        with self.assertRaises(InferenceError):
            client2.complete([Message(role="user", content="Hi")])


if __name__ == "__main__":
    unittest.main()

