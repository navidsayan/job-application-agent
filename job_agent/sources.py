from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .domain import Job


class JobSource(Protocol):
    """Interface implemented by API, ATS, feed, or fixture job providers."""

    def fetch(self) -> list[Job]: ...


class JsonJobSource:
    """Local fixture source; replace with compliant APIs or approved ATS feeds."""

    def __init__(self, path: str | Path) -> None:
        """Create a source backed by a local JSON job-listing file."""
        self.path = Path(path)

    def fetch(self) -> list[Job]:
        """Load and normalize every listing in the configured JSON file."""
        records = json.loads(self.path.read_text(encoding="utf-8"))
        return [
            Job(
                id=str(record["id"]),
                title=record["title"],
                company=record["company"],
                location=record.get("location", ""),
                description=record.get("description", ""),
                url=record["url"],
                source=record.get("source", "json"),
                required_skills=frozenset(record.get("required_skills", [])),
                preferred_skills=frozenset(record.get("preferred_skills", [])),
                min_years_experience=float(record.get("min_years_experience", 0)),
                remote=bool(record.get("remote", False)),
            )
            for record in records
        ]


class CompositeSource:
    """Combine multiple sources while retaining one listing per job ID."""

    def __init__(self, sources: list[JobSource]) -> None:
        """Create a source that fans out to each configured provider."""
        self.sources = sources

    def fetch(self) -> list[Job]:
        """Fetch all providers and let later providers replace duplicate IDs."""
        jobs: dict[str, Job] = {}
        for source in self.sources:
            for job in source.fetch():
                jobs[job.id] = job
        return list(jobs.values())
