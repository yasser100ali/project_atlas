from __future__ import annotations

import base64
import io
import json
from typing import Optional, List

from agents import function_tool  # type: ignore
from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader


@function_tool(name_override="extract_resume_text")
def extract_resume_text(pdf_base64: Optional[str] = None, file_path: Optional[str] = None) -> str:
    """Extract plain text from a PDF resume using pypdf. Provide either pdf_base64 (data URL ok) or file_path."""
    if not pdf_base64 and not file_path:
        return "Error: Provide pdf_base64 or file_path."

    try:
        if pdf_base64:
            if "," in pdf_base64:
                pdf_base64 = pdf_base64.split(",", 1)[1]
            pdf_bytes = base64.b64decode(pdf_base64)
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)
        else:
            reader = PdfReader(file_path or "")

        extracted = []
        for page in reader.pages:
            extracted.append(page.extract_text() or "")
        return "\n".join(extracted).strip()
    except Exception as e:
        return f"Error extracting PDF text: {e}"


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    skills: Optional[List[str]] = None
    summary: Optional[str] = None


@function_tool(name_override="resume_generator")
def resume_generator(profile: Profile, job_desc: Optional[str] = None) -> str:
    """Generate a simple Markdown resume from a Profile. Returns JSON with {text}."""
    name = profile.name or "Candidate"
    skills = ", ".join(profile.skills or [])
    summary = profile.summary or ""
    sections = []
    if summary:
        sections.append(f"## Summary\n{summary}")
    if skills:
        sections.append(f"## Skills\n{skills}")
    if job_desc:
        sections.append(f"## Target Role\n{job_desc}")
    md = "# " + name + "\n\n" + "\n\n".join(sections) + "\n"
    return json.dumps({"text": md})

