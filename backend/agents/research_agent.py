
# agents/research_agent.py
from agents import Agent, function_tool, WebSearchTool, Runner, SQLiteSession
from typing import Dict, Any, List
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from dotenv import load_dotenv
import json, uuid

load_dotenv()

def _normalize_url(u: str) -> str:
    try:
        p = urlparse(u)
        # strip tracking params
        qs = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
              if k.lower() not in {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid"}]
        return urlunparse((p.scheme, p.netloc, p.path, "", urlencode(qs), ""))
    except Exception:
        return u

@function_tool
def summarize_research(
    findings: str,  # Changed from List[Dict[str, Any]] to str for JSON compatibility
    query: str,
    focus_area: str = "",
    max_sources: int = 8,
    max_bullets: int = 8,
    max_snippet_chars: int = 240
) -> str:  # Changed return type to str for JSON compatibility
    """
    TERMINAL step: normalize & compress findings and return the final JSON.
    """
    # Parse JSON string to list of dicts
    try:
        findings = json.loads(findings) if isinstance(findings, str) else findings
    except json.JSONDecodeError:
        findings = []

    if not isinstance(findings, list):
        findings = []

    # Dedupe by normalized URL then by title
    seen_urls, seen_titles, cleaned = set(), set(), []
    for f in findings:
        title = (f.get("title") or "").strip() or (f.get("url") or "Source")
        url = _normalize_url((f.get("url") or "").strip())
        snippet = (f.get("snippet") or f.get("summary") or "").strip()

        key_url = url.lower()
        key_title = title.lower()

        if key_url and key_url in seen_urls: 
            continue
        if key_title in seen_titles:
            continue

        seen_urls.add(key_url)
        seen_titles.add(key_title)

        cleaned.append({
            "title": title[:200],
            "url": url,
            "snippet": snippet[:max_snippet_chars]
        })
        if len(cleaned) >= max_sources:
            break

    # Key insights: short bullets from snippets/titles
    bullets: List[str] = []
    for c in cleaned[:max_bullets]:
        base = c["snippet"] or c["title"]
        bullets.append(base.strip())

    # Compose a short final answer (4–8 sentences max-ish)
    lines = []
    if focus_area:
        lines.append(f"Focus: {focus_area}.")
    # Use up to ~5 bullets to craft succinct sentences
    for b in bullets[:5]:
        # ensure each bullet is a sentence-like chunk
        s = b.rstrip(".;:")
        lines.append(s + ".")

    answer = " ".join(lines)[:1500]

    result = {
        "success": True,
        "query": query,
        "focus_area": focus_area,
        "answer": answer,
        "key_insights": bullets,
        "sources": [{"title": c["title"], "url": c["url"]} for c in cleaned],
        "status": "final"
    }

    return json.dumps(result)

research_agent = Agent(
    name="Research_Assistant",
    model="gpt-4.1",
    tools=[WebSearchTool(), summarize_research],
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
