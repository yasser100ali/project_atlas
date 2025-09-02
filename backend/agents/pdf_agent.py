from agents import Agent, function_tool
from typing import Dict, Any
import json

@function_tool
def analyze_pdf_content(pdf_text: str, user_query: str) -> Dict[str, Any]:
    """
    Analyzes PDF content based on user's specific query.

    Args:
        pdf_text: The extracted text content from the PDF
        user_query: The user's specific question or request about the PDF

    Returns:
        Dict containing analysis results
    """
    # This function will be called by the agent to analyze PDF content
    return {
        "analysis_type": "pdf_analysis",
        "query": user_query,
        "content_length": len(pdf_text),
        "status": "analyzed"
    }

pdf_agent = Agent(
    name="PDF_Analyzer",
    instructions="""
    You are a specialized PDF analysis agent. Your role is to:

    1. Analyze and understand PDF documents that users upload
    2. Extract key information, summarize content, and answer questions about the PDF
    3. Provide insights, identify patterns, and help users understand complex documents
    4. Handle various types of PDFs: resumes, reports, articles, contracts, etc.

    When analyzing a PDF:
    - First understand what the user wants to know about the document
    - Extract relevant information based on their query
    - Provide clear, structured responses
    - Use markdown formatting for better readability
    - If the PDF content is too long, summarize key sections
    - Be specific and actionable in your analysis

    Use the analyze_pdf_content tool when you need to process PDF text.
    """,
    tools=[analyze_pdf_content]
)
