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
from .agents.orchestrator import career_agent, create_ephemeral_session
from agents import Runner, ItemHelpers  # type: ignore
from openai.types.responses import ResponseTextDeltaEvent  # type: ignore

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
            yield json.dumps({"event": "thinking", "data": "Starting agent..."}) + "\n"

            # Create a new session per request to avoid accumulating memory across refreshes
            session = create_ephemeral_session()
            result = Runner.run_streamed(career_agent, input=combined_text, session=session)

            accumulated_text = ""

            async for event in result.stream_events():
                # Stream raw token deltas as progressively growing final content
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    delta = event.data.delta or ""
                    if delta:
                        accumulated_text += delta
                        yield json.dumps({"event": "final", "response": accumulated_text}) + "\n"
                    continue

                # Agent switched/updated
                if event.type == "agent_updated_stream_event":
                    payload = {
                        "event": "thinking",
                        "data": {"type": "agent_updated", "new_agent": event.new_agent.name},
                    }
                    yield json.dumps(payload) + "\n"
                    continue

                # High-level run item events
                if event.type == "run_item_stream_event":
                    if event.item.type == "tool_call_item":
                        # try to extract a readable tool name
                        tool_name = (
                            getattr(event.item, "tool_name", None)
                            or getattr(getattr(event.item, "tool", None), "name", None)
                            or getattr(getattr(event.item, "tool_call", None), "name", None)
                            or "unknown_tool"
                        )
                        yield json.dumps({
                            "event": "thinking",
                            "data": {"type": "tool_call", "tool": tool_name},
                        }) + "\n"
                    elif event.item.type == "tool_call_output_item":
                        # do not forward full tool outputs (can be huge). Only signal completion
                        tool_name = (
                            getattr(event.item, "tool_name", None)
                            or getattr(getattr(event.item, "tool", None), "name", None)
                            or getattr(getattr(event.item, "tool_call", None), "name", None)
                            or "unknown_tool"
                        )
                        yield json.dumps({
                            "event": "thinking",
                            "data": {"type": "tool_output", "tool": tool_name, "status": "completed"},
                        }) + "\n"
                    elif event.item.type == "message_output_item":
                        # Optional: show completed message chunks at item level
                        text = ItemHelpers.text_message_output(event.item) or ""
                        # keep this concise for the Thinking panel
                        snippet = (text[:200] + ("..." if len(text) > 200 else "")) if text else ""
                        if snippet:
                            yield json.dumps({
                                "event": "thinking",
                                "data": {"type": "message_output", "text": snippet},
                            }) + "\n"
                    continue
        except Exception as e:
            import traceback
            err = {"event": "error", "message": str(e), "trace": traceback.format_exc()[:2000]}
            yield json.dumps(err) + "\n"

    return StreamingResponse(ndjson_stream(), media_type="application/x-ndjson")
