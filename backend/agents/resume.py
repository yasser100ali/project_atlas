from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
import tempfile
import textwrap
from typing import Optional, Type

import yaml
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from pypdf import PdfReader


class ResumeTextExtractorInput(BaseModel):
    pdf_base64: Optional[str] = Field(
        default=None,
        description="A data URL or raw base64 string of the PDF to extract text from.",
    )
    file_path: Optional[str] = Field(
        default=None, description="Absolute path to a local PDF file to extract text from."
    )


class ResumeTextExtractor(BaseTool):
    name = "extract_resume_text"
    description = "Extracts plain text content from a PDF resume using pypdf. Provide either pdf_base64 or file_path."
    args_schema: Type[BaseModel] = ResumeTextExtractorInput

    def _run(self, pdf_base64: Optional[str] = None, file_path: Optional[str] = None) -> str:
        if not pdf_base64 and not file_path:
            return "Error: Provide pdf_base64 or file_path."

        try:
            if pdf_base64:
                # Support optional data URL prefix
                if "," in pdf_base64:
                    pdf_base64 = pdf_base64.split(",", 1)[1]
                pdf_bytes = base64.b64decode(pdf_base64)
                pdf_file = io.BytesIO(pdf_bytes)
                reader = PdfReader(pdf_file)
            else:
                if not os.path.isfile(file_path):
                    return f"Error: File not found: {file_path}"
                reader = PdfReader(file_path)

            extracted_text_parts = []
            for page in reader.pages:
                text = page.extract_text() or ""
                extracted_text_parts.append(text)

            return "\n".join(extracted_text_parts).strip()
        except Exception as e:
            return f"Error extracting PDF text: {e}"

    async def _arun(self, pdf_base64: Optional[str] = None, file_path: Optional[str] = None) -> str:
        return self._run(pdf_base64=pdf_base64, file_path=file_path)


class ResumeGeneratorInput(BaseModel):
    user_prompt: str = Field(
        description="User instructions/context for the resume. Include any updates or requirements."
    )
    extracted_resume_text: Optional[str] = Field(
        default=None, description="Plain text extracted from an existing resume (optional)."
    )


class ResumeGenerator(BaseTool):
    name = "resume_generator"
    description = (
        "Generates a resume with RenderCV. It asks the LLM to produce valid RenderCV YAML based on user_prompt "
        "(and optional extracted_resume_text), corrects the YAML if needed, runs rendercv, and returns a JSON "
        "with {text, pdf_base64}."
    )
    args_schema: Type[BaseModel] = ResumeGeneratorInput

    def _run(self, user_prompt: str, extracted_resume_text: Optional[str] = None) -> str:
        # Compose system + user content for YAML generation
        system_prompt = self._build_yaml_system_prompt()
        user_content = self._build_user_content(user_prompt, extracted_resume_text)

        # Call LLM (LangChain ChatOpenAI) to obtain YAML (model must be accessible via OPENAI_API_KEY)
        llm = ChatOpenAI(temperature=0, model="gpt-4.1")
        llm_response = llm.invoke(
            [
                ("system", system_prompt),
                ("user", user_content),
            ]
        )
        raw_text = getattr(llm_response, "content", "") or ""

        # Extract YAML fenced block if present
        yaml_code = self._extract_yaml_block(raw_text)
        if not yaml_code.strip():
            return json.dumps({
                "text": "Failed to get YAML from the model.",
                "pdf_base64": None,
            })

        # Correct YAML
        corrected_yaml = self._correct_rendercv_yaml(yaml_code)
        if corrected_yaml.startswith("Error:"):
            return json.dumps({
                "text": f"YAML correction failed: {corrected_yaml}",
                "pdf_base64": None,
            })

        # Generate PDF via rendercv
        result_json = self._generate_and_execute_bash(corrected_yaml)
        return json.dumps(result_json)

    async def _arun(self, user_prompt: str, extracted_resume_text: Optional[str] = None) -> str:
        return self._run(user_prompt=user_prompt, extracted_resume_text=extracted_resume_text)

    # ---------- Helpers ----------

    def _build_yaml_system_prompt(self) -> str:
        return (
            "You are an expert resume creator using RenderCV. Output only YAML wrapped in ```yaml fences. "
            "Ensure the YAML strictly follows RenderCV schema. Use concise one-page resume guidance. "
            "Top-level keys are only 'cv' and 'design' at the same indentation level. Use design: theme: sb2nov."
        )

    def _build_user_content(self, user_prompt: str, extracted_resume_text: Optional[str]) -> str:
        merged = [
            "User instructions:",
            user_prompt.strip(),
        ]
        if extracted_resume_text:
            merged.append("\nExisting resume text (for reference):\n" + extracted_resume_text.strip())
        return "\n\n".join(merged)

    def _extract_yaml_block(self, text: str) -> str:
        # Find fenced yaml block ```yaml ... ```; fallback to whole text
        match = re.search(r"```yaml\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _correct_rendercv_yaml(self, yaml_str: str) -> str:
        # Normalize line endings and strip trailing spaces
        yaml_str = "\n".join(line.rstrip() for line in yaml_str.splitlines())

        # Move misplaced top-level keys (design, locale, rendercv_settings)
        top_level_keys = ["design", "locale", "rendercv_settings"]
        misplaced = {}
        for key in top_level_keys:
            pattern = rf"^(\s{{2,}}){key}:\n((^\1  .*\n?)*)"
            match = re.search(pattern, yaml_str, re.MULTILINE)
            if match:
                indent = match.group(1)
                block = match.group(0)
                deindented_block = textwrap.dedent(block.replace(indent, "", 1))
                misplaced[key] = deindented_block
                yaml_str = re.sub(pattern, "", yaml_str, flags=re.MULTILINE)

        for block in misplaced.values():
            yaml_str += "\n\n" + block.strip()

        if re.match(r"^\s{2,}cv:", yaml_str, re.MULTILINE):
            yaml_str = textwrap.dedent(yaml_str)

        # Normalize indentation to multiples of 2
        lines = []
        for line in yaml_str.splitlines():
            indent_match = re.match(r"^(\s+)", line)
            if indent_match:
                original_indent = len(indent_match.group(1))
                new_indent = " " * (original_indent // 2 * 2)
                line = re.sub(r"^\s+", new_indent, line)
            lines.append(line)
        yaml_str = "\n".join(lines)

        # Validate/coerce structure
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            return f"Error: Invalid YAML syntax - {e}\nOriginal:\n{yaml_str}"

        if data is None:
            return "Error: Empty YAML"

        if "cv" not in data:
            return "Error: Missing required top-level 'cv' key"
        if "sections" not in data["cv"]:
            data["cv"]["sections"] = {}

        allowed_root = {"cv", "design", "locale", "rendercv_settings"}
        data = {k: v for k, v in data.items() if k in allowed_root}

        corrected = yaml.dump(data, default_flow_style=False, indent=2, sort_keys=False)
        if "cv" in data and "sections" in data["cv"] and isinstance(data["cv"]["sections"], dict):
            return corrected
        return f"Error: Invalid structure after correction\nCorrected:\n{corrected}"

    def _generate_and_execute_bash(self, yaml_code: str) -> dict:
        # Write YAML to temp file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp_yaml:
            tmp_yaml.write(yaml_code.encode("utf-8"))
            yaml_path = tmp_yaml.name

        try:
            # Run rendercv (expects 'rendercv' CLI to be installed and on PATH)
            cmd = ["rendercv", "render", yaml_path]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0:
                return {"text": f"RenderCV failed: {proc.stderr}", "pdf_base64": None}

            # Determine expected output file name from YAML
            try:
                data = yaml.safe_load(yaml_code)
                name = data["cv"]["name"]
                pdf_filename = name.replace(" ", "_") + "_CV.pdf"
                output_dir = "rendercv_output"
                pdf_path = os.path.join(output_dir, pdf_filename)
            except Exception:
                # Fallback: search for most recent PDF under rendercv_output
                output_dir = "rendercv_output"
                pdf_path = None
                if os.path.isdir(output_dir):
                    pdfs = [
                        os.path.join(output_dir, f)
                        for f in os.listdir(output_dir)
                        if f.lower().endswith(".pdf")
                    ]
                    if pdfs:
                        pdfs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                        pdf_path = pdfs[0]

            if not pdf_path or not os.path.exists(pdf_path):
                return {"text": f"Generated PDF not found in {output_dir}", "pdf_base64": None}

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return {"text": "Resume generated.", "pdf_base64": pdf_b64}
        finally:
            try:
                os.remove(yaml_path)
            except Exception:
                pass

