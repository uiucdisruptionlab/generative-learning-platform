import boto3
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.getenv("AWS_REGION", "us-east-1")
)

def extract_json(text: str) -> str:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else text

async def get_onboarding_step(user_input: str, history: list = None):
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    
    formatted_messages = []

    # FIX: Bedrock MUST start with a 'user' message. 
    # If history is empty, we just send the current input.
    # If history exists, we process it normally.
    if history:
        for msg in history:
            # Handle both Pydantic objects and raw dicts
            role = msg.role if hasattr(msg, 'role') else msg.get('role')
            content = msg.content if hasattr(msg, 'content') else msg.get('content')
            
            # Skip empty messages to prevent ValidationExceptions
            if not content or not content.strip():
                continue
                
            formatted_messages.append({
                "role": role,
                "content": [{"text": content}]
            })

    # Add the current user message at the end
    formatted_messages.append({
        "role": "user",
        "content": [{"text": user_input if user_input.strip() else "Hello"}]
    })

    # If for some reason the first message in the list isn't 'user', 
    # Bedrock will throw the error you saw. This is the safety net:
    if formatted_messages and formatted_messages[0]["role"] != "user":
        formatted_messages.pop(0) # Remove the leading assistant message

    system_prompt = """You are an onboarding assistant for a Generative Learning Platform. 
    Your job is to help collect student onboarding information through a short, natural conversation. 
    You will be given: 
    1. The user's current structured profile. 
    2. The conversation history. 
    3. The user's latest message. 
    You MUST return valid JSON only. No markdown. 
    Your goals: 
    - Be extremely conversational. Don't sound like a bot. 
    - Ask for only ONE or TWO pieces of information at a time. 
    - Do not ask for information already known. 
    - Personalize lightly based on what the user already said. 
    - Extract structured updates from the latest user message. 
    - Get all the information that is needed for the json, only stop if the user seems finished
    - Decide whether the user seems finished, especially if they say things like 'no, that's all', 'that's it for now', 'nothing else', 'we are good', etc. 
    - If the user seems finished AND the required fields are already collected, then your assistant_reply should be a brief closing message rather than another question. 
    - If the user seems finished but required fields are missing, politely ask for the single most important missing field. 
    - Prefer these fields in this order when missing: name, major, academic_level, learning_goals, interests, and weekly_hours. Try to get all the fields for Output format. Use null for any unknown extracted field. 
    MANDATORY OUTPUT FORMAT (JSON ONLY) after talking to the user: 
    { "assistant_reply": "string", 
    "extracted_updates": { 
    "id": "uuid or null", 
    "name": "string or null", 
    "major_or_field": "string or null", 
    "learning_goals": "json or null", 
    "interests": jsonb or null, 
    "academic_level": "string or integer or null", 
    "weekly_hours": "integer or null", 
    "preferred_formats": "jsonb or null", 
    "llm_profile": "jsonb or null", 
    "created_at": "timestamp or null", 
    "updated_at": "timestamp or null" }, 
    "user_seems_finished": true, 
    "missing_fields": ["field_name", "..."] 
    } """

    try:
        response = client.converse(
            modelId=model_id,
            messages=formatted_messages,
            system=[{"text": system_prompt}],
            inferenceConfig={"temperature": 0}
        )
        
        raw_text = response['output']['message']['content'][0]['text']
        
        try:
            ai_data = json.loads(extract_json(raw_text))
        except:
            ai_data = {
                "assistant_reply": raw_text,
                "extracted_updates": {},
                "user_seems_finished": False
            }
        return ai_data

    except Exception as e:
        print(f"Bedrock Error: {e}")
        raise e