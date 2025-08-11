
from typing import Type, Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json
from agents import function_tool  # type: ignore
from ..utils.tools.search_job import search_jobs


class JobScraperInput(BaseModel):
    query: str = Field(description="Job title or keywords to search for.")
    location: str = Field(
        default="San Francisco, California, United States",
        description="Location query (city, state, country)."
    )
    pages: int = Field(default=1, ge=1, description="How many pages to fetch from the API.")
    date_posted: Optional[str] = Field(
        default=None,
        description="Filter by recency: 'today'|'3days'|'week'|'month'|'all'."
    )
    remote_only: bool = Field(default=False, description="Return only remote jobs if True.")
    employment_types: Optional[List[str]] = Field(
        default=None,
        description="Subset of ['FULLTIME','PARTTIME','CONTRACTOR','INTERN']."
    )
    salary_min: Optional[float] = Field(default=None, description="Minimum annual salary to include.")
    salary_max: Optional[float] = Field(default=None, description="Maximum annual salary to include.")
    salary_currency: Optional[str] = Field(default=None, description="Expected currency code, e.g. 'USD'.")
    extra: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pass-through for additional API params supported by JSearch."
    )
    top_k: int = Field(default=10, ge=1, description="Limit the number of returned jobs.")


@function_tool(name_override="job_scraper")
async def job_scraper(
    query: str,
    location: str = "San Francisco, California, United States",
    pages: int = 1,
    date_posted: Optional[str] = None,
    remote_only: bool = False,
    employment_types: Optional[List[str]] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    salary_currency: Optional[str] = None,
    top_k: int = 10,
) -> str:
    """Search for jobs using JSearch with optional filters. Return a JSON string list of jobs."""
    jobs = search_jobs(
        query=query,
        location=location,
        pages=pages,
        date_posted=date_posted,
        remote_only=remote_only,
        employment_types=employment_types,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        extra=None,
    ) or []
    return json.dumps(jobs[: max(1, top_k)])
