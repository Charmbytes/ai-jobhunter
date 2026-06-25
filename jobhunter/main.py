"""CLI entry point: load config -> fetch from sources -> filter+rank ->
review/approve -> assisted apply."""
from __future__ import annotations

import argparse
import os
import sys

import yaml

from .apply import assisted_apply
from .matching import filter_and_rank
from .models import Filters, UserProfile
from .review import console, review
from .sources import AdzunaSource, MockSource, RemotiveSource


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        console.print(f"[red]Config not found: {path}[/red] — copy config.example.yaml to config.yaml")
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f) or {}


def build_sources(cfg: dict, use_mock: bool):
    if use_mock:
        return [MockSource()]
    sources = []
    az = cfg.get("adzuna") or {}
    if az.get("app_id") and az.get("app_key"):
        sources.append(AdzunaSource(az["app_id"], az["app_key"], az.get("country", "in")))
    else:
        console.print("[yellow]No Adzuna keys in config — skipping Adzuna.[/yellow]")
    if (cfg.get("filters") or {}).get("remote_ok", True):
        sources.append(RemotiveSource())
    if not sources:
        console.print("[yellow]No real sources configured; falling back to mock data.[/yellow]")
        sources.append(MockSource())
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Job & internship hunter")
    parser.add_argument("-c", "--config", default="config.yaml")
    parser.add_argument("--mock", action="store_true", help="use built-in sample data (no API keys)")
    parser.add_argument("--limit", type=int, default=50, help="max listings per source")
    parser.add_argument("--no-apply", action="store_true", help="review only, skip the apply step")
    parser.add_argument("--autofill", action="store_true", help="enable best-effort form autofill (never submits)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    prof_cfg = cfg.get("profile") or {}
    profile = UserProfile(
        name=prof_cfg.get("name", ""),
        email=prof_cfg.get("email", ""),
        phone=prof_cfg.get("phone", ""),
        skills=prof_cfg.get("skills", []),
        resume_path=prof_cfg.get("resume_path", ""),
    )

    f = cfg.get("filters") or {}
    filters = Filters(
        keywords=f.get("keywords", []),
        locations=f.get("locations", []),
        salary_min=f.get("salary_min"),
        experience_levels=f.get("experience_levels", []),
        min_alignment=f.get("min_alignment", 0),
        max_days_old=f.get("max_days_old", 30),
        remote_ok=f.get("remote_ok", True),
    )

    sources = build_sources(cfg, args.mock)
    console.print(f"[dim]Fetching from: {', '.join(s.name for s in sources)}[/dim]")

    all_jobs = []
    for s in sources:
        got = s.fetch(filters, limit=args.limit)
        console.print(f"  {s.name}: {len(got)} listings")
        all_jobs.extend(got)

    ranked = filter_and_rank(all_jobs, profile.skills, filters)
    console.print(f"[bold]{len(ranked)} jobs passed your filters.[/bold]\n")

    approved = review(ranked)

    if approved and not args.no_apply:
        assisted_apply(approved, profile, autofill=args.autofill)
    elif approved:
        console.print("\nApproved links:")
        for j in approved:
            console.print(f"  • {j.title} @ {j.company} — {j.url}")


if __name__ == "__main__":
    main()
