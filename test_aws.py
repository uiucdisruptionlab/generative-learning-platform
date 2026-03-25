import os
import boto3
from dotenv import load_dotenv

# This is the most important line!
load_dotenv() 

token = os.getenv("AWS_BEARER_TOKEN")
region = os.getenv("AWS_REGION", "us-east-1")

if not token:
    print("❌ ERROR: Your .env file is not being read or AWS_BEARER_TOKEN is empty.")
else:
    try:
        # We manually pass the token into the 'aws_session_token' slot
        client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            aws_access_key_id="NOT_NEEDED", # Some SDK versions require a dummy string
            aws_secret_access_key="NOT_NEEDED",
            aws_session_token=token
        )
        print(f"✅ Credentials located! Attempting to contact {region}...")
        # ... rest of your invoke_model code ...
    except Exception as e:
        print(f"Connection Failed: {e}")