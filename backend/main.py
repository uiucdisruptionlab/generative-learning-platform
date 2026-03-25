import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schemas import ChatRequest, ChatResponse
from services.claude_service import get_onboarding_step

app = FastAPI()

# Enable CORS so your Vite frontend can talk to this FastAPI server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Prevent Bedrock ValidationException by ensuring text is not empty
        user_msg = request.message.strip() if request.message else "Hello"
        if not user_msg:
            user_msg = "Hello"

        ai_data = await get_onboarding_step(user_msg, request.history)
        
        return ChatResponse(
            reply=ai_data.get("assistant_reply", "I'm listening, tell me more!"),
            is_onboarding_complete=bool(ai_data.get("user_seems_finished", False)),
            updates=ai_data.get("extracted_updates") or {}
        )
    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Reload=True helps during dev, main:app refers to this filename and the FastAPI instance
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)