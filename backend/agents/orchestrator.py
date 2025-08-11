import asyncio
import json
from typing import Optional, List
from pydantic import BaseModel

from dotenv import load_dotenv

# OpenAI Agents SDK
from agents import Agent, Runner, SQLiteSession, function_tool  # type: ignore

from .job_scraper import job_scraper

load_dotenv()


# `job_scraper` tool is imported from `.job_scraper`


class ResumeProfile(BaseModel):
    name: Optional[str] = None
    skills: Optional[List[str]] = None
    summary: Optional[str] = None


@function_tool(name_override="resume_generator")
def resume_generator(
    profile: ResumeProfile,
    template: Optional[str] = None,
    job_desc: Optional[str] = None,
) -> str:
    """Generate a tailored resume (simple JSON). This is a lightweight placeholder.
    Provide a profile dict with keys like name, skills, experience. Optionally include job_desc.
    Returns a JSON string with a 'text' field containing a simple Markdown resume.
    """
    name = profile.name or "Candidate"
    skills = ", ".join(profile.skills) if isinstance(profile.skills, list) else ""
    summary = profile.summary or ""
    md = f"# {name}\n\n## Summary\n{summary}\n\n## Skills\n{skills}\n\n"
    return json.dumps({"text": md})


career_agent = Agent(
    name="CareerAssistant",
    instructions=(
        "You are a helpful career copilot. When the user asks for jobs, call job_scraper with appropriate "
        "filters. When the user wants a resume, call resume_generator. Prefer concise JSON for structured "
        "lists (e.g., jobs). If providing a final answer, begin with 'Final Answer:' before the user-facing summary."
    ),
    tools=[job_scraper, resume_generator],
)

session = SQLiteSession("career_copilot_session")


async def handle_user_message(user_text: str) -> str:
    print(f"[orchestrator] Running agent with user_text: {user_text}")
    result = await Runner.run(
        career_agent,
        user_text,
        session=session,
        # Use default model; can set via env if needed
        run_config=None,
    )
    print("[orchestrator] Agent final_output:\n" + str(result.final_output))
    return result.final_output
