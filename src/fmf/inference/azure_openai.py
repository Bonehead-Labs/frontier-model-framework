from __future__ import annotations

from typing import Callable, Optional

from .base_client import Completion, InferenceError, LLMClient, Message, RateLimiter, with_retries
from ..processing.chunking import estimate_tokens


class AzureOpenAIClient:
    def __init__(
        self,
        *,
        endpoint: str,
        api_version: str,
        deployment: str,
        rate_per_sec: float = 5.0,
        transport: Optional[Callable[[dict], dict]] = None,
    ) -> None:
        self.endpoint = endpoint
        self.api_version = api_version
        self.deployment = deployment
        self._transport = transport
        self._rl = RateLimiter(rate_per_sec)

    def _default_transport(self, payload: dict) -> dict:  # pragma: no cover - requires network
        import os
        import json
        import urllib.request

        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        if api_key:
            req.add_header("api-key", api_key)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise InferenceError(str(e))

    def complete(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool | None = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Completion:
        # Map to Azure OpenAI chat.completions payload
        def _map_content(c):
            if isinstance(c, list):
                out = []
                for part in c:
                    if not isinstance(part, dict):
                        continue
                    ptype = part.get("type")
                    if ptype == "text":
                        out.append({"type": "text", "text": part.get("text", "")})
                    elif ptype in {"image_url", "image"}:
                        url = part.get("url")
                        if not url and isinstance(part.get("image_url"), dict):
                            url = part.get("image_url", {}).get("url")
                        if not url and part.get("type") == "image_base64":
                            data = part.get("data")
                            media = part.get("media_type", "image/png")
                            url = f"data:{media};base64,{data}"
                        out.append({"type": "image_url", "image_url": {"url": url}})
                return out
            return c

        payload = {
            "messages": [{"role": m.role, "content": _map_content(m.content)} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        def _do():
            self._rl.wait()
            transport = self._transport or self._default_transport
            data = transport(payload)
            # Expected shape: {choices:[{message:{content:...}, finish_reason:...}], usage:{prompt_tokens, completion_tokens}, model:...}
            if stream and on_token:
                # Simulate streaming by tokenizing the content and invoking callback
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                for tok in text.split():
                    on_token(tok)
            choice = (data.get("choices") or [{}])[0]
            msg = (choice.get("message") or {}).get("content", "")
            finish = choice.get("finish_reason")
            usage = data.get("usage", {}) or {}
            pt = usage.get("prompt_tokens")
            ct = usage.get("completion_tokens")
            if pt is None:
                pt = sum(estimate_tokens(m.content) for m in messages)
            if ct is None:
                ct = estimate_tokens(msg)
            return Completion(text=msg, model=data.get("model"), stop_reason=finish, prompt_tokens=pt, completion_tokens=ct)

        return with_retries(_do)


__all__ = ["AzureOpenAIClient"]
