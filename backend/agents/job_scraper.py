from langchain.tools import BaseTool
from typing import Type, Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json
from ..utils.tools import search_jobs


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


class JobScraper(BaseTool):
    name = "job_scraper"
    description = (
        "Search for jobs using JSearch with optional filters like location, date_posted, "
        "employment type, remote-only, and salary range. Returns a JSON list of jobs."
    )
    args_schema: Type[BaseModel] = JobScraperInput

    def _run(
        self,
        query: str,
        location: str = "San Francisco, California, United States",
        pages: int = 1,
        *,
        date_posted: Optional[str] = None,
        remote_only: bool = False,
        employment_types: Optional[List[str]] = None,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        salary_currency: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
    ) -> str:
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
            extra=extra,
        )

        if not jobs:
            return json.dumps([])

        # Limit to top_k and return as JSON string for the agent to consume/display
        limited = jobs[: max(1, top_k)]
        return json.dumps(limited)

    async def _arun(
        self,
        query: str,
        location: str = "San Francisco, California, United States",
        pages: int = 1,
        *,
        date_posted: Optional[str] = None,
        remote_only: bool = False,
        employment_types: Optional[List[str]] = None,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        salary_currency: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
    ) -> str:
        return self._run(
            query=query,
            location=location,
            pages=pages,
            date_posted=date_posted,
            remote_only=remote_only,
            employment_types=employment_types,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            extra=extra,
            top_k=top_k,
        )
