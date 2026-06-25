"""Adzuna job source.

Adzuna offers a free developer API that legally aggregates listings from
across the web, including Naukri/Indeed-style postings in India. It supports
keyword, location, salary and category filters server-side.

Get free credentials at https://developer.adzuna.com/ and put them in config:
    adzuna:
      app_id: "xxxx"
      app_key: "yyyy"
      country: "in"
"""
from __future__ import annotations

from datetime import datetime

import requests

from ..models import Filters, Job
from .base import JobSource

BASE = "https://api.adzuna.com/v1/api/jobs"


class AdzunaSource(JobSource):
    name = "adzuna"

    def __init__(self, app_id: str, app_key: str, country: str = "in"):
        self.app_id = app_id
        self.app_key = app_key
        self.country = country

    def fetch(self, filters: Filters, limit: int = 50) -> list[Job]:
        what = " ".join(filters.keywords) if filters.keywords else ""
        where = filters.locations[0] if filters.locations else ""
        per_page = min(limit, 50)

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": per_page,
            "what": what,
            "max_days_old": filters.max_days_old,
            "content-type": "application/json",
        }
        if where and where.lower() != "remote":
            params["where"] = where
        if filters.salary_min:
            params["salary_min"] = int(filters.salary_min)

        url = f"{BASE}/{self.country}/search/1"
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            print(f"[adzuna] fetch failed: {e}")
            return []

        jobs: list[Job] = []
        for r in data.get("results", []):
            posted = None
            if r.get("created"):
                try:
                    posted = datetime.fromisoformat(r["created"].replace("Z", "+00:00"))
                except ValueError:
                    posted = None
            jobs.append(
                Job(
                    source=self.name,
                    source_id=str(r.get("id", "")),
                    title=r.get("title", "").strip(),
                    company=(r.get("company") or {}).get("display_name", "Unknown"),
                    location=(r.get("location") or {}).get("display_name", ""),
                    url=r.get("redirect_url", ""),
                    description=r.get("description", ""),
                    salary_min=r.get("salary_min"),
                    salary_max=r.get("salary_max"),
                    currency="INR" if self.country == "in" else "",
                    posted=posted,
                    contract_time=r.get("contract_time"),
                    category=(r.get("category") or {}).get("label"),
                )
            )
        return jobs
