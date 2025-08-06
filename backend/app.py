import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from .utils.prompt import ClientMessage, convert_to_openai_messages
from .utils.utils import stream_text
from .utils.attachment import Attachment


load_dotenv(".env")

app = FastAPI()


class Request(BaseModel):
    messages: List[ClientMessage]
    data: Optional[dict] = None


@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query('data')):
    print("Received request in handle_chat_data")

    attachments = []
    if request.data and 'attachments' in request.data:
        attachments = [Attachment(**attachment) for attachment in request.data['attachments']]
        print(f"Received {len(attachments)} attachments:")
        for attachment in attachments:
            print(f"- {attachment.name} ({attachment.type})")

    messages = request.messages
    openai_messages = convert_to_openai_messages(messages, attachments)
    print("Messages sent to OpenAI:", openai_messages)

    response = StreamingResponse(stream_text(openai_messages, protocol))
    response.headers['x-vercel-ai-data-stream'] = 'v1'
    return response
