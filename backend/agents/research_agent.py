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
    # This function will be enhanced to actually perform research
    return {
        "research_type": research_type,
        "query": query,
        "status": "research_completed",
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
    2. Gather information from reliable sources
    3. Provide comprehensive yet concise research summaries
    4. Help users understand complex topics through research

    Research capabilities:
    - Career research: job markets, salary data, industry trends
    - Financial research: investment options, market analysis, economic trends
    - Technical research: programming, tools, technologies
    - General research: any topic requiring web-based information gathering

    When conducting research:
    - Use WebSearchTool for finding current and reliable information
    - Verify information from multiple sources when possible
    - Provide balanced perspectives on controversial topics
    - Include relevant statistics and data points
    - Cite sources when possible
    - Structure information clearly with headings and bullet points
    - Be objective and evidence-based in your findings

    Use the conduct_research tool to gather information and summarize_research to organize findings.
    """,
    tools=[conduct_research, summarize_research, WebSearchTool()]
)
