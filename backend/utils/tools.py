import os, requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List

load_dotenv(".env")


def _annualize(amount: Optional[float], period: Optional[str]) -> Optional[float]:
    """Convert salary to annual based on reported period."""
    if amount is None or not period:
        return amount
    p = period.upper()
    if p == "HOUR":   return amount * 2080     # 40h * 52w
    if p == "DAY":    return amount * 260      # 5d * 52w
    if p == "WEEK":   return amount * 52
    if p == "MONTH":  return amount * 12
    # YEAR or unknown -> assume already annual
    return amount

def search_jobs(
    query: str,
    location: str = "San Francisco, California, United States",
    pages: int = 1,
    *,
    date_posted: Optional[str] = None,          # 'today'|'3days'|'week'|'month'|'all'
    remote_only: bool = False,
    employment_types: Optional[list[str]] = None,  # ['FULLTIME','PARTTIME','CONTRACTOR','INTERN']
    salary_min: Optional[float] = None,         # annual USD (or your chosen currency)
    salary_max: Optional[float] = None,         # annual USD
    salary_currency: Optional[str] = None,      # e.g., 'USD'
    extra: Optional[Dict[str, Any]] = None,     # pass-through for any future params
) -> List[Dict[str, Any]]:
    """
    JSearch (RapidAPI) job search with optional salary filtering.
    Requires env RAPIDAPI_KEY.
    Notes:
      - JSearch returns salary fields when present on the listing:
        job_min_salary, job_max_salary, job_salary_currency, job_salary_period. :contentReference[oaicite:0]{index=0}
      - Server-side salary filters aren't clearly documented; we filter client-side.
        If your tier/docs show 'salary_min'/'salary_max', pass them in via `extra`.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        raise RuntimeError("RAPIDAPI_KEY is missing")

    all_jobs = []
    for page in range(1, max(1, pages) + 1):
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        params = {
            "query": f"{query} {location}",
            "page": str(page),
            "num_pages": "1",
        }
        if date_posted:
            params["date_posted"] = date_posted
        if remote_only:
            params["remote_jobs_only"] = "true"
        if employment_types:
            params["employment_types"] = ",".join(employment_types)
        if extra:
            params.update(extra)  # future-proof: radius, any experimental salary filters, etc.

        r = requests.get("https://jsearch.p.rapidapi.com/search",
                         headers=headers, params=params, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"JSearch error {r.status_code}: {r.text}")

        data = r.json()
        for j in data.get("data", []):
            # Raw salary fields from JSearch (may be None)  :contentReference[oaicite:1]{index=1}
            raw_min = j.get("job_min_salary")
            raw_max = j.get("job_max_salary")
            currency = j.get("job_salary_currency")
            period   = j.get("job_salary_period")

            # Normalize to annual to compare against filters
            ann_min = _annualize(raw_min, period)
            ann_max = _annualize(raw_max, period)

            # Currency filter (optional)
            if salary_currency and currency and currency.upper() != salary_currency.upper():
                continue

            # Apply client-side salary range filter (only include if we can compare)
            if salary_min is not None or salary_max is not None:
                # If the listing has no salary at all, skip it when filters are requested
                if ann_min is None and ann_max is None:
                    continue
                # Treat missing bound as equal to the other
                lo = ann_min if ann_min is not None else ann_max
                hi = ann_max if ann_max is not None else ann_min
                # If still None, skip
                if lo is None and hi is None:
                    continue
                # Range overlap checks
                if salary_min is not None and (hi is not None and hi < salary_min):
                    continue
                if salary_max is not None and (lo is not None and lo > salary_max):
                    continue

            all_jobs.append({
                "title": j.get("job_title"),
                "company": j.get("employer_name"),
                "location": ", ".join([x for x in [j.get("job_city"), j.get("job_state"), j.get("job_country")] if x]) or j.get("job_country"),
                "via": j.get("job_publisher"),
                "posted": j.get("job_posted_at_datetime_utc") or j.get("job_posted_at_timestamp"),
                "schedule": j.get("job_employment_type"),
                "apply_options": [j.get("job_apply_link")] if j.get("job_apply_link") else [],
                "job_id": j.get("job_id"),
                "share_link": j.get("job_google_link"),
                "description": j.get("job_description"),
                # salary (raw + normalized for convenience)
                "salary_min": raw_min,
                "salary_max": raw_max,
                "salary_currency": currency,
                "salary_period": period,
                "salary_annual_min": ann_min,
                "salary_annual_max": ann_max,
            })
    return all_jobs

