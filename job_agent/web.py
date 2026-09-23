from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .store import ApplicationStore


class ReviewHandler(SimpleHTTPRequestHandler):
    """Serve the dashboard and expose the review queue as a small local API."""

    store: ApplicationStore

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Return review data for API requests; otherwise serve frontend files."""
        if urlparse(self.path).path == "/api/reviews":
            self._send_json(self.store.list_reviews())
            return
        if urlparse(self.path).path == "/api/health":
            self._send_json({"status": "ok"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        """Approve a review item when the dashboard's button is pressed."""
        path = urlparse(self.path).path
        prefix = "/api/applications/"
        suffix = "/approve"
        if not (path.startswith(prefix) and path.endswith(suffix)):
            self._send_json({"error": "Not found"}, 404)
            return

        job_id = path[len(prefix) : -len(suffix)]
        if not self.store.approve(job_id):
            self._send_json({"error": "Review item not found"}, 404)
            return
        self._send_json({"job_id": job_id, "status": "approved"})


def main() -> None:
    """Start the local review dashboard server."""
    parser = argparse.ArgumentParser(description="Run the job application review dashboard")
    parser.add_argument("--db", default="job-agent.db")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    frontend = Path(__file__).resolve().parent.parent / "frontend"
    handler = lambda *handler_args: ReviewHandler(*handler_args, directory=str(frontend))
    ReviewHandler.store = ApplicationStore(args.db)
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
