import tempfile
import unittest
from pathlib import Path

from job_agent.domain import Application, Job, MatchResult
from job_agent.store import ApplicationStore


class StoreTests(unittest.TestCase):
    def test_reject_moves_review_item_out_of_queue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ApplicationStore(Path(directory) / "applications.db")
            job = Job("job-1", "Engineer", "Acme", "Remote", "", "url", "test")
            match = MatchResult("job-1", 0.8, frozenset(), frozenset())
            store.save_review(Application(job=job, match=match))

            self.assertTrue(store.reject("job-1"))
            self.assertEqual(store.status("job-1"), "rejected")
            self.assertEqual(store.list_reviews(), [])