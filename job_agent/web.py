from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .domain import ApplicationStatus
from .pipeline import discover_once
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


class ReviewHandler(SimpleHTTPRequestHandler):
    """Serve the dashboard and expose the review queue as a small local API."""

    store: ApplicationStore
    resume_path: str

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Return review data for API requests; otherwise serve frontend files."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/reviews":
            status = parse_qs(parsed.query).get("status", [ApplicationStatus.REVIEW.value])[0]
            self._send_json(self.store.list_applications(status))
            return
        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        """Run discovery or change a review item's status."""
        path = urlparse(self.path).path
        if path == "/api/discover":
            length = int(self.headers.get("Content-Length", "0"))
            try:
                request = json.loads(self.rfile.read(length) or b"{}")
                source = self._source_from_request(request)
                applications = discover_once(load_resume(self.resume_path), source, self.store)
            except (ValueError, KeyError, OSError, RuntimeError) as error:
                self._send_json({"error": str(error)}, 400)
                return
            self._send_json({"count": len(applications), "applications": self.store.list_reviews()})
            return

        prefix = "/api/applications/"
        suffix = "/approve"
        if not (path.startswith(prefix) and path.endswith(suffix)):
            reject_suffix = "/reject"
            if path.startswith(prefix) and path.endswith(reject_suffix):
                job_id = path[len(prefix) : -len(reject_suffix)]
                if not self.store.reject(job_id):
                    self._send_json({"error": "Review item not found"}, 404)
                    return
                self._send_json({"job_id": job_id, "status": "rejected"})
                return
            self._send_json({"error": "Not found"}, 404)
            return

        job_id = path[len(prefix) : -len(suffix)]
        if not self.store.approve(job_id):
            self._send_json({"error": "Review item not found"}, 404)
            return
        self._send_json({"job_id": job_id, "status": "approved"})

    def _source_from_request(self, request: dict):
        source_name = request.get("source", "greenhouse")
        if source_name == "greenhouse":
            board = request.get("board", "").strip()
            if not board:
                raise ValueError("Enter a Greenhouse board slug")
            return GreenhouseJobSource(board)
        if source_name == "lever":
            site = request.get("site", "").strip()
            if not site:
                raise ValueError("Enter a Lever site slug")
            return LeverJobSource(site)
        if source_name == "json":
            path = request.get("path", "").strip()
            if not path:
                raise ValueError("Enter a local JSON jobs path")
            return JsonJobSource(path)
        if source_name == "ashby":
            board = request.get("board", "").strip()
            if not board:
                raise ValueError("Enter an Ashby board slug")
            return AshbyJobSource(board)
        if source_name == "smartrecruiters":
            company = request.get("company", "").strip()
            if not company:
                raise ValueError("Enter a SmartRecruiters company identifier")
            return SmartRecruitersJobSource(company)
        if source_name == "recruitee":
            company = request.get("company", "").strip()
            if not company:
                raise ValueError("Enter a Recruitee company slug")
            return RecruiteeJobSource(company)
        if source_name == "arbeitnow":
            return ArbeitnowJobSource()
        if source_name == "remotive":
            return RemotiveJobSource()
        if source_name == "all-public":
            return CompositeSource([ArbeitnowJobSource(), RemotiveJobSource()])
        raise ValueError("Unsupported job source")


def main() -> None:
    """Start the local review dashboard server."""
    parser = argparse.ArgumentParser(description="Run the job application review dashboard")
    parser.add_argument("--db", default="job-agent.db")
    parser.add_argument("--resume", default="resume.example.json")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    frontend = Path(__file__).resolve().parent.parent / "frontend"
    handler = lambda *handler_args: ReviewHandler(*handler_args, directory=str(frontend))
    ReviewHandler.store = ApplicationStore(args.db)
    ReviewHandler.resume_path = args.resume
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Review dashboard: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
