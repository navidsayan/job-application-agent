import unittest

from job_agent.domain import Job, Resume, match_job


class MatchingTests(unittest.TestCase):
    def test_good_match_requires_all_required_skills(self) -> None:
        resume = Resume("Ada", "engineer", frozenset({"Python", "Postgres"}), 5)
        job = Job(
            "1", "Backend Engineer", "Acme", "Remote", "", "https://example.com/1", "test",
            required_skills=frozenset({"Python"}), preferred_skills=frozenset({"Postgres"}), remote=True,
        )

        result = match_job(resume, job)

        self.assertTrue(result.is_good_match)
        self.assertEqual(result.missing_required_skills, frozenset())
        self.assertGreaterEqual(result.score, 0.9)


    def test_missing_required_skill_is_rejected(self) -> None:
        resume = Resume("Ada", "engineer", frozenset({"Python"}), 5)
        job = Job(
            "2", "Backend Engineer", "Acme", "Remote", "", "https://example.com/2", "test",
            required_skills=frozenset({"Python", "Go"}), remote=True,
        )

        result = match_job(resume, job)

        self.assertFalse(result.is_good_match)
        self.assertEqual(result.missing_required_skills, frozenset({"go"}))
