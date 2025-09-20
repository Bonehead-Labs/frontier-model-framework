from __future__ import annotations

import json
import os
from typing import Any, Callable, Iterable, Optional

from .base_client import Completion, InferenceError, LLMClient, Message, RateLimiter, with_retries
from ..core.interfaces.providers_base import TokenChunk
from .registry import register_provider
from ..processing.chunking import estimate_tokens


class BedrockClient:
    def __init__(
        self,
        *,
        region: str,
        model_id: str,
        rate_per_sec: float = 5.0,
        transport: Optional[Callable[[dict], dict]] = None,
        stream_transport: Optional[Callable[[dict], Iterable[dict]]] = None,
    ) -> None:
        self.region = region
        self.model_id = model_id
        self._transport = transport
        self._stream_transport = stream_transport
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
        system_texts: list[str] = []
        user_contents: list[dict] = []

        def _map_parts(parts):
            out = []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type")
                if ptype == "text":
                    out.append({"type": "text", "text": part.get("text", "")})
                elif ptype in {"image", "image_url"}:
                    url = part.get("url")
                    if not url and isinstance(part.get("image_url"), dict):
                        url = part.get("image_url", {}).get("url")
                    if url and url.startswith("data:"):
                        # parse data URL: data:<media>;base64,<data>
                        try:
                            header, b64 = url.split(",", 1)
                            media = header.split(";")[0].split(":", 1)[1]
                            out.append({
                                "type": "image",
                                "source": {"type": "base64", "media_type": media, "data": b64},
                            })
                        except Exception:
                            continue
                    elif url:
                        out.append({"type": "image", "source": {"type": "url", "url": url}})
                elif ptype == "image_base64":
                    media = part.get("media_type", "image/png")
                    out.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": part.get("data", "")}})
            return out

        for m in messages:
            if m.role == "system":
                if isinstance(m.content, str):
                    system_texts.append(m.content)
            elif m.role == "user":
                if isinstance(m.content, list):
                    user_contents.extend(_map_parts(m.content))
                else:
                    # plain text
                    user_contents.append({"type": "text", "text": str(m.content)})

        sysmsg = "\n\n".join(system_texts) if system_texts else None
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": user_contents}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system": sysmsg,
        }

        def _parse_response(data: dict) -> Completion:
            text = data.get("output", {}).get("text") or data.get("content") or ""
            usage = data.get("usage", {}) or {}
            pt = usage.get("input_tokens")
            ct = usage.get("output_tokens")
            if pt is None:
                pt = sum(estimate_tokens(m.content) for m in messages)
            if ct is None:
                ct = estimate_tokens(text)
            return Completion(text=text, model=self.model_id, stop_reason=data.get("stop_reason"), prompt_tokens=pt, completion_tokens=ct)

        def _stream_enabled() -> bool:
            value = os.getenv("FMF_EXPERIMENTAL_STREAMING", "")
            return value.lower() in {"1", "true", "yes", "on"}

        def _stream_payload() -> Optional[Completion]:
            transport = self._stream_transport
            if transport is None:
                return None
            chunks: list[str] = []
            usage: dict = {}
            stop_reason: Optional[str] = None
            for event in transport(payload):
                if not isinstance(event, dict):
                    continue
                usage = event.get("usage") or usage
                if "delta" in event:
                    delta = event.get("delta") or {}
                    content = delta.get("text")
                    if content:
                        chunk = TokenChunk(content, metadata={"provider": "bedrock", "type": "delta"})
                        chunks.append(chunk.text)
                        if on_token is not None:
                            on_token(chunk.text)
                    stop_reason = delta.get("stop_reason") or stop_reason
                elif "chunk" in event:
                    content = event.get("chunk")
                    if content:
                        chunks.append(str(content))
                        if on_token is not None:
                            on_token(str(content))
                elif "content" in event:
                    content = event.get("content")
                    if isinstance(content, str):
                        chunks.append(content)
                        if on_token is not None:
                            on_token(content)
            if not chunks:
                return None
            text = "".join(chunks)
            pt = usage.get("input_tokens") if isinstance(usage, dict) else None
            ct = usage.get("output_tokens") if isinstance(usage, dict) else None
            if pt is None:
                pt = sum(estimate_tokens(m.content) for m in messages)
            if ct is None:
                ct = estimate_tokens(text)
            return Completion(
                text=text,
                model=self.model_id,
                stop_reason=stop_reason,
                prompt_tokens=pt,
                completion_tokens=ct,
            )

        def _call_transport() -> dict:
            transport = self._transport or self._default_transport
            return transport(payload)

        def _do():
            self._rl.wait()
            if stream and on_token is not None:
                if _stream_enabled():
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
            return with_retries(_do)
        except InferenceError as e:
            raise InferenceError(f"Bedrock error: {e}", status_code=e.status_code)


@register_provider("aws_bedrock")
def _build_from_config(cfg: Any) -> BedrockClient:  # type: ignore[name-defined]
    region = getattr(cfg, "region", None) if not isinstance(cfg, dict) else cfg.get("region")
    model_id = getattr(cfg, "model_id", None) if not isinstance(cfg, dict) else cfg.get("model_id")
    return BedrockClient(region=region, model_id=model_id)


__all__ = ["BedrockClient"]
