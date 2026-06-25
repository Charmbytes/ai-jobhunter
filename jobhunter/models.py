"""Core data models for the job hunter pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    """A normalized job/internship listing from any source."""
    source: str                       # "adzuna", "remotive", "mock", ...
    source_id: str                    # unique id within the source
    title: str
    company: str
    location: str
    url: str                          # apply / listing url
    description: str = ""
    salary_min: Optional[float] = None  # annual, in source currency (INR for adzuna 'in')
    salary_max: Optional[float] = None
    currency: str = "INR"
    posted: Optional[datetime] = None
    contract_time: Optional[str] = None      # "full_time" / "part_time" / "internship"
    category: Optional[str] = None

    # filled in by the matching engine
    detected_skills: list[str] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    experience_level: Optional[str] = None   # inferred: intern/entry/mid/senior
    alignment: float = 0.0                    # 0-100 skills alignment score
    score: float = 0.0                        # overall ranking score

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.source_id}"

    def salary_str(self) -> str:
        if self.salary_min and self.salary_max:
            return f"{self.currency} {self.salary_min:,.0f}-{self.salary_max:,.0f}"
        if self.salary_min:
            return f"{self.currency} {self.salary_min:,.0f}+"
        return "not listed"


@dataclass
class UserProfile:
    name: str = ""
    email: str = ""
    skills: list[str] = field(default_factory=list)
    # answers used to help fill application forms during assisted-apply
    phone: str = ""
    resume_path: str = ""
    cover_letter_template: str = ""


@dataclass
class Filters:
    keywords: list[str] = field(default_factory=list)   # job profile / role terms
    locations: list[str] = field(default_factory=list)  # e.g. ["Mumbai", "Remote"]
    salary_min: Optional[float] = None                  # annual floor (INR)
    experience_levels: list[str] = field(default_factory=list)  # intern/entry/mid/senior
    min_alignment: float = 0.0                           # 0-100 skills-alignment floor
    max_days_old: int = 30
    remote_ok: bool = True
