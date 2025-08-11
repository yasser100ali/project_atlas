import asyncio
import json
from typing import Optional, List, Literal, Dict, Any

from dotenv import load_dotenv

# OpenAI Agents SDK
from agents import Agent, Runner, SQLiteSession, function_tool  # type: ignore

# Local utilities
from ..utils.tools import search_jobs

load_dotenv()


@function_tool(name_override="job_scraper")
async def job_scraper(
    query: str,
    location: str = "San Francisco, California, United States",
    pages: int = 1,
    date_posted: Optional[str] = None,
    remote_only: bool = False,
    employment_types: Optional[List[str]] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    salary_currency: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    top_k: int = 10,
) -> str:
    """Search for jobs using JSearch with optional filters. Return a JSON string list of jobs."""
    jobs = search_jobs(
        query=query,
        location=location,
        pages=pages,
        date_posted=date_posted,
        remote_only=remote_only,
        employment_types=employment_types,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        extra=extra,
    ) or []
    return json.dumps(jobs[: max(1, top_k)])


@function_tool(name_override="resume_generator")
def resume_generator(
    profile: Dict[str, Any],
    template: Optional[str] = None,
    job_desc: Optional[str] = None,
) -> str:
    """Generate a tailored resume (simple JSON). This is a lightweight placeholder.
    Provide a profile dict with keys like name, skills, experience. Optionally include job_desc.
    Returns a JSON string with a 'text' field containing a simple Markdown resume.
    """
    name = profile.get("name", "Candidate")
    skills = ", ".join(profile.get("skills", [])) if isinstance(profile.get("skills"), list) else str(profile.get("skills", ""))
    summary = profile.get("summary", "")
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
    result = await Runner.run(
        career_agent,
        user_text,
        session=session,
        # Use default model; can set via env if needed
        run_config=None,
    )
    return result.final_output
