# Job Application Agent

A human-in-the-loop MVP for discovering jobs, scoring resume fit, and queueing good matches for review.

## Run the first discovery pass

```bash
cd /home/navid/projects/job-application-agent
python3 -m job_agent.cli discover --resume resume.example.json --jobs jobs.example.json
python3 -m job_agent.cli review
python3 -m job_agent.cli approve acme-backend-001
```

The `--resume` option also accepts `.txt`, `.md`, `.pdf`, and `.docx` files. PDF and DOCX support is provided by the project dependencies.

Discovery can search public job feeds from Arbeitnow and Remotive without a company slug. It can also use company-specific feeds from Greenhouse, Lever, Ashby, SmartRecruiters, or Recruitee:

```bash
python3 -m job_agent.cli discover --resume resume.txt --greenhouse-board example-company
python3 -m job_agent.cli discover --resume resume.txt --lever-site example-company
python3 -m job_agent.cli discover --resume resume.txt --ashby-board example-company
python3 -m job_agent.cli discover --resume resume.txt --smartrecruiters-company example-company
python3 -m job_agent.cli discover --resume resume.txt --recruitee-company example-company
python3 -m job_agent.cli discover --resume resume.txt --arbeitnow --remotive
```

You can combine `--jobs`, `--greenhouse-board`, and `--lever-site`; duplicate listings are retained only once by job ID or URL.

Run discovery continuously with a 30-minute interval:

```bash
python3 -m job_agent.cli watch --resume resume.txt --jobs jobs.example.json --interval 1800
```

The dashboard supports search, source and score filters, listing details, saved tailoring drafts, approval, and rejection. Rejections can also be recorded from the CLI:

```bash
python3 -m job_agent.cli reject acme-backend-001
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

## Use the local coding agent

The repository includes a local Aider launcher that uses Ollama and does not require Copilot, Cline, or cloud API credits:

```bash
./local-agent.sh
```

You can pass files or a starting instruction directly:

```bash
./local-agent.sh job_agent/pipeline.py
```

The default model is `ollama/qwen2.5-coder:7b`. Set `AIDER_MODEL` to use another model already installed in Ollama.

Applications are stored in `job-agent.db` with status `review`. The browser submitter refuses to run unless a reviewer explicitly approves an application. Add compliant ATS/API sources through the `JobSource` protocol; avoid scraping or automating sites in ways that violate their terms.

The next integration points are:

- LLM-backed job extraction and resume/cover-letter tailoring.
- A review API or dashboard.
- Site-specific Playwright adapters after approval.
- A scheduler or worker process invoking `run_forever`.
