from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .domain import Job, Resume


class TextGenerator(Protocol):
    """Minimal interface that allows local LLMs and test doubles to be swapped."""

    def generate(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class TailoredMaterials:
    """Draft materials produced for human review before an application is sent."""

    resume_focus: str
    cover_letter: str


class OllamaClient:
    """Generate text through a local Ollama HTTP server."""

    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://127.0.0.1:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str) -> str:
        """Request one non-streaming completion from the configured local model."""
        from urllib.request import Request, urlopen

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        }).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["response"]


def tailor_application(resume: Resume, job: Job, generator: TextGenerator) -> TailoredMaterials:
    """Create factual, job-specific drafts from the candidate profile and listing."""
    prompt = f"""You are a careful job-application writing assistant.

Use only facts present in the candidate profile. Never invent employers, dates,
projects, metrics, degrees, certifications, skills, or authorization status.
Return valid JSON with exactly two string fields: resume_focus and cover_letter.
The resume_focus should be a concise paragraph describing which existing
experience and skills to emphasize for this role. The cover_letter should be
professional, specific to the job, and under 300 words.

CANDIDATE PROFILE:
Name: {resume.name}
Summary: {resume.summary}
Skills: {', '.join(sorted(resume.skills))}
Years of experience: {resume.years_experience}

JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Required skills: {', '.join(sorted(job.required_skills))}
Preferred skills: {', '.join(sorted(job.preferred_skills))}
Description: {job.description}
"""
    raw = generator.generate(prompt)
    try:
        result = json.loads(raw)
        resume_focus = result["resume_focus"].strip()
        cover_letter = result["cover_letter"].strip()
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("The local model returned invalid tailoring JSON") from error
    if not resume_focus or not cover_letter:
        raise ValueError("The local model returned empty tailoring content")
    return TailoredMaterials(resume_focus=resume_focus, cover_letter=cover_letter)
