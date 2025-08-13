import os
import json
import base64
from io import BytesIO
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pypdf import PdfReader
from .utils.prompt import ClientMessage
from .utils.attachment import Attachment
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

    # Parse attachments (if any) for PDFs and extract text
    attachments: List[Attachment] = []
    if request.data and isinstance(request.data, dict) and request.data.get("attachments"):
        try:
            attachments = [Attachment(**att) for att in request.data["attachments"]]
        except Exception as e:
            print("Failed to parse attachments:", e)

    pdf_texts: List[str] = []
    for att in attachments:
        if att.type == "application/pdf" and att.content:
            try:
                # Expecting data URL like: data:application/pdf;base64,<b64>
                if "," in att.content:
                    b64 = att.content.split(",", 1)[1]
                else:
                    b64 = att.content
                pdf_bytes = base64.b64decode(b64)
                pdf_reader = PdfReader(BytesIO(pdf_bytes))
                text = "".join([(page.extract_text() or "") for page in pdf_reader.pages])
                if text.strip():
                    pdf_texts.append(text)
            except Exception as e:
                print(f"Failed to extract PDF text from {att.name}:", e)

    combined_text = user_message
    if pdf_texts:
        combined_text = user_message + "\n\nPDF Content:\n" + "\n\n".join(pdf_texts)

    async def ndjson_stream():
        try:
            # Initial thinking hint
            yield json.dumps({"event": "thinking", "data": "Starting agent..."}) + "\n"

            import asyncio
            queue: asyncio.Queue = asyncio.Queue()

            async def on_event(event_type, data):
                # forward tool/attempt events as thinking lines
                payload = {"event": "thinking", "data": {"type": event_type, **(data or {})}}
                await queue.put(json.dumps(payload) + "\n")

            # Run agent concurrently while flushing queue
            done = False

            async def run_agent():
                final = await handle_user_message(combined_text, on_event=on_event)
                await queue.put(json.dumps({"event": "final", "response": final}) + "\n")
                return

            task = asyncio.create_task(run_agent())
            while not task.done() or not queue.empty():
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=0.2)
                    yield line
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.05)
            # ensure any exception is raised
            await task
        except Exception as e:
            import traceback
            err = {"event": "error", "message": str(e), "trace": traceback.format_exc()[:2000]}
            yield json.dumps(err) + "\n"

    return StreamingResponse(ndjson_stream(), media_type="application/x-ndjson")
