"""Filtering + skills-alignment scoring + ranking.

The scoring is deliberately transparent so you can see *why* a job ranks where
it does: it reports which of the job's skills you match and which you're missing.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from .models import Filters, Job

# A pragmatic skills vocabulary used to detect skills mentioned in a job post.
# Extend this freely — anything here that also appears in your profile counts
# toward alignment.
SKILL_VOCAB = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby",
    "php", "kotlin", "swift", "scala", "r", "matlab", "sql", "nosql",
    "react", "angular", "vue", "node.js", "node", "express", "django", "flask",
    "fastapi", "spring", "rails", ".net", "next.js",
    "html", "css", "tailwind", "bootstrap", "sass",
    "pandas", "numpy", "scikit-learn", "scikit", "tensorflow", "pytorch", "keras",
    "machine learning", "deep learning", "nlp", "computer vision", "data science",
    "statistics", "data analysis", "data visualization",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "jenkins",
    "git", "linux", "bash", "rest", "rest apis", "graphql", "microservices",
    "excel", "power bi", "tableau", "looker", "spark", "hadoop", "airflow", "kafka",
    "figma", "ui/ux", "product management", "agile", "scrum", "mlops",
}

# experience-level inference keywords (checked against title + description)
_LEVEL_PATTERNS = {
    "intern": [r"\bintern\b", r"\binternship\b", r"\btrainee\b"],
    "entry": [r"\bfresher\b", r"\bentry[\s-]?level\b", r"\bjunior\b", r"\bgraduate\b",
              r"\b0[\s-]?1\s*year", r"\b0[\s-]?2\s*year"],
    "mid": [r"\bmid[\s-]?level\b", r"\b2[\s-]?4\s*year", r"\b3[\s-]?5\s*year",
            r"\bassociate\b"],
    "senior": [r"\bsenior\b", r"\blead\b", r"\bprincipal\b", r"\bstaff\b",
               r"\b[5-9]\+?\s*year", r"\b1[0-9]\+?\s*year", r"\barchitect\b"],
}

_WORD = re.compile(r"[a-z0-9.+#/ ]+")


def _norm(s: str) -> str:
    return s.lower().strip()


def detect_skills(text: str) -> list[str]:
    """Find vocabulary skills present in free text (word-boundary aware)."""
    t = " " + text.lower() + " "
    found = []
    for skill in SKILL_VOCAB:
        # multiword skills: substring; single tokens: padded boundaries
        if " " in skill or any(c in skill for c in ".+#/"):
            if skill in t:
                found.append(skill)
        else:
            if re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", t):
                found.append(skill)
    return sorted(set(found))


def infer_experience(job: Job) -> str:
    text = f"{job.title} {job.description}".lower()
    if job.contract_time == "internship":
        return "intern"
    scores = {}
    for level, pats in _LEVEL_PATTERNS.items():
        scores[level] = sum(1 for p in pats if re.search(p, text))
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "entry"


def _fuzzy_in(skill: str, user_skills: set[str]) -> bool:
    """True if `skill` matches one of the user's skills (exact or fuzzy)."""
    if skill in user_skills:
        return True
    return any(fuzz.token_set_ratio(skill, us) >= 88 for us in user_skills)


def score_job(job: Job, user_skills: list[str], filters: Filters) -> Job:
    """Compute skills alignment + an overall ranking score, in place."""
    user_set = {_norm(s) for s in user_skills}
    job.detected_skills = detect_skills(f"{job.title} {job.description}")
    job.matched_skills = [s for s in job.detected_skills if _fuzzy_in(s, user_set)]
    job.missing_skills = [s for s in job.detected_skills if s not in job.matched_skills]
    job.experience_level = infer_experience(job)

    # alignment = how much of what the job asks for you cover
    if job.detected_skills:
        job.alignment = round(100 * len(job.matched_skills) / len(job.detected_skills), 1)
    else:
        job.alignment = 0.0

    # overall score blends alignment with a few quality signals
    score = job.alignment
    if job.salary_min:                       # listed salary -> small bonus
        score += 5
    if filters.salary_min and job.salary_min and job.salary_min >= filters.salary_min:
        score += 5
    if filters.experience_levels and job.experience_level in filters.experience_levels:
        score += 10
    job.score = round(min(score, 120), 1)
    return job


def _location_ok(job: Job, filters: Filters) -> bool:
    # Remotive only lists remote roles; "location" there is a candidate-eligibility
    # restriction (e.g. "Brazil", "USA only"), not a literal "remote" marker.
    is_remote = job.source == "remotive" or "remote" in job.location.lower()
    if filters.remote_ok and is_remote:
        return True
    if not filters.locations:
        return True
    loc = job.location.lower()
    for want in filters.locations:
        w = want.lower()
        if w != "remote" and w in loc:
            return True
    return False


def _keyword_ok(job: Job, filters: Filters) -> bool:
    if not filters.keywords:
        return True
    hay = f"{job.title} {job.description}".lower()
    return any(kw.lower() in hay for kw in filters.keywords)


def filter_and_rank(jobs: list[Job], user_skills: list[str], filters: Filters) -> list[Job]:
    """Score every job, drop those failing hard filters, return ranked best-first."""
    out: list[Job] = []
    seen: set[str] = set()
    for job in jobs:
        if job.uid in seen:
            continue
        seen.add(job.uid)

        score_job(job, user_skills, filters)

        if not _keyword_ok(job, filters):
            continue
        if not _location_ok(job, filters):
            continue
        if filters.salary_min and (not job.salary_min or job.salary_min < filters.salary_min):
            # keep jobs with no listed salary; only drop ones below the floor
            if job.salary_min is not None:
                continue
        if filters.experience_levels and job.experience_level not in filters.experience_levels:
            continue
        if job.alignment < filters.min_alignment:
            continue

        out.append(job)

    out.sort(key=lambda j: j.score, reverse=True)
    return out
