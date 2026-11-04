"""A loopback HTTP server that answers with recorded tracker responses.

A source's ``base_url`` names the server's address, so a case runs the real command, the real
connector and the real HTTP path while no request leaves the machine.
"""

import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qsl, urlsplit

FIXTURES = Path(__file__).parent / "fixtures" / "sources"


def _matches(route: dict[str, Any], path: str, query: dict[str, str]) -> bool:
    wanted = cast("dict[str, str]", route.get("query", {}))
    return route["path"] == path and all(query.get(k) == v for k, v in wanted.items())


class Tracker:
    """The recorded routes, and the requests the server received."""

    def __init__(self, routes: list[dict[str, Any]]) -> None:
        self.routes = routes
        self.requests: list[tuple[str, dict[str, str], dict[str, str]]] = []
        self.base_url = ""

    def answer(
        self, path: str, query: dict[str, str], headers: dict[str, str]
    ) -> tuple[int, dict[str, str], object]:
        """The status, headers and JSON body of the first route matching the request."""
        self.requests.append((path, query, headers))
        for route in self.routes:
            if _matches(route, path, query):
                return route.get("status", 200), route.get("headers", {}), route.get("body")
        return 404, {}, {"message": "404 Not found"}


def load_routes(name: str) -> list[dict[str, Any]]:
    """The recorded routes of fixture file *name* under ``tests/fixtures/sources``."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["routes"]


@contextmanager
def serve(routes: list[dict[str, Any]]) -> Generator[Tracker]:
    """Serve *routes* on a free loopback port until the block ends."""
    tracker = Tracker(routes)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parts = urlsplit(self.path)
            query = dict(parse_qsl(parts.query))
            status, headers, body = tracker.answer(parts.path, query, dict(self.headers.items()))
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            """Keep the test output quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    tracker.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield tracker
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
