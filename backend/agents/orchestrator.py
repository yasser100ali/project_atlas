import asyncio
import json

from dotenv import load_dotenv

# OpenAI Agents SDK
from agents import Agent, Runner, SQLiteSession, function_tool  # type: ignore

from .job_scraper import job_scraper
from .resume_agent import resume_agent, resume_builder

load_dotenv()


career_agent = Agent(
    name="CareerAssistant",
    instructions="""
        You are a helpful career copilot. Decide which tool to use based on the user's message and any embedded PDF content in the text.
        - For job search, call job_scraper with appropriate filters, and return a concise JSON list.
        - For resume drafting/refinement (especially when a resume PDF was provided and its text appears in the message), call resume_builder passing the full text so the specialized resume agent can produce RenderCV output.
        - If the information is insufficient for either task, ask concise follow-up questions to gather the missing details.

        If providing a final answer, begin with 'Final Answer:' before the user-facing summary.

    """,
    model="gpt-4.1",
    tools=[job_scraper, resume_builder],
)

session = SQLiteSession("career_copilot_session")


async def stream_agent(user_text: str):
    streamed = Runner.run_streamed(career_agent, input=user_text, session=session)

    async for event in streamed.stream_events():
        yield event 

    return 