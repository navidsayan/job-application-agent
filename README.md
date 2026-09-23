# Job Application Agent

A human-in-the-loop MVP for discovering jobs, scoring resume fit, and queueing good matches for review.

## Run the first discovery pass

```bash
cd /home/navid/projects/job-application-agent
python3 -m job_agent.cli discover --resume resume.example.json --jobs jobs.example.json
python3 -m job_agent.cli review
python3 -m job_agent.cli approve acme-backend-001
```

Generate local AI drafts for a reviewed job with Ollama:

```bash
python3 -m job_agent.cli tailor acme-backend-001 \
	--resume resume.example.json \
	--jobs jobs.example.json
```

This uses the local `qwen2.5-coder:7b` model by default and saves a factual resume focus and cover-letter draft to the review record. It does not submit applications.

## Open the review dashboard

```bash
python3 -m job_agent.web --db job-agent.db --port 8765
```

Then open http://127.0.0.1:8765. The dashboard shows queued matches, scores, matching reasons, and an explicit approval action.

Applications are stored in `job-agent.db` with status `review`. The browser submitter refuses to run unless a reviewer explicitly approves an application. Add compliant ATS/API sources through the `JobSource` protocol; avoid scraping or automating sites in ways that violate their terms.

The next integration points are:

- LLM-backed job extraction and resume/cover-letter tailoring.
- A review API or dashboard.
- Site-specific Playwright adapters after approval.
- A scheduler or worker process invoking `run_forever`.
