import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from .utils.prompt import ClientMessage
from .agents.career_copilot import CareerAgent

load_dotenv(".env")

app = FastAPI()

# Instantiate the CareerAgent once when the application starts
career_agent = CareerAgent()

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

    # Run the agent with the user's message
    agent_response = career_agent.run(prompt=user_message)

    # The Langchain agent's response is a dictionary.
    # We will extract the 'output' to send back to the client.
    final_response = agent_response.get("output", "Sorry, I encountered an error.")

    return JSONResponse(content={"response": final_response})
