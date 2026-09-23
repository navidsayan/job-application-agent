from __future__ import annotations

import argparse
from .pipeline import discover_once, run_forever
from .resume import load_resume
from .sources import (
    AshbyJobSource,
    CompositeSource,
    GreenhouseJobSource,
    JsonJobSource,
    LeverJobSource,
    RecruiteeJobSource,
    SmartRecruitersJobSource,
    ArbeitnowJobSource,
    RemotiveJobSource,
)
from .store import ApplicationStore
from .tailoring import OllamaClient, tailor_application


def build_job_source(args: argparse.Namespace):
    """Build configured fixture and public ATS sources for discovery."""
    sources = []
    if args.jobs:
        sources.append(JsonJobSource(args.jobs))
    if args.greenhouse_board:
        sources.append(GreenhouseJobSource(args.greenhouse_board))
    if args.lever_site:
        sources.append(LeverJobSource(args.lever_site))
    if args.ashby_board:
        sources.append(AshbyJobSource(args.ashby_board))
    if args.smartrecruiters_company:
        sources.append(SmartRecruitersJobSource(args.smartrecruiters_company))
    if args.recruitee_company:
        sources.append(RecruiteeJobSource(args.recruitee_company))
    if args.arbeitnow:
        sources.append(ArbeitnowJobSource())
    if args.remotive:
        sources.append(RemotiveJobSource())
    if not sources:
        raise ValueError("Configure at least one job source")
    return CompositeSource(sources)


def add_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--jobs")
    parser.add_argument("--greenhouse-board")
    parser.add_argument("--lever-site")
    parser.add_argument("--ashby-board")
    parser.add_argument("--smartrecruiters-company")
    parser.add_argument("--recruitee-company")
    parser.add_argument("--arbeitnow", action="store_true")
    parser.add_argument("--remotive", action="store_true")


def main() -> None:
    """Run discovery, review, or explicit approval from the command line."""
    parser = argparse.ArgumentParser(description="Discover and queue matching jobs for review")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover")
    discover_parser.add_argument("--resume", required=True)
    add_source_arguments(discover_parser)
    discover_parser.add_argument("--db", default="job-agent.db")

    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("--resume", required=True)
    add_source_arguments(watch_parser)
    watch_parser.add_argument("--db", default="job-agent.db")
    watch_parser.add_argument("--interval", type=int, default=1800)

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--db", default="job-agent.db")

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("job_id")
    approve_parser.add_argument("--db", default="job-agent.db")

    reject_parser = subparsers.add_parser("reject")
    reject_parser.add_argument("job_id")
    reject_parser.add_argument("--db", default="job-agent.db")

    tailor_parser = subparsers.add_parser("tailor")
    tailor_parser.add_argument("job_id")
    tailor_parser.add_argument("--resume", required=True)
    tailor_parser.add_argument("--jobs", required=True)
    tailor_parser.add_argument("--db", default="job-agent.db")
    tailor_parser.add_argument("--model", default="qwen2.5-coder:7b")
    tailor_parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")

    args = parser.parse_args()
    store = ApplicationStore(args.db)
    if args.command in {"discover", "watch"}:
        try:
            source = build_job_source(args)
        except ValueError as error:
            parser.error(str(error))
        resume = load_resume(args.resume)
        if args.command == "watch":
            run_forever(resume, source, store, args.interval)
            return
        applications = discover_once(resume, source, store)
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
    elif args.command == "reject":
        if not store.reject(args.job_id):
            parser.error(f"No review application found for {args.job_id!r}")
        print(f"Rejected {args.job_id}")
    elif args.command == "tailor":
        job = next((job for job in JsonJobSource(args.jobs).fetch() if job.id == args.job_id), None)
        if not job:
            parser.error(f"Job {args.job_id!r} was not found in the job source")
        if store.status(args.job_id) != "review":
            parser.error(f"Job {args.job_id!r} is not waiting for review")
        materials = tailor_application(
            load_resume(args.resume),
            job,
            OllamaClient(model=args.model, base_url=args.ollama_url),
        )
        store.save_materials(args.job_id, materials.resume_focus, materials.cover_letter)
        print(f"Tailored drafts saved for {args.job_id}")


if __name__ == "__main__":
    main()
