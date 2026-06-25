"""A built-in mock source so you can run the full pipeline (filter -> rank ->
review) immediately, with no API keys. Swap it out for real sources later."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..models import Filters, Job
from .base import JobSource

_SAMPLE = [
    dict(title="Data Science Intern", company="Acme Analytics", location="Mumbai, Maharashtra",
         salary_min=300000, salary_max=600000, contract_time="internship",
         desc="Looking for an intern with Python, Pandas, SQL and basic Machine Learning. "
              "Exposure to scikit-learn and data visualization preferred. Fresher / 0-1 year."),
    dict(title="Backend Developer (Junior)", company="ByteForge", location="Pune, Maharashtra",
         salary_min=600000, salary_max=1000000, contract_time="full_time",
         desc="Entry level backend role. Python, Django, REST APIs, PostgreSQL, Docker. "
              "0-2 years experience. Knowledge of AWS is a plus."),
    dict(title="Senior Machine Learning Engineer", company="DeepMind Labs", location="Bengaluru, Karnataka",
         salary_min=2500000, salary_max=4000000, contract_time="full_time",
         desc="Senior role. PyTorch, TensorFlow, MLOps, distributed training, 6+ years experience. "
              "Strong Python and system design required."),
    dict(title="Frontend Engineering Intern", company="PixelWorks", location="Remote",
         salary_min=240000, salary_max=480000, contract_time="internship",
         desc="React, JavaScript, TypeScript, HTML, CSS. Intern position, remote. "
              "Figma familiarity nice to have."),
    dict(title="Full Stack Developer", company="StartupX", location="Mumbai, Maharashtra",
         salary_min=800000, salary_max=1400000, contract_time="full_time",
         desc="Mid-level. React, Node.js, MongoDB, Python, Docker, AWS. 2-4 years. "
              "Will work across the stack."),
    dict(title="Data Analyst", company="FinReports", location="Remote",
         salary_min=500000, salary_max=900000, contract_time="full_time",
         desc="SQL, Excel, Power BI, Python, statistics. Entry to mid level, 1-3 years."),
]


class MockSource(JobSource):
    name = "mock"

    def fetch(self, filters: Filters, limit: int = 50) -> list[Job]:
        jobs = []
        for i, s in enumerate(_SAMPLE):
            jobs.append(
                Job(
                    source=self.name,
                    source_id=str(i),
                    title=s["title"],
                    company=s["company"],
                    location=s["location"],
                    url=f"https://example.com/job/{i}",
                    description=s["desc"],
                    salary_min=s["salary_min"],
                    salary_max=s["salary_max"],
                    currency="INR",
                    posted=datetime.now() - timedelta(days=i),
                    contract_time=s["contract_time"],
                )
            )
        return jobs[:limit]
