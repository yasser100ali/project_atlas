import asyncio
import json

from dotenv import load_dotenv

# OpenAI Agents SDK
from agents import Agent, Runner, SQLiteSession, function_tool  # type: ignore

from .job_scraper import job_scraper
from .resume_agent import resume_agent, resume_builder, set_resume_events_handler

load_dotenv()


career_agent = Agent(
    name="CareerAssistant",
    instructions=(
        "You are a helpful career copilot. Decide which tool to use based on the user's message and any "
        "embedded PDF content in the text.\n"
        "- For job search, call job_scraper with appropriate filters, and return a concise JSON list.\n"
        "- For resume drafting/refinement (especially when a resume PDF was provided and its text appears in the "
        "message), call resume_builder passing the full text so the specialized resume agent can produce RenderCV output.\n"
        "- If the information is insufficient for either task, ask concise follow-up questions to gather the missing details.\n"
        "If providing a final answer, begin with 'Final Answer:' before the user-facing summary."
    ),
    model="gpt-4.1",
    tools=[job_scraper, resume_builder],
)

session = SQLiteSession("career_copilot_session")


async def handle_user_message(user_text: str, on_event=None) -> str:
    print(f"[orchestrator] Running career agent with user_text length={len(user_text)}")

    async def handler(event_type, data):
        if on_event is not None:
            try:
                await on_event(event_type, data)
            except Exception:
                pass

    # Register streaming handler for resume agent phases
    set_resume_events_handler(handler)
    try:
        result = await Runner.run(
            career_agent,
            user_text,
            session=session,
            run_config=None,
        )
    finally:
        # Ensure handler is cleared
        set_resume_events_handler(None)

    return result.final_output
