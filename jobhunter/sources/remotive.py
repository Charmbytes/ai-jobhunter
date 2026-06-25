"""Remotive job source — free public API for remote roles, no key needed.

Good complement to Adzuna when filters.remote_ok is True.
Docs: https://remotive.com/api/remote-jobs
"""
from __future__ import annotations

import re
from datetime import datetime

import requests

from ..models import Filters, Job
from .base import JobSource

API = "https://remotive.com/api/remote-jobs"
_TAGS = re.compile(r"<[^>]+>")


class RemotiveSource(JobSource):
    name = "remotive"

    def fetch(self, filters: Filters, limit: int = 50) -> list[Job]:
        search = " ".join(filters.keywords) if filters.keywords else ""
        params = {"limit": min(limit, 100)}
        if search:
            params["search"] = search
        try:
            resp = requests.get(API, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            print(f"[remotive] fetch failed: {e}")
            return []

        jobs: list[Job] = []
        for r in data.get("jobs", []):
            posted = None
            if r.get("publication_date"):
                try:
                    posted = datetime.fromisoformat(r["publication_date"])
                except ValueError:
                    posted = None
            desc = _TAGS.sub(" ", r.get("description", ""))
            jobs.append(
                Job(
                    source=self.name,
                    source_id=str(r.get("id", "")),
                    title=r.get("title", "").strip(),
                    company=r.get("company_name", "Unknown"),
                    location=r.get("candidate_required_location", "Remote") or "Remote",
                    url=r.get("url", ""),
                    description=desc,
                    currency="",
                    posted=posted,
                    contract_time=r.get("job_type"),
                    category=r.get("category"),
                )
            )
        return jobs
