from __future__ import annotations

import os
from typing import Any, Callable, Iterable, Optional

from .base_client import Completion, InferenceError, LLMClient, Message, RateLimiter, with_retries
from ..core.interfaces.providers_base import TokenChunk
from .registry import register_provider
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
        stream_transport: Optional[Callable[[dict], Iterable[dict]]] = None,
    ) -> None:
        self.endpoint = endpoint
        self.api_version = api_version
        self.deployment = deployment
        self._transport = transport
        self._stream_transport = stream_transport
        self._rl = RateLimiter(rate_per_sec)
        self._last_retries = 0

    def supports_streaming(self) -> bool:
        return self._stream_transport is not None

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

        def _parse_response(data: dict) -> Completion:
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

        def _stream_payload() -> Optional[Completion]:
            transport = self._stream_transport
            if transport is None:
                return None
            chunks: list[str] = []
            finish_reason: Optional[str] = None
            usage: dict = {}
            model_name: Optional[str] = None
            for event in transport(payload):
                if not isinstance(event, dict):
                    continue
                model_name = event.get("model") or model_name
                usage = event.get("usage") or usage
                for choice in event.get("choices", []):
                    delta = choice.get("delta") or {}
                    content = delta.get("content") or ""
                    if content:
                        chunk = TokenChunk(content, metadata={"provider": "azure", "type": "delta"})
                        chunks.append(chunk.text)
                        if on_token is not None:
                            on_token(chunk.text)
                    finish_reason = choice.get("finish_reason") or finish_reason
            if not chunks:
                return None
            text = "".join(chunks)
            pt = usage.get("prompt_tokens") if isinstance(usage, dict) else None
            ct = usage.get("completion_tokens") if isinstance(usage, dict) else None
            if pt is None:
                pt = sum(estimate_tokens(m.content) for m in messages)
            if ct is None:
                ct = estimate_tokens(text)
            return Completion(
                text=text,
                model=model_name or self.deployment,
                stop_reason=finish_reason,
                prompt_tokens=pt,
                completion_tokens=ct,
            )

        def _call_transport() -> dict:
            transport = self._transport or self._default_transport
            return transport(payload)

        attempts: dict[str, int] = {}

        def _do():
            self._rl.wait()
            if stream and on_token is not None:
                streamed = _stream_payload()
                if streamed is not None:
                    return streamed
                data = _call_transport()
                completion = _parse_response(data)
                if completion.text:
                    on_token(completion.text)
                return completion
            data = _call_transport()
            return _parse_response(data)

        try:
            completion = with_retries(_do, record_attempts=attempts)
        except InferenceError as err:
            try:
                self._last_retries = attempts.get("retries", 0)
            except Exception:
                pass
            raise err
        else:
            try:
                self._last_retries = attempts.get("retries", 0)
            except Exception:
                pass
            return completion


@register_provider("azure_openai")
def _build_from_config(cfg: Any) -> AzureOpenAIClient:  # type: ignore[name-defined]
    endpoint = getattr(cfg, "endpoint", None) if not isinstance(cfg, dict) else cfg.get("endpoint")
    api_version = getattr(cfg, "api_version", None) if not isinstance(cfg, dict) else cfg.get("api_version")
    deployment = getattr(cfg, "deployment", None) if not isinstance(cfg, dict) else cfg.get("deployment")
    return AzureOpenAIClient(endpoint=endpoint, api_version=api_version, deployment=deployment)


__all__ = ["AzureOpenAIClient"]
