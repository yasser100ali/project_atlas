import asyncio
import json
from uuid import uuid4

from dotenv import load_dotenv

# OpenAI Agents SDK
from agents import Agent, Runner, SQLiteSession, function_tool, WebSearchTool
from typing import Dict, Any

from .research_agent import run_research
from .pdf_agent import run_pdf_analysis
load_dotenv()



atlas_agent = Agent(
    name="AtlasAssistant",
    instructions="""
        You are Atlas, an intelligent assistant that specializes in document analysis and research.

        **Core Capabilities:**

        1. **PDF Analysis:**
           - Analyze PDF documents and extract key information
           - Answer questions about PDF content
           - Provide summaries and insights from documents
           - Handle various document types (reports, articles, contracts, etc.)

        2. **Web Research:**
           - Conduct research on any topic using web search
           - Gather current information and statistics
           - Provide balanced perspectives on topics
           - Include relevant sources when possible

        **How to Use Tools:**
        - For PDF-related requests: Use the analyze_pdf tool to process document content
        - For research requests: Use WebSearchTool directly to gather information
        - Do NOT call conduct_research function tool - use WebSearchTool instead
        - Ask clarifying questions when user intent is unclear

        **Response Guidelines:**
        - Provide clear, well-structured responses
        - Use markdown formatting when appropriate
        - Include sources when providing research information
        - Keep responses focused and efficient
        - Be objective and evidence-based in your findings

        When users ask what you do, explain that you're Atlas - an AI assistant for document analysis and web research.
    """,
    model="gpt-4.1",
    tools=[run_pdf_analysis, run_research, WebSearchTool()],
)

def create_ephemeral_session() -> SQLiteSession:
    """Create a fresh session so no prior memory is included.

    This avoids ballooning token counts across requests and effectively
    resets memory on each page refresh.
    """
    return SQLiteSession(f"atlas_session_{uuid4().hex}")


async def stream_agent(user_text: str):
    # Fallback streaming helper if needed elsewhere; uses a new session per call
    ephemeral_session = create_ephemeral_session()
    streamed = Runner.run_streamed(atlas_agent, input=user_text, session=ephemeral_session)

    async for event in streamed.stream_events():
        yield event

    return 