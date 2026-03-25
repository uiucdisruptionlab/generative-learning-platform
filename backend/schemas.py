from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]

class ChatResponse(BaseModel):
    reply: str
    is_onboarding_complete: bool
    # We keep 'updates' so the backend can save data
    updates: Dict[str, Any] 
    # Adding this helps the logic "know" what's left
    missing_fields: Optional[List[str]] = []