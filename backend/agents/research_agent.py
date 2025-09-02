from agents import Agent, function_tool, WebSearchTool
from typing import Dict, Any, List
import json

@function_tool
def conduct_research(query: str, research_type: str = "general") -> Dict[str, Any]:
    """
    Conducts web research based on the user's query.

    Args:
        query: The research question or topic to investigate
        research_type: Type of research (general, career, financial, technical, etc.)

    Returns:
        Dict containing research results and findings
    """
    # This function serves as a trigger for the research agent to use WebSearchTool
    # The actual research will be performed by the agent's WebSearchTool
    return {
        "research_type": research_type,
        "query": query,
        "status": "research_initiated",
        "message": f"Starting {research_type} research on: {query}",
        "findings": []
    }

@function_tool
def summarize_research(findings: List[Dict[str, Any]], focus_area: str = "") -> Dict[str, Any]:
    """
    Summarizes research findings into key insights.

    Args:
        findings: List of research results to summarize
        focus_area: Specific area to focus the summary on

    Returns:
        Dict containing summarized research insights
    """
    return {
        "summary_type": "research_summary",
        "focus_area": focus_area,
        "key_insights": [],
        "status": "summarized"
    }

research_agent = Agent(
    name="Research_Assistant",
    instructions="""
    You are a specialized research agent. Your role is to:

    1. Conduct thorough web research on topics requested by users
    2. Gather information from reliable sources using WebSearchTool
    3. Provide comprehensive yet concise research summaries
    4. Help users understand complex topics through research

    Research capabilities:
    - Career research: job markets, salary data, industry trends
    - Financial research: investment options, market analysis, economic trends
    - Technical research: programming, tools, technologies
    - General research: any topic requiring web-based information gathering

    IMPORTANT: When you receive a request to conduct research:
    1. Always use the WebSearchTool to gather current information from the web
    2. Search for the specific topic requested
    3. Gather information from multiple reliable sources
    4. Provide balanced perspectives on controversial topics
    5. Include relevant statistics and data points when available
    6. Structure your response clearly with headings and bullet points
    7. Cite sources when possible
    8. Be objective and evidence-based in your findings
    9. Keep responses focused and comprehensive but not overwhelming

    Do NOT just call conduct_research tool - use WebSearchTool directly to gather information.
    Only use conduct_research when you need to trigger a research workflow.
    Always perform actual web searches using WebSearchTool for any research request.
    """,
    tools=[conduct_research, summarize_research, WebSearchTool()],
    model="gpt-4.1"
)
