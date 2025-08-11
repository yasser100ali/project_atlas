import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from .utils.prompt import ClientMessage
from .agents.career_copilot import handle_user_message

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

    # Run the OpenAI Agent
    final_response = await handle_user_message(user_message)
    return JSONResponse(content={"response": final_response})
