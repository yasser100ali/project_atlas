# agents/resume_agent.py
import json
import asyncio
from typing import Optional, Awaitable, Callable, Dict, Any
from agents import Agent, ModelSettings, Runner, SQLiteSession, function_tool
from ..utils.tools.resume_generation import rendercv_render  # your @function_tool from earlier
from dotenv import load_dotenv

load_dotenv()

resume_agent = Agent(
    name="ResumeAgent",
    model="gpt-4.1",
    tools=[rendercv_render],
    tool_use_behavior="stop_on_first_tool",
    instructions="""
You are an expert resume creator using RenderCV.

CONTRACT
- Convert the provided resume text (may include extracted PDF/JD text) into STRICT RenderCV YAML.
- Then call the tool `rendercv_render(yaml_str=<your YAML>)` to render a PDF.
- If rendering fails (non‑zero return code or validation errors in stderr/stdout), FIX the YAML using the error messages and RETRY.
- Iterate up to 3 total attempts (initial + 2 retries) until the tool returns a successful render.
- Do NOT add prose or explanations. Do NOT wrap YAML in code fences. Tool input must be plain YAML.

YAML RULES (STRICT)
- Top-level keys ONLY: `cv` and `design`.
- Under `cv`, include: `name`, `email`, optional `phone` (valid intl format), `location`,
  optional `social_networks` (list of {network, username} ONLY), and `sections`.
- Dates: YYYY-MM; use `present` for ongoing.
- Sections shape:
  - summary/about: 3–5 concise bullet lines (TextEntry list).
  - experience: each entry must include {company, position, start_date, end_date, location, highlights[]} with 2–3 quantified bullets.
  - education: each entry must include {institution, area, study_type, start_date, end_date, location, highlights[]}.
  - projects: each entry must include {name, start_date, end_date, summary, highlights[]}.
  - skills: 4–6 OneLineEntry items {label, details}.
- Omit `languages` unless explicitly requested. Target ~1 page; trim redundancy.
- End with:
  design:
    theme: sb2nov

FORMAT EXAMPLE (FOLLOW THIS SHAPE):
cv:
  name: Jane Smith
  location: San Francisco, CA, USA
  email: jane.smith@example.com
  phone: +1 (415) 555-0199
  social_networks:
    - network: LinkedIn
      username: jane-smith
    - network: GitHub
      username: janesmith
  sections:
    summary:
      - "Data scientist specializing in ML systems and experiment design."
      - "Shipped models impacting revenue and latency at scale."
      - "Seeking ML Engineer roles focused on applied modeling."
    experience:
      - company: Acme AI
        position: Machine Learning Engineer
        start_date: 2023-04
        end_date: present
        location: San Francisco, CA
        highlights:
          - "Built XGBoost + SHAP pipeline; improved retention uplift by 6.8%."
          - "Productionized feature store features; cut training time by 40%."
    education:
      - institution: University of California, Santa Barbara
        area: Applied Mathematics
        study_type: B.S.
        start_date: 2019-09
        end_date: 2023-06
        location: Santa Barbara, CA
        highlights:
          - "Coursework: statistical learning, Bayesian methods, numerical analysis."
    projects:
      - name: X-Ray Anomaly Classifier
        start_date: 2024-02
        end_date: present
        summary: "DICOM → PNG pipeline; fine-tuned CNN for abnormality detection."
        highlights:
          - "Optimized image size & augmentation; robust 92.5% val accuracy."
    skills:
      - label: Programming
        details: "Python, R, SQL, Bash, Git"
      - label: ML/DS
        details: "XGBoost, CNNs, SHAP, scikit-learn, PyTorch"
      - label: Data
        details: "Pandas, Feature Stores, ETL"
      - label: MLOps
        details: "Experiment tracking, CI/CD"
design:
  theme: sb2nov

WORKFLOW
1) Read the input resume/JD text.
2) Produce VALID RenderCV YAML (no code fences).
3) Call tool `rendercv_render(yaml_str=<that YAML>)`.
4) If `returncode != 0` or stderr indicates validation errors, analyze the error, fix the YAML, and call the tool again (up to 2 retries).
5) When rendering succeeds, return the tool result as the final output.
"""
)


# Deterministic resume builder tool with retries, colocated with the resume agent
@function_tool(name_override="resume_builder")
async def resume_builder(input_text: str) -> str:
    """Run the resume agent with up to 3 attempts, repairing YAML based on RenderCV errors.

    Returns the final tool output from `rendercv_render` (JSON string).
    """
    session = SQLiteSession("career_copilot_session")
    max_attempts = 3
    last_output = ""
    error_feedback = ""

    for attempt in range(max_attempts):
        augmented_input = input_text
        if error_feedback:
            augmented_input = (
                f"{input_text}\n\nRENDER_ERROR_FEEDBACK:\n{error_feedback}\n"
                "Please correct the YAML according to the error feedback above and call the render tool again."
            )

        print(f"[resume_builder] Attempt {attempt + 1} starting")
        await _emit("attempt_start", {"attempt": attempt + 1})

        result = await Runner.run(
            resume_agent,
            augmented_input,
            session=session,
            run_config=None,
        )

        last_output = result.final_output
        print(f"[resume_builder] Attempt {attempt + 1} tool output length={len(str(last_output))}")

        # Parse the tool output from rendercv_render
        parsed = None
        try:
            parsed = json.loads(last_output)
        except Exception:
            error_feedback = (
                "The previous output was not valid JSON from rendercv_render. "
                f"Raw output (truncated): {last_output[:2000]}"
            )
            print(f"[resume_builder] Attempt {attempt + 1} JSON parse error")
            await _emit("attempt_fail", {"attempt": attempt + 1, "reason": "json_parse_error"})
            continue

        if not isinstance(parsed, dict):
            error_feedback = (
                "The previous output was not a JSON object. "
                f"Raw output (truncated): {last_output[:2000]}"
            )
            print(f"[resume_builder] Attempt {attempt + 1} non-dict tool result")
            await _emit("attempt_fail", {"attempt": attempt + 1, "reason": "non_dict"})
            continue

        returncode = parsed.get("returncode")
        pdf_b64 = parsed.get("pdf_b64") or ""
        pdf_path = parsed.get("pdf_path")
        stderr = parsed.get("stderr") or ""
        stdout = parsed.get("stdout") or ""

        if returncode == 0 and (pdf_path or len(pdf_b64) > 0):
            print(f"[resume_builder] Attempt {attempt + 1} success -> pdf_path={pdf_path}")
            await _emit("attempt_success", {"attempt": attempt + 1, "pdf_path": pdf_path, "has_pdf_b64": len(pdf_b64) > 0})
            return last_output

        error_feedback = (
            f"Render failed (returncode={returncode}).\n"
            f"stderr (truncated): {stderr[:2000]}\n"
            f"stdout (truncated): {stdout[:2000]}"
        )
        print(f"[resume_builder] Attempt {attempt + 1} failed: returncode={returncode}")
        await _emit("attempt_fail", {"attempt": attempt + 1, "returncode": returncode})

    return last_output

# --- Lightweight event plumbing for streaming ---
_resume_events_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None

def set_resume_events_handler(handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]]) -> None:
    global _resume_events_handler
    _resume_events_handler = handler

async def _emit(event_type: str, data: Dict[str, Any]) -> None:
    if _resume_events_handler is not None:
        try:
            await _resume_events_handler(event_type, data)
        except Exception:
            pass
