
# agents/research_agent.py
from agents import Agent, function_tool, WebSearchTool, Runner, SQLiteSession
from typing import Dict, Any, List
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from dotenv import load_dotenv
import json, uuid

load_dotenv()


research_agent = Agent(
    name="Research_Assistant",
    model="gpt-4.1",
    tools=[WebSearchTool()],
    instructions="""
    You are a research agent.

    WORKFLOW
    1) Use WebSearchTool to gather 5–12 relevant, reputable, and recent items for the user's topic.
    2) Build a Python list named `findings` where each item is a dict with keys:
    - title (string)
    - url (string)
    - snippet (short 1–3 sentence summary)
    3) Call summarize_research(findings=json.dumps(findings), query="<original query>", focus_area="<if any>")
    EXACTLY ONCE. This is your FINAL step.

    CONSTRAINTS
    - Do not echo or create meta-instructions like “Please conduct research…”.
    - After calling summarize_research, DO NOT send any more messages or call any more tools.
    - Keep the answer neutral, concise, and evidence-based.
    - Prefer sources with clear authority; include a mix if viewpoints differ.

    OUTPUT
    - The tool result from summarize_research is the final JSON payload for the caller.
    """
)

# Optional: a convenience tool callable by an orchestrator, similar to your resume_builder
@function_tool(name_override="run_research")
async def run_research(query: str, focus_area: str = "", max_steps: int = 8) -> str:
    """
    Runs the research workflow and returns the final JSON string produced by summarize_research.
    """
    session = SQLiteSession(f"research_session_{uuid.uuid4().hex}")
    task = f"User query: {query}\nFocus area: {focus_area or '(general)'}"

    result = await Runner.run(
        research_agent,
        task,
        session=session
    )

    out = (result.final_output or "").strip()
    # Ensure we always return JSON
    try:
        json.loads(out)
        return out
    except Exception:
        return json.dumps({
            "success": False,
            "query": query,
            "focus_area": focus_area,
            "answer": out[:1500],
            "key_insights": [],
            "sources": [],
            "status": "final"
        })
