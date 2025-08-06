import json
from enum import Enum
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from pydantic import BaseModel
import base64
import fitz  # PyMuPDF
from typing import List, Optional, Any
from .attachment import ClientAttachment, Attachment


class ToolInvocationState(str, Enum):
    CALL = 'call'
    PARTIAL_CALL = 'partial-call'
    RESULT = 'result'


class ToolInvocation(BaseModel):
    state: ToolInvocationState
    toolCallId: str
    toolName: str
    args: Any
    result: Any


class ClientMessage(BaseModel):
    role: str
    content: str
    experimental_attachments: Optional[List[ClientAttachment]] = None
    toolInvocations: Optional[List[ToolInvocation]] = None


def convert_to_openai_messages(messages: List[ClientMessage], attachments: Optional[List[Attachment]] = None) -> List[ChatCompletionMessageParam]:
    openai_messages = []

    for index, message in enumerate(messages):
        parts = []
        tool_calls = []

        parts.append({
            'type': 'text',
            'text': message.content
        })

        # Only add attachments to the last user message
        if attachments and message.role == 'user' and index == len(messages) - 1:
            for attachment in attachments:
                if attachment.type.startswith('image/'):
                    parts.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': attachment.content
                        }
                    })
                elif attachment.type == 'application/pdf':
                    # Decode the base64 string
                    pdf_bytes = base64.b64decode(attachment.content.split(',')[1])
                    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                    
                    pdf_text = ""
                    for page_num in range(len(pdf_document)):
                        page = pdf_document.load_page(page_num)
                        pdf_text += page.get_text()

                    parts.append({
                        'type': 'text',
                        'text': f"PDF Content:\n{pdf_text}"
                    })

        if message.experimental_attachments:
            for attachment in message.experimental_attachments:
                if attachment.contentType.startswith('image'):
                    parts.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': attachment.url
                        }
                    })
                elif attachment.contentType.startswith('text'):
                    parts.append({
                        'type': 'text',
                        'text': attachment.url
                    })

        if message.toolInvocations:
            for toolInvocation in message.toolInvocations:
                tool_calls.append({
                    "id": toolInvocation.toolCallId,
                    "type": "function",
                    "function": {
                        "name": toolInvocation.toolName,
                        "arguments": json.dumps(toolInvocation.args)
                    }
                })

        tool_calls_dict = {"tool_calls": tool_calls} if tool_calls else {}

        openai_messages.append({
            "role": message.role,
            "content": parts,
            **tool_calls_dict,
        })

        if message.toolInvocations:
            for toolInvocation in message.toolInvocations:
                tool_message = {
                    "role": "tool",
                    "tool_call_id": toolInvocation.toolCallId,
                    "content": json.dumps(toolInvocation.result),
                }
                openai_messages.append(tool_message)

    return openai_messages
