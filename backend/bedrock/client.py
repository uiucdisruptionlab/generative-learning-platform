from __future__ import annotations

import io
import json
import os
from typing import Any, Iterable
from urllib.parse import quote

import boto3
import requests
from botocore.config import Config


class BearerTokenBedrockClient:
    def __init__(self, *, region: str, api_key: str, connect_timeout: float = 10.0, read_timeout: float = 180.0):
        self.region = region
        self.api_key = api_key
        self._timeout = (connect_timeout, read_timeout)
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
            response = self.session.post(url, data=payload, timeout=self._timeout)
        elif isinstance(payload, str):
            response = self.session.post(url, data=payload.encode("utf-8"), timeout=self._timeout)
        else:
            response = self.session.post(url, json=payload, timeout=self._timeout)
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
    read_timeout = float(os.getenv("BEDROCK_READ_TIMEOUT", "180"))
    connect_timeout = float(os.getenv("BEDROCK_CONNECT_TIMEOUT", "10"))
    boto_cfg = Config(
        read_timeout=read_timeout,
        connect_timeout=connect_timeout,
        retries={"max_attempts": 3, "mode": "standard"},
    )

    if _has_standard_aws_credentials():
        return boto3.client("bedrock-runtime", region_name=region, config=boto_cfg)

    api_key = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    if api_key:
        return BearerTokenBedrockClient(
            region=region,
            api_key=api_key,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )

    raise RuntimeError(
        "Bedrock authentication is not configured. Set AWS_BEARER_TOKEN_BEDROCK "
        "or standard AWS credentials (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)."
    )
