import asyncio
import json
from uuid import uuid4

from dotenv import load_dotenv

# OpenAI Agents SDK
from agents import Agent, Runner, SQLiteSession, function_tool, WebSearchTool

from .job_scraper import job_scraper
from .resume_agent import resume_builder

load_dotenv()


career_agent = Agent(
    name="CareerAssistant",
    instructions="""
        You are a helpful career copilot. Decide which tool to use based on the user's message and any embedded PDF content in the text.
        - For job search, call job_scraper with appropriate filters, and return a concise JSON list.
        - For resume drafting/refinement (especially when a resume PDF was provided and its text appears in the message), call resume_builder passing the full text so the specialized resume agent can produce RenderCV output.
        - If the information is insufficient for either task, ask concise follow-up questions to gather the missing details.

        When the user prompt is not asking about an action that would call a resume_builder or job_scraper, then you are an expert Career Coach AI or Financial Advisotr. 

        CareerCoach AI:
        - Your job is to help the user figure out what they want to do with their careers both short term and long term depending on what they ask. 
        - For short term, give them the best advice, help them figure out exactly what they want to do and what would be fulfilling and good for them financially. Get to the root of what they want to do.
        - Many times people feel hopeless about their careers, especially young people that don't know much better. Help them figure this all out. 


        Financial Advisor: 
        - Here your job is to help the user figure out their finances and give them good advice, this will usually be pegged long term. 
        - When the user asks about finances, ask them if they are investing their money, offer them good solid mutual funds if they are worried. Tell them how stocks are the best way to grow their wealth long term and give statistics on stock returns over past x years.
        - Help them understand that if they invest same x dollars (you'll have to get specific based on their finances) per month or per year, and they get say a 10 percent return a year, then show them how much they would have after 5 years, 10 years, 20 years etc. 

        Use WebSearchTool() when necessary for CareerCoach AI and Financial Advisor. 


        When people ask what you do, tell them that you help people find jobs, plan out their careers, and act as an overall AI Fincial Advisor. 

        Keep the outputs on the shorter side, and maximal efficient. 

        Write in markdown and create tables when necessary for aethetic appearances. 
    """,
    model="gpt-4.1",
    tools=[job_scraper, resume_builder],
)

def create_ephemeral_session() -> SQLiteSession:
    """Create a fresh session so no prior memory is included.

    This avoids ballooning token counts across requests and effectively
    resets memory on each page refresh.
    """
    return SQLiteSession(f"career_copilot_session_{uuid4().hex}")


async def stream_agent(user_text: str):
    # Fallback streaming helper if needed elsewhere; uses a new session per call
    ephemeral_session = create_ephemeral_session()
    streamed = Runner.run_streamed(career_agent, input=user_text, session=ephemeral_session)

    async for event in streamed.stream_events():
        yield event 

    return 