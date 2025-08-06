import os
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from .utils.prompt import ClientMessage, convert_to_openai_messages
from .utils.utils import stream_text


load_dotenv(".env")

app = FastAPI()


class Request(BaseModel):
    messages: List[ClientMessage]


@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query('data')):
    print("Received request in handle_chat_data")
    messages = request.messages
    openai_messages = convert_to_openai_messages(messages)
    print("Messages sent to OpenAI:", openai_messages)

    response = StreamingResponse(stream_text(openai_messages, protocol))
    response.headers['x-vercel-ai-data-stream'] = 'v1'
    return response
