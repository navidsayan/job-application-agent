from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApplicationStatus(str, Enum):
    """Lifecycle states used to keep discovery, review, and submission separate."""

    DISCOVERED = "discovered"
    REVIEW = "review"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Resume:
    """Normalized candidate profile used by the matching engine."""

    name: str
    summary: str
    skills: frozenset[str]
    years_experience: float = 0
    preferred_titles: tuple[str, ...] = ()
    preferred_locations: tuple[str, ...] = ()
    work_authorization: str | None = None


@dataclass(frozen=True)
class Job:
    """Job listing data normalized across all discovery sources."""

    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    required_skills: frozenset[str] = frozenset()
    preferred_skills: frozenset[str] = frozenset()
    min_years_experience: float = 0
    remote: bool = False


@dataclass(frozen=True)
class MatchResult:
    """Explainable fit score and gaps produced for one job."""

    job_id: str
    score: float
    matched_skills: frozenset[str]
    missing_required_skills: frozenset[str]
    reasons: tuple[str, ...] = ()

    @property
    def is_good_match(self) -> bool:
        """Require both a minimum score and no missing required skills."""
        return not self.missing_required_skills and self.score >= 0.55


@dataclass
class Application:
    """Reviewable application package built from a job and its match result."""

    job: Job
    match: MatchResult
    status: ApplicationStatus = ApplicationStatus.REVIEW
    tailored_resume: str | None = None
    cover_letter: str | None = None
    answers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize(value: str) -> str:
    """Normalize skill and location text for case-insensitive comparisons."""
    return " ".join(value.lower().replace("/", " ").split())


def match_job(resume: Resume, job: Job) -> MatchResult:
    """Score a job against a resume and collect human-readable match reasons."""
    resume_skills = {normalize(skill) for skill in resume.skills}
    required = {normalize(skill) for skill in job.required_skills}
    preferred = {normalize(skill) for skill in job.preferred_skills}
    matched_required = resume_skills & required
    matched_preferred = resume_skills & preferred
    missing_required = required - resume_skills

    required_score = len(matched_required) / len(required) if required else 1.0
    preferred_score = len(matched_preferred) / len(preferred) if preferred else 1.0
    # Required skills dominate; experience and location provide smaller adjustments.
    score = (required_score * 0.65) + (preferred_score * 0.2)

    if resume.years_experience >= job.min_years_experience:
        score += 0.1
    else:
        score -= 0.1

    location_matches = not resume.preferred_locations or any(
        normalize(location) in normalize(job.location)
        for location in resume.preferred_locations
    )
    if location_matches or job.remote:
        score += 0.05
    else:
        score -= 0.05

    reasons = []
    title_matches = any(
        normalize(title) in normalize(job.title) or normalize(job.title) in normalize(title)
        for title in resume.preferred_titles
    )
    if title_matches:
        score += 0.05
        reasons.append("Matches a preferred job title")
    if matched_required:
        reasons.append(f"Matches required skills: {', '.join(sorted(matched_required))}")
    if missing_required:
        reasons.append(f"Missing required skills: {', '.join(sorted(missing_required))}")
    if resume.years_experience < job.min_years_experience:
        reasons.append("Below the stated experience requirement")
    if not location_matches and not job.remote:
        reasons.append("Outside preferred locations")

    return MatchResult(
        job_id=job.id,
        score=max(0.0, min(1.0, score)),
        matched_skills=frozenset(matched_required | matched_preferred),
        missing_required_skills=frozenset(missing_required),
        reasons=tuple(reasons),
    )
