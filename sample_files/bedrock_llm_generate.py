import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()  # Loads AWS_BEARER_TOKEN_BEDROCK from .env in project root

# Create an Amazon Bedrock client
client = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"  # If you've configured a default region, you can omit this line
)

# # Define the model and message
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
messages = [{"role": "user", "content": [{"text": "Hello"}]}]

response = client.converse(
    modelId=model_id,
    messages=messages,
)
print(response)

model_id = "amazon.titan-embed-text-v2:0"

input_text = "Please recommend books with a theme similar to the movie 'Inception'."

# Create the request for the model.
native_request = {"inputText": input_text}

# Convert the native request to JSON.
request = json.dumps(native_request)

# Invoke the model with the request.
response = client.invoke_model(modelId=model_id, body=request)

# Decode the model's native response body.
model_response = json.loads(response["body"].read())

# Extract and print the generated embedding and the input text token count.
embedding = model_response["embedding"]
input_token_count = model_response["inputTextTokenCount"]

print("\nYour input:")
print(input_text)
print(f"Number of input tokens: {input_token_count}")
print(f"Size of the generated embedding: {len(embedding)}")
print("Embedding:")
print(embedding)


print(response)
