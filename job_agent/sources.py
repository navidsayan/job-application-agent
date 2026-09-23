from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Protocol
from urllib.request import Request, urlopen

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


class GreenhouseJobSource:
    """Read published jobs from a company's public Greenhouse board API."""

    def __init__(self, board: str) -> None:
        self.board = board

    def fetch(self) -> list[Job]:
        payload = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs?content=true")
        jobs = []
        for record in payload.get("jobs", []):
            description = _strip_html(record.get("content", ""))
            location = record.get("location", {}).get("name", "")
            jobs.append(Job(
                id=f"greenhouse:{self.board}:{record['id']}",
                title=record["title"],
                company=self.board,
                location=location,
                description=description,
                url=record["absolute_url"],
                source="greenhouse",
                remote="remote" in f"{location} {description}".lower(),
            ))
        return jobs


class LeverJobSource:
    """Read published jobs from a company's public Lever postings API."""

    def __init__(self, site: str) -> None:
        self.site = site

    def fetch(self) -> list[Job]:
        payload = _get_json(f"https://api.lever.co/v0/postings/{self.site}?mode=json")
        return [Job(
            id=f"lever:{self.site}:{record['id']}",
            title=record["text"],
            company=self.site,
            location=record.get("categories", {}).get("location", ""),
            description=record.get("descriptionPlain", ""),
            url=record["hostedUrl"],
            source="lever",
            remote="remote" in (
                record.get("categories", {}).get("location", "")
                + " "
                + record.get("descriptionPlain", "")
            ).lower(),
        ) for record in payload]

class AshbyJobSource:
    """Read published jobs from an Ashby public job board API."""

    def __init__(self, board: str) -> None:
        self.board = board

    def fetch(self) -> list[Job]:
        payload = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{self.board}")
        return [_ashby_job(self.board, record) for record in payload.get("jobs", [])]


class SmartRecruitersJobSource:
    """Read published jobs from a SmartRecruiters public company API."""

    def __init__(self, company: str) -> None:
        self.company = company

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        offset = 0
        while True:
            payload = _get_json(
                f"https://api.smartrecruiters.com/v1/companies/{self.company}/postings?limit=100&offset={offset}"
            )
            content = payload.get("content", [])
            jobs.extend(_smartrecruiters_job(self.company, record) for record in content)
            if len(content) < 100:
                return jobs
            offset += len(content)


class RecruiteeJobSource:
    """Read published jobs from a Recruitee public company API."""

    def __init__(self, company: str) -> None:
        self.company = company

    def fetch(self) -> list[Job]:
        payload = _get_json(f"https://{self.company}.recruitee.com/api/offers")
        return [_recruitee_job(self.company, record) for record in payload.get("offers", [])]


class ArbeitnowJobSource:
    """Read jobs from Arbeitnow's public job-board API."""

    def fetch(self) -> list[Job]:
        payload = _get_json("https://www.arbeitnow.com/api/job-board-api")
        return [Job(
            id=f"arbeitnow:{record.get('slug', record.get('id'))}",
            title=record["title"],
            company=record.get("company_name", "Unknown company"),
            location=record.get("location", ""),
            description=_strip_html(record.get("description", "")),
            url=record["url"],
            source="arbeitnow",
            remote=bool(record.get("remote")),
            preferred_skills=frozenset(record.get("tags", [])),
        ) for record in payload.get("data", [])]


class RemotiveJobSource:
    """Read remote jobs from Remotive's public jobs API."""

    def fetch(self) -> list[Job]:
        payload = _get_json("https://remotive.com/api/remote-jobs")
        return [Job(
            id=f"remotive:{record['id']}",
            title=record["title"],
            company=record.get("company_name", "Unknown company"),
            location=record.get("candidate_required_location", "Remote"),
            description=_strip_html(record.get("description", "")),
            url=record["url"],
            source="remotive",
            remote=True,
            preferred_skills=frozenset(record.get("tags", [])),
        ) for record in payload.get("jobs", [])]


class CompositeSource:
    """Combine multiple sources while retaining one listing per job ID."""

    def __init__(self, sources: list[JobSource]) -> None:
        """Create a source that fans out to each configured provider."""
        self.sources = sources

    def fetch(self) -> list[Job]:
        """Fetch all providers and retain one listing per ID or URL."""
        jobs: dict[str, Job] = {}
        identities: dict[str, str] = {}
        for source in self.sources:
            for job in source.fetch():
                identity_values = (job.id, job.url.rstrip("/").lower())
                existing_key = next((identities[value] for value in identity_values if value in identities), None)
                key = existing_key or job.id
                jobs[key] = job
                for value in identity_values:
                    identities[value] = key
        return list(jobs.values())


def _get_json(url: str) -> dict | list:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "job-application-agent/0.1"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _ashby_job(board: str, record: dict) -> Job:
    location = record.get("location", "")
    description = record.get("descriptionPlain", "") or _strip_html(record.get("descriptionHtml", ""))
    return Job(
        id=f"ashby:{board}:{record.get('id', record.get('jobPostingId'))}",
        title=record["title"],
        company=board,
        location=location,
        description=description,
        url=record["jobUrl"],
        source="ashby",
        remote=bool(record.get("isRemote")) or "remote" in f"{location} {description}".lower(),
    )


def _smartrecruiters_job(company: str, record: dict) -> Job:
    location = record.get("location", {})
    location_text = ", ".join(filter(None, (location.get("city"), location.get("region"), location.get("country"))))
    return Job(
        id=f"smartrecruiters:{company}:{record['id']}",
        title=record["name"],
        company=company,
        location=location_text,
        description=record.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", ""),
        url=record.get("ref", f"https://jobs.smartrecruiters.com/{company}/{record['id']}"),
        source="smartrecruiters",
        remote="remote" in location_text.lower(),
    )


def _recruitee_job(company: str, record: dict) -> Job:
    location = record.get("location", {})
    location_text = location.get("name", "") if isinstance(location, dict) else str(location)
    description = record.get("description", "")
    return Job(
        id=f"recruitee:{company}:{record['id']}",
        title=record["title"],
        company=company,
        location=location_text,
        description=_strip_html(description),
        url=record.get("careers_url", f"https://{company}.recruitee.com/o/{record['slug']}"),
        source="recruitee",
        remote="remote" in f"{location_text} {description}".lower(),
    )
