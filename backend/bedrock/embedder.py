import os
import json
import boto3
from typing import List


class BedrockEmbedder:

    def __init__(self, region: str | None = None):
        region = region or os.getenv("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def embed_data(self, text:str) -> List[float]:
        """
        Embed text using Amazon Titan Embed Text v2.
        Input: text string
        Returns: embedding vector
        """
        model_id = "amazon.titan-embed-text-v2:0"
        req = json.dumps({"inputText" : text})
        r = self.client.invoke_model(modelId=model_id, body=req)
        body = json.loads(r["body"].read())
        
        return body["embedding"]

    def embed_image(self, image_bytes: bytes) -> List[float]:
        """
        Embed an image using Amazon Titan Embed Image v1.
        Input: raw image bytes (PNG, JPEG, etc.)
        Returns: embedding vector
        """
        model_id = "amazon.titan-embed-image-v1:0"
        r = self.client.invoke_model(modelId=model_id, body=image_bytes)
        body = json.loads(r["body"].read())
        
        return body["embedding"]

    def embed_image_from_path(self, image_path: str) -> List[float]:
        """
        Load image from file path and embed it.
        """
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        return self.embed_image(image_bytes)

