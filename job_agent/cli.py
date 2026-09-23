from __future__ import annotations

import argparse
import json
from pathlib import Path

from .domain import Resume
from .pipeline import discover_once
from .sources import JsonJobSource
from .store import ApplicationStore


def load_resume(path: str) -> Resume:
    """Load the candidate profile JSON into the matching model."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    return Resume(
        name=record["name"],
        summary=record.get("summary", ""),
        skills=frozenset(record.get("skills", [])),
        years_experience=float(record.get("years_experience", 0)),
        preferred_titles=tuple(record.get("preferred_titles", [])),
        preferred_locations=tuple(record.get("preferred_locations", [])),
        work_authorization=record.get("work_authorization"),
    )


def main() -> None:
    """Run discovery, review, or explicit approval from the command line."""
    parser = argparse.ArgumentParser(description="Discover and queue matching jobs for review")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover")
    discover_parser.add_argument("--resume", required=True)
    discover_parser.add_argument("--jobs", required=True)
    discover_parser.add_argument("--db", default="job-agent.db")

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--db", default="job-agent.db")

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("job_id")
    approve_parser.add_argument("--db", default="job-agent.db")

    args = parser.parse_args()
    store = ApplicationStore(args.db)
    if args.command == "discover":
        applications = discover_once(
            load_resume(args.resume), JsonJobSource(args.jobs), store
        )
        for application in applications:
            print(f"{application.job.id}: {application.job.title} at {application.job.company} ({application.match.score:.0%})")
    elif args.command == "review":
        for application in store.list_reviews():
            match = application["match"]
            print(f"{application['job_id']}: {application['job']['title']} at {application['job']['company']} ({match['score']:.0%})")
    elif args.command == "approve":
        if not store.approve(args.job_id):
            parser.error(f"No review application found for {args.job_id!r}")
        print(f"Approved {args.job_id}")


if __name__ == "__main__":
    main()
