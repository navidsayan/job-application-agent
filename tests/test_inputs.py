import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from job_agent.resume import load_resume, parse_resume_text
from job_agent.domain import Job
from job_agent.sources import (
    AshbyJobSource,
    ArbeitnowJobSource,
    CompositeSource,
    GreenhouseJobSource,
    LeverJobSource,
    RecruiteeJobSource,
    RemotiveJobSource,
    SmartRecruitersJobSource,
)


class InputTests(unittest.TestCase):
    def test_text_resume_extracts_profile_fields(self) -> None:
        resume = parse_resume_text(
            "Ada Lovelace\nSoftware Engineer\n\nSUMMARY\nBuild reliable systems.\n\nSKILLS\nPython, Postgres, Docker\n\n7+ years experience\nToronto"
        )

        self.assertEqual(resume.name, "Ada Lovelace")
        self.assertEqual(resume.skills, frozenset({"Python", "Postgres", "Docker"}))
        self.assertEqual(resume.years_experience, 7)

    def test_json_resume_keeps_existing_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.json"
            path.write_text('{"name":"Ada","skills":["Python"]}', encoding="utf-8")
            self.assertEqual(load_resume(path).skills, frozenset({"Python"}))

    @patch("job_agent.sources._get_json")
    def test_greenhouse_source_maps_public_listing(self, get_json) -> None:
        get_json.return_value = {"jobs": [{"id": 1, "title": "Engineer", "location": {"name": "Remote"}, "content": "<p>Python</p>", "absolute_url": "https://jobs.test/1"}]}
        job = GreenhouseJobSource("acme").fetch()[0]
        self.assertEqual(job.source, "greenhouse")
        self.assertTrue(job.remote)
        self.assertEqual(job.description, "Python")

    @patch("job_agent.sources._get_json")
    def test_lever_source_maps_public_listing(self, get_json) -> None:
        get_json.return_value = [{"id": "1", "text": "Engineer", "categories": {"location": "Remote"}, "descriptionPlain": "Build APIs", "hostedUrl": "https://jobs.test/1"}]
        job = LeverJobSource("acme").fetch()[0]
        self.assertEqual(job.id, "lever:acme:1")
        self.assertTrue(job.remote)

    @patch("job_agent.sources._get_json")
    def test_ashby_source_maps_public_listing(self, get_json) -> None:
        get_json.return_value = {"jobs": [{"jobPostingId": "1", "title": "Engineer", "location": "Remote", "descriptionPlain": "Build APIs", "jobUrl": "https://jobs.test/1", "isRemote": True}]}
        job = AshbyJobSource("acme").fetch()[0]
        self.assertEqual(job.id, "ashby:acme:1")
        self.assertTrue(job.remote)

    @patch("job_agent.sources._get_json")
    def test_smartrecruiters_source_maps_public_listing(self, get_json) -> None:
        get_json.return_value = {"content": [{"id": "1", "name": "Engineer", "location": {"city": "Toronto", "country": "Canada"}, "ref": "https://jobs.test/1"}]}
        job = SmartRecruitersJobSource("acme").fetch()[0]
        self.assertEqual(job.id, "smartrecruiters:acme:1")
        self.assertIn("Toronto", job.location)

    @patch("job_agent.sources._get_json")
    def test_recruitee_source_maps_public_listing(self, get_json) -> None:
        get_json.return_value = {"offers": [{"id": 1, "slug": "engineer", "title": "Engineer", "location": {"name": "Remote"}, "description": "<p>Build APIs</p>"}]}
        job = RecruiteeJobSource("acme").fetch()[0]
        self.assertEqual(job.id, "recruitee:acme:1")
        self.assertEqual(job.description, "Build APIs")
        self.assertTrue(job.remote)

    @patch("job_agent.sources._get_json")
    def test_arbeitnow_source_requires_no_company_slug(self, get_json) -> None:
        get_json.return_value = {"data": [{"slug": "1", "title": "Engineer", "company_name": "Acme", "location": "Toronto", "description": "Build APIs", "url": "https://jobs.test/1", "remote": False, "tags": ["Python"]}]}
        job = ArbeitnowJobSource().fetch()[0]
        self.assertEqual(job.source, "arbeitnow")
        self.assertEqual(job.preferred_skills, frozenset({"Python"}))

    @patch("job_agent.sources._get_json")
    def test_remotive_source_requires_no_company_slug(self, get_json) -> None:
        get_json.return_value = {"jobs": [{"id": 1, "title": "Engineer", "company_name": "Acme", "candidate_required_location": "Worldwide", "description": "<p>Build APIs</p>", "url": "https://jobs.test/1", "tags": ["Python"]}]}
        job = RemotiveJobSource().fetch()[0]
        self.assertEqual(job.source, "remotive")
        self.assertTrue(job.remote)

    def test_composite_source_deduplicates_by_url(self) -> None:
        first = Job("first", "Engineer", "Acme", "Remote", "", "https://jobs.test/1", "one")
        second = Job("second", "Engineer", "Acme", "Remote", "Updated", "https://jobs.test/1/", "two")

        class Source:
            def __init__(self, jobs):
                self.jobs = jobs

            def fetch(self):
                return self.jobs

        jobs = CompositeSource([Source([first]), Source([second])]).fetch()

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].source, "two")