from __future__ import annotations

from .domain import ApplicationStatus
from .store import ApplicationStore


class PlaywrightSubmitter:
    """Submission boundary. Automation must be called only after explicit approval."""

    def __init__(self, store: ApplicationStore) -> None:
        """Create a submitter that checks approval through the shared store."""
        self.store = store

    def submit(self, job_id: str) -> None:
        """Enforce approval before a future site-specific Playwright submission."""
        if self.store.status(job_id) != ApplicationStatus.APPROVED.value:
            raise PermissionError(
                f"Application {job_id!r} is not approved; review it before submitting."
            )
        raise NotImplementedError(
            "Add a site-specific Playwright adapter after confirming the site's terms and form flow."
        )
