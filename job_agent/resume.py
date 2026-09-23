from __future__ import annotations

import json
import re
from pathlib import Path

from .domain import Resume


def load_resume(path: str | Path) -> Resume:
    """Load a structured JSON or document resume into the matching model."""
    resume_path = Path(path)
    if resume_path.suffix.lower() == ".json":
        return _resume_from_record(json.loads(resume_path.read_text(encoding="utf-8")))
    return parse_resume_text(_extract_text(resume_path))


def parse_resume_text(text: str) -> Resume:
    """Extract conservative profile fields from plain resume text."""
    lines = [line.strip(" \t-*") for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Resume does not contain readable text")
    name = lines[0]
    summary = _section(text, ("summary", "professional summary", "profile"))
    skills_text = _section(text, ("skills", "technical skills", "technologies"))
    skills = _split_skills(skills_text)
    years = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\+?\s+years?", text, re.I)]
    locations = tuple(
        location for location in ("Toronto", "Ontario", "Remote", "Canada", "United States")
        if re.search(rf"\b{re.escape(location)}\b", text, re.I)
    )
    title = lines[1] if len(lines) > 1 and not _is_heading(lines[1]) else ""
    return Resume(
        name=name,
        summary=summary or title,
        skills=frozenset(skills),
        years_experience=max(years, default=0),
        preferred_titles=(title,) if title else (),
        preferred_locations=locations,
    )


def _resume_from_record(record: dict) -> Resume:
    return Resume(
        name=record["name"],
        summary=record.get("summary", ""),
        skills=frozenset(record.get("skills", [])),
        years_experience=float(record.get("years_experience", 0)),
        preferred_titles=tuple(record.get("preferred_titles", [])),
        preferred_locations=tuple(record.get("preferred_locations", [])),
        work_authorization=record.get("work_authorization"),
    )


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise RuntimeError("PDF resumes require the optional 'pypdf' dependency") from error
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as error:
            raise RuntimeError("DOCX resumes require the optional 'python-docx' dependency") from error
        return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    raise ValueError("Resume must be a .json, .txt, .md, .pdf, or .docx file")


def _section(text: str, headings: tuple[str, ...]) -> str:
    heading_pattern = "|".join(re.escape(heading) for heading in headings)
    match = re.search(rf"(?im)^\s*(?:{heading_pattern})\s*:?\s*$", text)
    if not match:
        return ""
    remainder = text[match.end():]
    next_heading = re.search(r"(?m)^\s*[A-Z][A-Z /&-]{2,}\s*:?\s*$", remainder)
    return remainder[:next_heading.start() if next_heading else None].strip()


def _split_skills(text: str) -> set[str]:
    skills = set()
    for value in re.split(r"[,;|\n]", text):
        skill = value.strip()
        if not skill or len(skill) > 60 or re.search(r"\d+\+?\s+years?", skill, re.I):
            continue
        if skill.lower() in {"toronto", "ontario", "remote", "canada", "united states"}:
            continue
        skills.add(skill)
    return skills


def _is_heading(line: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z /&-]{2,}", line))