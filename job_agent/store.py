from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .domain import Application, ApplicationStatus


class ApplicationStore:
    """SQLite persistence layer for review records and approval state."""

    def __init__(self, path: str | Path = "job-agent.db") -> None:
        """Open the database and create its table on first use."""
        self.path = str(path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS applications (
                    job_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        """Return a short-lived connection for one atomic store operation."""
        return sqlite3.connect(self.path)

    def save_review(self, application: Application) -> None:
        """Persist a new review item without duplicating an existing job ID."""
        payload = {
            "job": application.job.__dict__ | {
                "required_skills": list(application.job.required_skills),
                "preferred_skills": list(application.job.preferred_skills),
            },
            "match": application.match.__dict__ | {
                "matched_skills": list(application.match.matched_skills),
                "missing_required_skills": list(application.match.missing_required_skills),
            },
            "tailored_resume": application.tailored_resume,
            "cover_letter": application.cover_letter,
            "answers": application.answers,
            "metadata": application.metadata,
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO applications(job_id, payload, status) VALUES (?, ?, ?)",
                (application.job.id, json.dumps(payload), application.status.value),
            )

    def save_materials(self, job_id: str, resume_focus: str, cover_letter: str) -> bool:
        """Attach generated drafts to an existing application review record."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM applications WHERE job_id = ?", (job_id,)
            ).fetchone()
            if not row:
                return False
            payload = json.loads(row[0])
            payload["tailored_resume"] = resume_focus
            payload["cover_letter"] = cover_letter
            result = connection.execute(
                "UPDATE applications SET payload = ? WHERE job_id = ?",
                (json.dumps(payload), job_id),
            )
        return result.rowcount == 1

    def list_applications(self, status: str | None = None) -> list[dict]:
        """Return persisted applications, optionally filtered by status."""
        with self._connect() as connection:
            if status:
                rows = connection.execute(
                    "SELECT job_id, payload, status FROM applications WHERE status = ? ORDER BY job_id",
                    (status,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT job_id, payload, status FROM applications ORDER BY job_id"
                ).fetchall()
        return [{"job_id": job_id, "status": status, **json.loads(payload)} for job_id, payload, status in rows]

    def list_reviews(self) -> list[dict]:
        """Return all applications waiting for human review."""
        return self.list_applications(ApplicationStatus.REVIEW.value)

    def approve(self, job_id: str) -> bool:
        """Move one review item to approved, returning whether it was updated."""
        with self._connect() as connection:
            result = connection.execute(
                "UPDATE applications SET status = ? WHERE job_id = ? AND status = ?",
                (ApplicationStatus.APPROVED.value, job_id, ApplicationStatus.REVIEW.value),
            )
        return result.rowcount == 1

    def reject(self, job_id: str) -> bool:
        """Move one review item out of the queue without submitting it."""
        with self._connect() as connection:
            result = connection.execute(
                "UPDATE applications SET status = ? WHERE job_id = ? AND status = ?",
                (ApplicationStatus.REJECTED.value, job_id, ApplicationStatus.REVIEW.value),
            )
        return result.rowcount == 1

    def status(self, job_id: str) -> str | None:
        """Read the current lifecycle state for a job, if it is known."""
        with self._connect() as connection:
            row = connection.execute("SELECT status FROM applications WHERE job_id = ?", (job_id,)).fetchone()
        return row[0] if row else None
