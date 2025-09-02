import asyncio
import json
from uuid import uuid4

from dotenv import load_dotenv

# OpenAI Agents SDK
from agents import Agent, Runner, SQLiteSession, function_tool, WebSearchTool
from typing import Dict, Any

load_dotenv()

@function_tool
def analyze_pdf(pdf_text: str, query: str) -> Dict[str, Any]:
    """
    Analyze PDF content based on user's query.

    Args:
        pdf_text: The extracted text from the PDF
        query: User's specific question about the PDF

    Returns:
        Analysis results
    """
    return {
        "tool": "pdf_analyzer",
        "pdf_length": len(pdf_text),
        "query": query,
        "analysis": "PDF analysis would be performed here"
    }

@function_tool
async def conduct_research(query: str, research_type: str = "general") -> Dict[str, Any]:
    """
    Conduct research on a given topic.

    Args:
        query: The research question or topic
        research_type: Type of research needed

    Returns:
        Research results
    """
    # Import the research agent here to avoid circular imports
    from .research_agent import research_agent, conduct_research as research_conduct_research

    # Actually perform research using the research agent
    try:
        # Create a session for the research
        research_session = create_ephemeral_session()

        # Run the research agent
        research_input = f"Conduct {research_type} research on: {query}"
        result = await Runner.run(research_agent, input=research_input, session=research_session)

        # Extract the final response
        if hasattr(result, 'final_output') and result.final_output:
            return {
                "tool": "research_conductor",
                "query": query,
                "research_type": research_type,
                "findings": result.final_output,
                "status": "completed"
            }
        else:
            return {
                "tool": "research_conductor",
                "query": query,
                "research_type": research_type,
                "findings": "Research completed but no specific findings extracted",
                "status": "completed"
            }
    except Exception as e:
        return {
            "tool": "research_conductor",
            "query": query,
            "research_type": research_type,
            "findings": f"Research failed: {str(e)}",
            "status": "error"
        }


atlas_agent = Agent(
    name="AtlasAssistant",
    instructions="""
        You are Atlas, an intelligent assistant that specializes in document analysis, research, and career/financial guidance.

        **Agent Selection Guidelines:**

        1. **Use PDF Agent when:**
           - User uploads or mentions analyzing a PDF document
           - User wants to extract information from a document
           - User asks questions about PDF content (resumes, reports, articles, contracts)
           - User wants summaries, insights, or analysis of document content

        2. **Use Research Agent when:**
           - User asks to research a topic, company, or industry
           - User needs information gathering from the web
           - User wants market research, salary data, or industry trends
           - User asks for current information or statistics

        3. **Handle as Career Coach when:**
           - User asks about career planning, job search strategies
           - User needs help figuring out career goals (short-term and long-term)
           - User feels lost about their career direction
           - User wants advice on career transitions or skill development

        4. **Handle as Financial Advisor when:**
           - User asks about investments, savings, or financial planning
           - User wants advice on mutual funds, stocks, or retirement planning
           - User needs help understanding compound interest or investment returns
           - User asks about long-term wealth building strategies

        **Key Behaviors:**
        - Detect PDF content in user messages and automatically engage PDF analysis
        - Use WebSearchTool when research or current information is needed
        - Ask clarifying questions when user intent is unclear
        - Provide concise, actionable advice
        - Use markdown formatting and tables for clarity
        - Keep responses focused and efficient

        When users ask what you do, explain that you're Atlas - an AI assistant for document analysis, research, career planning, and financial guidance.
    """,
    model="gpt-4.1",
    tools=[analyze_pdf, conduct_research, WebSearchTool()],
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
    streamed = Runner.run_streamed(atlas_agent, input=user_text, session=ephemeral_session)

    async for event in streamed.stream_events():
        yield event

    return 