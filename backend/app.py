import os
import base64
from io import BytesIO
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
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

    # Run the OpenAI Agent
    try:
        final_response = await handle_user_message(combined_text)
        print("Agent final response:\n" + str(final_response))
        return JSONResponse(content={"response": final_response})
    except Exception as e:
        import traceback
        print("Error while handling chat:", e)
        print(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=500)
