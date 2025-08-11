import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from .utils.prompt import ClientMessage
from .agents.orchestrator import handle_user_message

load_dotenv(".env")

app = FastAPI()

# Agents SDK uses a session internally; nothing to instantiate here

class Request(BaseModel):
    messages: List[ClientMessage]
    data: Optional[dict] = None

@app.post("/api/chat")
async def handle_chat_data(request: Request):
    print("Received request in handle_chat_data")

    # Extract the last user message to use as the prompt
    if not request.messages:
        return JSONResponse(content={"error": "No messages provided"}, status_code=400)
    
    user_message = request.messages[-1].content
    print(f"User message: {user_message}")

    # Run the OpenAI Agent
    try:
        final_response = await handle_user_message(user_message)
        print("Agent final response:\n" + str(final_response))
        return JSONResponse(content={"response": final_response})
    except Exception as e:
        import traceback
        print("Error while handling chat:", e)
        print(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=500)
