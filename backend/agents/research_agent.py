
# agents/research_agent.py
from agents import Agent, function_tool, WebSearchTool, Runner, SQLiteSession
from typing import Dict, Any, List
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from dotenv import load_dotenv
import json, uuid

load_dotenv()


research_agent = Agent(
    name="Research_Assistant",
    model="o4-mini-deep-research",
    tools=[],
    instructions="""
    You are a Deep Research agent.

    WORKFLOW
    1) Interpret the user's query (and optional focus area).
    2) Use your built-in browsing & analysis to gather facts, stats, and differing viewpoints from reputable, recent sources.
    3) Build a list named `findings` with dicts:
    - title (string)
    - url (string)
    - snippet (1–3 sentence extract/summary)
    4) Call summarize_research(findings=findings, query="<query>", focus_area="<focus>") EXACTLY ONCE.
    That tool returns the FINAL JSON payload. After calling it, STOP.

    CONSTRAINTS
    - No meta-instructions (e.g., “Please conduct research…”).
    - Prefer authoritative and recent sources when recency matters.
    - Keep the synthesis concise, neutral, and evidence-based.
    """
)



# -------------------------------
# Orchestrator-callable wrapper
# -------------------------------
@function_tool(name_override="run_research")
async def run_research(query: str, focus_area: str = "", max_steps: int = 20) -> str:
    """
    Runs the Deep Research agent and returns the final JSON string
    produced by summarize_research.
    """
    session = SQLiteSession(f"research_session_{uuid.uuid4().hex}")
    task = f"User query: {query}\nFocus area: {focus_area or '(general)'}"

    # Deep Research can plan and browse on its own; we just cap steps.
    result = await Runner.run(
        research_agent,
        task,
        session=session
    )

    out = (result.final_output or "").strip()
    try:
        json.loads(out)  # ensure JSON
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