import os
import json
import base64
from io import BytesIO
from typing import List, Optional, Dict
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from urllib.parse import quote
from pypdf import PdfReader
from .utils.prompt import ClientMessage
from .utils.attachment import Attachment
from .agents.orchestrator import career_agent, create_ephemeral_session
from .agents.resume_agent import get_successful_response_with_base64
from agents import SQLiteSession  # type: ignore
from agents import Runner, ItemHelpers  # type: ignore
from openai.types.responses import ResponseTextDeltaEvent  # type: ignore

load_dotenv(".env")

# Debug environment variables
print(f"[DEBUG] Environment variables:")
print(f"[DEBUG] VERCEL: {os.getenv('VERCEL')}")
print(f"[DEBUG] RENDER_WORKER_URL: {os.getenv('RENDER_WORKER_URL')}")
print(f"[DEBUG] RENDER_WORKER_AUTH: {'***' if os.getenv('RENDER_WORKER_AUTH') else 'None'}")

app = FastAPI()

# Persist agent sessions per chatId so context is preserved across requests
SESSIONS: Dict[str, SQLiteSession] = {}

# Agents SDK uses a session internally; nothing to instantiate here

class Request(BaseModel):
    messages: List[ClientMessage]
    data: Optional[dict] = None
    chatId: Optional[str] = "default"

@app.post("/api/chat")
async def handle_chat_data(request: Request):
    print("Received request in handle_chat_data")

    # Debug: Log chat history and memory info
    print(f"[DEBUG] Chat ID: {request.chatId or 'default'}")
    print(f"[DEBUG] Number of messages in history: {len(request.messages)}")
    if len(request.messages) > 0:
        print(f"[DEBUG] First message: {request.messages[0].content[:100]}...")
        print(f"[DEBUG] Last message: {request.messages[-1].content[:100]}...")

        # Calculate approximate token count for chat history
        total_chars = sum(len(msg.content) for msg in request.messages)
        estimated_tokens = total_chars // 4  # Rough estimate: 1 token ≈ 4 chars
        print(f"[DEBUG] Total characters in chat history: {total_chars}")
        print(f"[DEBUG] Estimated tokens in chat history: {estimated_tokens}")

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

    # Debug: Log the final combined text length
    print(f"[DEBUG] Final combined text length: {len(combined_text)}")
    print(f"[DEBUG] Estimated tokens in combined text: {len(combined_text) // 4}")
    print(f"[DEBUG] Combined text preview: {combined_text[:200]}...")

    async def ndjson_stream():
        try:
            yield json.dumps({"event": "thinking", "data": "Starting agent..."}) + "\n"

            # Use or create persistent session per chatId
            chat_id = request.chatId or "default"
            session = SESSIONS.get(chat_id)
            if session is None:
                session = create_ephemeral_session()
                SESSIONS[chat_id] = session

            result = Runner.run_streamed(career_agent, input=combined_text, session=session)

            accumulated_text = ""
            last_pdf: Optional[dict] = None

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
                        print(f"[DEBUG] Tool call detected: {tool_name}")
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
                        # Surface resume PDF to client if available from resume_builder/rendercv_render
                        try:
                            output = getattr(event.item, "output", None)
                            print(
                                f"[tool_call_output_item] tool={tool_name}, output_type={type(output)},\n"
                                f"snippet={str(output)[:300] if output is not None else '(none)'}\n"
                            )
                            # Be robust: sometimes tool metadata is missing. Detect by output shape.
                            if output is not None:
                                parsed = None
                                if isinstance(output, str):
                                    try:
                                        parsed = json.loads(output)
                                    except Exception as e:
                                        print(f"[resume_ready] json.loads failed: {e}")
                                elif isinstance(output, dict):
                                    parsed = output

                                if isinstance(parsed, dict):
                                    print(f"[resume_ready] parsed keys: {list(parsed.keys())}")

                                    # Check if this is a clean success message - if so, get the real data from global
                                    if (parsed.get("success") and parsed.get("has_base64") and
                                        not parsed.get("pdf_b64")):
                                        print(f"[DEBUG] Detected clean success message, checking for full response...")
                                        full_response = get_successful_response_with_base64()
                                        if full_response:
                                            try:
                                                parsed = json.loads(full_response)
                                                print(f"[DEBUG] Using full response with base64 data")
                                            except:
                                                print(f"[DEBUG] Failed to parse full response")
                                                parsed = None

                                    if parsed:
                                        pdf_path = parsed.get("pdf_path")
                                        if not pdf_path:
                                            out_dir = parsed.get("output_folder")
                                            fname = parsed.get("filename")
                                            if isinstance(out_dir, str) and isinstance(fname, str):
                                                pdf_path = os.path.join(out_dir, fname)
                                        filename = parsed.get("filename") or "resume.pdf"

                                        # Build URL. Prefer file path but allow base64 fallback if path not under base_dir
                                        file_url = None
                                        if isinstance(pdf_path, str):
                                            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                                            base_dir = os.path.abspath(os.path.join(project_root, "generated_resumes"))
                                            real = os.path.abspath(pdf_path)
                                            if real.startswith(base_dir) and os.path.exists(real):
                                                file_url = f"/api/file?path={quote(real)}"
                                            else:
                                                b64 = parsed.get("pdf_b64")
                                                if isinstance(b64, str) and len(b64) > 0:
                                                    file_url = f"data:application/pdf;base64,{b64}"
                                        else:
                                            b64 = parsed.get("pdf_b64")
                                            if isinstance(b64, str) and len(b64) > 0:
                                                file_url = f"data:application/pdf;base64,{b64}"

                                        print(f"\nHere is that pdf path: {pdf_path}\nHere is the filename: {filename}\nUsing URL: {file_url}\n\n")
                                        if file_url:
                                            last_pdf = {"url": file_url, "name": filename, "contentType": "application/pdf"}
                                            print(f"[DEBUG] About to emit resume_ready event with data: {last_pdf}")
                                            yield json.dumps({
                                                "event": "resume_ready",
                                                "data": last_pdf,
                                            }) + "\n"
                                            print(f"[resume_ready] emitted with url={file_url}")
                                        else:
                                            print("[resume_ready] No usable URL (no path and no b64)")
                        except Exception as e:
                            print(f"\nError: {e}\n")
                            pass
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
            # After streaming finishes, re-emit resume_ready if we saw a PDF but the client may have missed it
            if last_pdf is not None:
                yield json.dumps({"event": "resume_ready", "data": last_pdf}) + "\n"

        except Exception as e:
            import traceback
            err = {"event": "error", "message": str(e), "trace": traceback.format_exc()[:2000]}
            yield json.dumps(err) + "\n"

    return StreamingResponse(ndjson_stream(), media_type="application/x-ndjson")


@app.get("/api/file")
async def get_file(path: str):
    # Only serve files from generated_resumes to prevent arbitrary file access
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    base_dir = os.path.abspath(os.path.join(project_root, "generated_resumes"))
    tmp_base = "/tmp/generated_resumes"
    real = os.path.abspath(path)
    if not (real.startswith(base_dir) or real.startswith(tmp_base)):
        return JSONResponse(content={"error": "Forbidden"}, status_code=403)
    media = "application/pdf" if real.lower().endswith(".pdf") else "application/octet-stream"
    # For PDFs, set inline so browsers can preview; avoid default 'attachment' disposition
    if media == "application/pdf":
        return FileResponse(
            real,
            media_type=media,
            headers={"Content-Disposition": f"inline; filename=\"{os.path.basename(real)}\""},
        )
    return FileResponse(real, media_type=media, filename=os.path.basename(real))


class ResetRequest(BaseModel):
    chatId: Optional[str] = "default"


@app.post("/api/session/reset")
async def reset_session(req: ResetRequest):
    chat_id = req.chatId or "default"
    print(f"[DEBUG] Session reset requested for chat_id: {chat_id}")
    print(f"[DEBUG] Sessions before reset: {list(SESSIONS.keys())}")

    # Remove existing session so a new one is created on next message
    if chat_id in SESSIONS:
        try:
            del SESSIONS[chat_id]
            print(f"[DEBUG] Successfully removed session: {chat_id}")
        except Exception as e:
            print(f"[DEBUG] Error removing session: {e}")
    else:
        print(f"[DEBUG] Session {chat_id} not found in active sessions")

    print(f"[DEBUG] Sessions after reset: {list(SESSIONS.keys())}")
    return JSONResponse(content={"ok": True, "chatId": chat_id})
