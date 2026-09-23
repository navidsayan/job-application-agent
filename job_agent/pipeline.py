from __future__ import annotations

import time
from collections.abc import Callable

from .domain import Application, ApplicationStatus, Resume, match_job
from .sources import JobSource
from .store import ApplicationStore


def discover_once(resume: Resume, source: JobSource, store: ApplicationStore) -> list[Application]:
    """Fetch jobs, retain good matches, and place them in the review queue."""
    reviews: list[Application] = []
    for job in source.fetch():
        match = match_job(resume, job)
        if match.is_good_match:
            application = Application(job=job, match=match, status=ApplicationStatus.REVIEW)
            store.save_review(application)
            reviews.append(application)
    return reviews


def run_forever(
    resume: Resume,
    source: JobSource,
    store: ApplicationStore,
    interval_seconds: int,
    on_cycle: Callable[[list[Application]], None] | None = None,
) -> None:
    """Repeat discovery at a fixed interval for background operation."""
    while True:
        applications = discover_once(resume, source, store)
        if on_cycle:
            on_cycle(applications)
        time.sleep(interval_seconds)
