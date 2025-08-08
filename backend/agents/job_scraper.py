from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from jobspy import scrape_jobs

class JobScraperInput(BaseModel):
    query: str = Field(description="The job title or keywords to search for.")

class JobScraper(BaseTool):
    name = "job_scraper"
    description = "A tool for scraping jobs from the internet."
    args_schema: Type[BaseModel] = JobScraperInput

    def _run(self, query: str):
        # Call the scrape_jobs function with the provided query
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin"],
            search_term=query,
            results_wanted=5,
        )
        # We'll return the results as a string for now.
        # Later, we can format this more nicely.
        if jobs is not None and not jobs.empty:
            return jobs.to_string()
        return "No jobs found for the given query."

    async def _arun(self, query: str):
        # For simplicity, we'll just use the synchronous version for now.
        return self._run(query)
