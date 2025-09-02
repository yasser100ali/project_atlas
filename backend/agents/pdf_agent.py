# agents/pdf_agent.py
from agents import Agent, function_tool, Runner, SQLiteSession
from typing import Dict, Any, List
from dotenv import load_dotenv
import json, re, uuid

load_dotenv()

# Define the agent first (tools attached after the function tool is defined)
pdf_agent = Agent(
    name="PDF_Analyzer",
    model="gpt-4.1",
    tools=[],  # attach later per request
    instructions="""
You are a specialized PDF analysis agent.

WORKFLOW
1) Read the provided PDF text (already extracted) and the user's query.
2) Identify the most relevant sentences and core facts that answer the query.
3) Call analyze_pdf_content(pdf_text=<full_text>, user_query="<query>") EXACTLY ONCE.
   This is the FINAL step; the tool returns the final JSON payload.

CONSTRAINTS
- Do not echo the entire PDF. Use short quotes only when necessary.
- Avoid meta-instructions. After calling the tool, do not send further messages.
- If information is not present, say so explicitly in the final JSON and avoid hallucinating.
"""
)

# -------------------------
# Tools (defined below agent)
# -------------------------

@function_tool
def analyze_pdf_content(pdf_text: str, user_query: str) -> str:
    """
    TERMINAL step: deterministic summarization of PDF text relative to a query.
    Produces the final JSON payload expected by the caller.
    """
    # naive keyword extraction from the query
    q = (user_query or "").lower()
    tokens = re.findall(r"[a-zA-Z0-9]+", q)
    keywords = {t for t in tokens if len(t) >= 3}

    # split into rough sentences
    text = (pdf_text or "")
    content_len = len(text)
    raw_sents = re.split(r"(?<=[.!?])\s+", text.strip())
    sents = [s.strip() for s in raw_sents if s.strip()]

    # score sentences by keyword hits
    scored: List[tuple[int, str]] = []
    for s in sents:
        low = s.lower()
        score = sum(1 for k in keywords if k in low)
        if score > 0 or not keywords:
            scored.append((score, s))

    # choose top sentences; if no keywords, fall back to first few
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    top = [s for _, s in (scored[:8] if scored else sents[:6])]

    # helpers
    def tcut(s: str, n=240):
        return (s[:n] + "…") if len(s) > n else s

    key_points = [tcut(s) for s in top[:8]]
    evidence = key_points[:]

    # short answer (4–8 sentences)
    answer = " ".join([tcut(s, 300).rstrip() for s in top[:6]])
    if not answer:
        answer = "The provided PDF text contains insufficient information to answer the query."

    confidence = "high" if scored and scored[0][0] >= 2 else ("medium" if scored else "low")

    result = {
        "success": True if key_points else False,
        "query": user_query,
        "content_length": content_len,
        "answer": answer[:1500],
        "key_points": key_points,
        "evidence": evidence,
        "confidence": confidence,
        "status": "final"
    }

    return json.dumps(result)

# Attach tool after definition (per your request that the @function_tool be below the agent)
pdf_agent.tools = [analyze_pdf_content]

@function_tool(name_override="run_pdf_analysis")
async def run_pdf_analysis(pdf_text: str, query: str) -> str:
    """
    Runs PDF_Analyzer: the agent will call analyze_pdf_content exactly once and stop.
    Returns the final JSON string produced by the tool.
    """
    session = SQLiteSession(f"pdf_session_{uuid.uuid4().hex}")
    # Safety cap to prevent huge prompts; the tool also avoids echoing everything back.
    task = f"User query: {query}\nPDF text follows:\n\n{(pdf_text or '')[:200000]}"

    result = await Runner.run(
        pdf_agent,
        task,
        session=session
    )

    out = (result.final_output or "").strip()
    try:
        json.loads(out)  # ensure it's JSON
        return out
    except Exception:
        # Wrap any non-JSON into a valid payload so callers always get JSON
        return json.dumps({
            "success": False,
            "query": query,
            "content_length": len(pdf_text or ""),
            "answer": out[:1500],
            "key_points": [],
            "evidence": [],
            "confidence": "low",
            "status": "final"
        })