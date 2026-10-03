from __future__ import annotations

import io
import json
import os
from typing import Any, Iterable
from urllib.parse import quote

import boto3
import requests


class OpenAICompatClient:
    """Bedrock-shaped client backed by OpenAI APIs."""

    def __init__(self, *, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    @staticmethod
    def _model_for_converse(default_model: str | None = None) -> str:
        return os.getenv("OPENAI_MODEL", default_model or "gpt-4o-mini")

    @staticmethod
    def _model_for_embeddings() -> str:
        return os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    @staticmethod
    def _embedding_dimensions() -> int | None:
        raw = (os.getenv("OPENAI_EMBED_DIMENSIONS") or "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @staticmethod
    def _extract_text_from_message_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                    elif "text" in item:
                        parts.append(str(item.get("text", "")))
            return "".join(parts)
        return ""

    def _post_json(self, path: str, payload: Any) -> requests.Response:
        response = self.session.post(f"{self.base_url}{path}", json=payload)
        response.raise_for_status()
        return response

    def _chat_completions(self, *, model: str, messages: list[dict[str, str]], max_tokens: int = 1024, temperature: float = 0.0) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        response = self._post_json("/chat/completions", payload)
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()

    def invoke_model(self, *, modelId: str, body: Any, **_: Any) -> dict[str, Any]:
        parsed_body = body
        if isinstance(body, (bytes, bytearray)):
            parsed_body = body.decode("utf-8", errors="ignore")
        if isinstance(parsed_body, str):
            try:
                parsed_body = json.loads(parsed_body)
            except Exception:
                parsed_body = {}

        # Embeddings compatibility used by BedrockEmbedder.
        if str(modelId).startswith("amazon.titan-embed-text"):
            text = str((parsed_body or {}).get("inputText", ""))
            embed_payload = {
                "model": self._model_for_embeddings(),
                "input": text,
            }
            dims = self._embedding_dimensions()
            if dims is not None:
                embed_payload["dimensions"] = dims
            response = self._post_json("/embeddings", embed_payload).json()
            vec = response["data"][0]["embedding"]
            return {"body": io.BytesIO(json.dumps({"embedding": vec}).encode("utf-8"))}

        if str(modelId).startswith("amazon.titan-embed-image"):
            raise RuntimeError("OpenAI compatibility client does not support Titan image embedding model IDs.")

        # Fallback: treat payload as a text generation request.
        system = str((parsed_body or {}).get("system", ""))
        incoming_messages = (parsed_body or {}).get("messages") or []
        chat_messages: list[dict[str, str]] = []
        if system:
            chat_messages.append({"role": "system", "content": system})
        for m in incoming_messages:
            role = str(m.get("role", "user"))
            content = self._extract_text_from_message_content(m.get("content"))
            chat_messages.append({"role": role, "content": content})
        text = self._chat_completions(
            model=self._model_for_converse(),
            messages=chat_messages or [{"role": "user", "content": ""}],
            max_tokens=int((parsed_body or {}).get("max_tokens", 1024)),
            temperature=float((parsed_body or {}).get("temperature", 0.0)),
        )
        payload = {"content": [{"type": "text", "text": text}]}
        return {"body": io.BytesIO(json.dumps(payload).encode("utf-8"))}

    def converse(
        self,
        *,
        modelId: str,
        system: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        inferenceConfig: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        system_text = ""
        if system:
            system_text = "\n".join(str(s.get("text", "")) for s in system if isinstance(s, dict))
        chat_messages: list[dict[str, str]] = []
        if system_text:
            chat_messages.append({"role": "system", "content": system_text})
        for m in messages or []:
            role = str(m.get("role", "user"))
            content = self._extract_text_from_message_content(m.get("content"))
            chat_messages.append({"role": role, "content": content})

        cfg = inferenceConfig or {}
        text = self._chat_completions(
            model=self._model_for_converse(modelId),
            messages=chat_messages or [{"role": "user", "content": ""}],
            max_tokens=int(cfg.get("maxTokens", 1024)),
            temperature=float(cfg.get("temperature", 0.0)),
        )
        return {"output": {"message": {"content": [{"text": text}]}}}

    def invoke_model_with_response_stream(
        self,
        *,
        modelId: str,
        body: Any,
        **_: Any,
    ) -> dict[str, Iterable[dict[str, Any]]]:
        response = self.invoke_model(modelId=modelId, body=body)
        payload = json.loads(response["body"].read())
        text = ""
        for block in payload.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text += str(block.get("text", ""))
        event = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": text},
        }
        return {"body": [{"chunk": {"bytes": json.dumps(event).encode("utf-8")}}]}


class BearerTokenBedrockClient:
    def __init__(self, *, region: str, api_key: str):
        self.region = region
        self.api_key = api_key
        self.base_url = f"https://bedrock-runtime.{region}.amazonaws.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _url(self, model_id: str, action: str) -> str:
        encoded_model_id = quote(model_id, safe="")
        return f"{self.base_url}/model/{encoded_model_id}/{action}"

    def _post_json(self, url: str, payload: Any) -> requests.Response:
        if isinstance(payload, (bytes, bytearray)):
            response = self.session.post(url, data=payload)
        elif isinstance(payload, str):
            response = self.session.post(url, data=payload.encode("utf-8"))
        else:
            response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response

    def invoke_model(self, *, modelId: str, body: Any, **_: Any) -> dict[str, Any]:
        response = self._post_json(self._url(modelId, "invoke"), body)
        return {"body": io.BytesIO(response.content)}

    def converse(
        self,
        *,
        modelId: str,
        system: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        inferenceConfig: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"messages": messages or []}
        if system:
            payload["system"] = system
        if inferenceConfig:
            payload["inferenceConfig"] = inferenceConfig
        response = self._post_json(self._url(modelId, "converse"), payload)
        return response.json()

    def invoke_model_with_response_stream(
        self,
        *,
        modelId: str,
        body: Any,
        **_: Any,
    ) -> dict[str, Iterable[dict[str, Any]]]:
        response = self.invoke_model(modelId=modelId, body=body)
        payload = json.loads(response["body"].read())
        response["body"].seek(0)

        text = ""
        for block in payload.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")

        event = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": text},
        }
        return {"body": [{"chunk": {"bytes": json.dumps(event).encode("utf-8")}}]}



def _has_standard_aws_credentials() -> bool:
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    return bool(access_key and secret_key)



def _has_bedrock_api_key() -> bool:
    return bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))



def create_bedrock_runtime_client(region: str | None = None):
    region = region or os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    if _has_standard_aws_credentials():
        return boto3.client("bedrock-runtime", region_name=region)

    api_key = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    if api_key:
        return BearerTokenBedrockClient(region=region, api_key=api_key)

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return OpenAICompatClient(api_key=openai_key)

    raise RuntimeError(
        "Bedrock authentication is not configured. Set AWS_BEARER_TOKEN_BEDROCK "
        "or standard AWS credentials (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY), "
        "or set OPENAI_API_KEY for OpenAI fallback."
    )
