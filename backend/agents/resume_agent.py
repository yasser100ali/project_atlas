# agents/resume_agent.py
import json
from agents import Agent, ModelSettings, Runner, SQLiteSession, function_tool
from ..utils.tools.resume_generation import rendercv_render  # your @function_tool from earlier
from dotenv import load_dotenv

load_dotenv()

# Global variable to store successful response with base64 data
successful_response_with_base64 = ""

def get_successful_response_with_base64():
    """Get the successful response with base64 data for frontend processing"""
    global successful_response_with_base64
    return successful_response_with_base64

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
  - summary: a singular paragraph summarizing the candidate. 
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
      - "Data scientist specializing in ML systems and experiment design. I shipped models impacting revenue and latency at scale. I am seeking ML Engineer roles focused on applied modeling."
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


@function_tool(name_override="resume_builder")
async def resume_builder(input_text: str) -> str:
    """
    Run the resume agent with up to 3 attempts, repairing YAML based on RenderCV errors.
    Returns the final tool output from `rendercv_render` (JSON string).
    """
    session = SQLiteSession("career_copilot_session")
    max_attempts = 3
    last_output = ""
    error_feedback = ""
    # Global variable to store successful response with base64 data
    global successful_response_with_base64
    successful_response_with_base64 = ""

    for attempt in range(1, max_attempts + 1):
        augmented_input = input_text if not error_feedback else (
            f"{input_text}\n\nRENDER_ERROR_FEEDBACK:\n{error_feedback}\n"
            "Please correct the YAML according to the error feedback above and call the render tool again."
        )

        print(f"[resume_builder] Attempt {attempt} starting")

        # No streaming needed inside this subagent
        result = await Runner.run(
            resume_agent,
            augmented_input,
            session=session,
            run_config=None,
        )

        raw_output = result.final_output or ""
        print(f"[resume_builder] Attempt {attempt} tool output length={len(raw_output)}")

        # Store original response if it contains successful PDF data
        if len(raw_output) > 10000:  # If response is very large
            try:
                parsed = json.loads(raw_output)
                if (isinstance(parsed, dict) and
                    parsed.get('returncode') == 0 and
                    ('pdf_b64' in parsed or 'pdf_path' in parsed)):
                    print(f"[DEBUG] Storing original successful response with base64 data")
                    successful_response_with_base64 = raw_output
            except json.JSONDecodeError:
                pass

        # Use sanitized version for processing to avoid token limits
        last_output = raw_output
        if len(raw_output) > 10000:  # If response is very large
            try:
                parsed = json.loads(raw_output)
                if isinstance(parsed, dict) and 'pdf_b64' in parsed and len(parsed['pdf_b64']) > 1000:
                    print(f"[DEBUG] Using sanitized version for processing: {len(parsed['pdf_b64'])} chars")
                    parsed['pdf_b64'] = f"<base64_data_sanitized_length_{len(parsed['pdf_b64'])}>"
                    last_output = json.dumps(parsed)
                    print(f"[DEBUG] Sanitized output length: {len(last_output)}")
            except json.JSONDecodeError:
                # If it's not JSON, check if it contains base64-like data
                if 'pdf_b64' in raw_output and len(raw_output) > 20000:
                    print("[DEBUG] Truncating non-JSON response with base64 data")
                    last_output = raw_output[:10000] + "...[truncated_base64_data]"

        # Parse tool output (rendercv_render returns JSON string)
        try:
            parsed = json.loads(last_output)
        except Exception:
            error_feedback = (
                "The previous output was not valid JSON from rendercv_render. "
                f"Raw output (truncated): {last_output[:2000]}"
            )
            print(f"[resume_builder] Attempt {attempt} JSON parse error")
            continue

        if not isinstance(parsed, dict):
            error_feedback = (
                "The previous output was not a JSON object. "
                f"Raw output (truncated): {last_output[:2000]}"
            )
            print(f"[resume_builder] Attempt {attempt} non-dict tool result")
            continue

        returncode = parsed.get("returncode")
        pdf_b64 = parsed.get("pdf_b64") or ""
        pdf_path = parsed.get("pdf_path")
        stderr = parsed.get("stderr") or ""
        stdout = parsed.get("stdout") or ""

        if returncode == 0 and (pdf_path or len(pdf_b64) > 0):
            print(f"[resume_builder] Attempt {attempt} success -> pdf_path={pdf_path}, has_b64={bool(pdf_b64)}")
            # Store the original successful response for returning to frontend
            successful_response_with_base64 = raw_output
            # Return a clean success message to the LLM (no base64 data)
            return json.dumps({
                "success": True,
                "message": "Resume PDF generated successfully",
                "filename": expected_filename,
                "has_base64": len(pdf_b64) > 0
            })

        # Create error feedback without the massive base64 data
        error_feedback_parts = [f"Render failed (returncode={returncode})."]

        if stderr and len(stderr) > 0:
            # Truncate stderr but avoid including base64 data
            clean_stderr = stderr[:2000]
            if 'pdf_b64' in clean_stderr:
                clean_stderr = clean_stderr.split('pdf_b64')[0] + '...[base64_data_truncated]'
            error_feedback_parts.append(f"stderr (truncated): {clean_stderr}")

        if stdout and len(stdout) > 0:
            # Truncate stdout but avoid including base64 data
            clean_stdout = stdout[:2000]
            if 'pdf_b64' in clean_stdout or len(clean_stdout) > 10000:
                clean_stdout = '...[output_truncated_to_avoid_token_limit]'
            error_feedback_parts.append(f"stdout (truncated): {clean_stdout}")

        error_feedback = "\n".join(error_feedback_parts)
        print(f"[resume_builder] Attempt {attempt} failed: returncode={returncode}")

    # After retries, return a clean success message if we had success, otherwise the last output
    if successful_response_with_base64:
        print(f"[DEBUG] Returning clean success message (base64 data preserved in global)")
        # Extract filename from the original response for the success message
        try:
            parsed = json.loads(successful_response_with_base64)
            filename = parsed.get("filename", "resume.pdf")
            return json.dumps({
                "success": True,
                "message": "Resume PDF generated successfully",
                "filename": filename,
                "has_base64": True
            })
        except:
            return json.dumps({
                "success": True,
                "message": "Resume PDF generated successfully",
                "filename": "resume.pdf",
                "has_base64": True
            })

    print(f"[DEBUG] Returning last output (no successful render)")
    return last_output