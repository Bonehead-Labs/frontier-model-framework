from __future__ import annotations

import json
from typing import Callable, Optional

from .base_client import Completion, InferenceError, LLMClient, Message, RateLimiter, with_retries
from ..processing.chunking import estimate_tokens


class BedrockClient:
    def __init__(
        self,
        *,
        region: str,
        model_id: str,
        rate_per_sec: float = 5.0,
        transport: Optional[Callable[[dict], dict]] = None,
    ) -> None:
        self.region = region
        self.model_id = model_id
        self._transport = transport
        self._rl = RateLimiter(rate_per_sec)

    def _default_transport(self, payload: dict) -> dict:  # pragma: no cover - requires network
        import boto3

        client = boto3.client("bedrock-runtime", region_name=self.region)
        body = json.dumps(payload)
        resp = client.invoke_model(modelId=self.model_id, body=body)
        data = resp.get("body")
        if hasattr(data, "read"):
            data = data.read()
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf-8")
        return json.loads(data)

    def complete(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool | None = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Completion:
        # Map unified messages to Anthropic Claude-style input via system + user
        system_parts = [m.content for m in messages if m.role == "system"]
        user_parts = [m.content for m in messages if m.role == "user"]
        sysmsg = "\n\n".join(system_parts) if system_parts else None
        prompt = "\n\n".join(user_parts)
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system": sysmsg,
        }

        def _do():
            self._rl.wait()
            transport = self._transport or self._default_transport
            data = transport(payload)
            # Expected generic structure: {output: {text: ...}, usage: {input_tokens, output_tokens}}
            text = data.get("output", {}).get("text") or data.get("content") or ""
            if stream and on_token:
                for tok in text.split():
                    on_token(tok)
            usage = data.get("usage", {}) or {}
            pt = usage.get("input_tokens")
            ct = usage.get("output_tokens")
            if pt is None:
                pt = sum(estimate_tokens(m.content) for m in messages)
            if ct is None:
                ct = estimate_tokens(text)
            return Completion(text=text, model=self.model_id, stop_reason=data.get("stop_reason"), prompt_tokens=pt, completion_tokens=ct)

        try:
            return with_retries(_do)
        except InferenceError as e:
            raise InferenceError(f"Bedrock error: {e}", status_code=e.status_code)


__all__ = ["BedrockClient"]

