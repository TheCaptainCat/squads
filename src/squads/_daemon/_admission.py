"""Admission: the rules a request meets before routing, decided by the listener it arrived on.

One ASGI middleware ahead of the application. It sends no CORS header and answers no preflight.
"""

import time
from collections.abc import Mapping
from typing import Any

from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from squads import _clock as clock
from squads._api._errors import FORBIDDEN, HTTP_STATUS, MISDIRECTED, ErrorBody, ErrorDetail

CLI = "cli"
BROWSER = "browser"

#: Where the CLI of this installation sends a command line; the browser listener has no such route.
COMMANDS_PATH = "/v1/commands"

#: The header every non-``GET`` request carries, which a cross-origin page cannot send without a
#: preflight that fails.
CLIENT_HEADER = b"squads-client"


class Activity:
    """What the daemon has been doing: the requests in progress and when the last one ended."""

    def __init__(self) -> None:
        self.in_flight = 0
        self._last = time.monotonic()
        #: When the last request ended (or the daemon started), for the deadline it reports.
        self.last_at = clock.now()

    def begin(self) -> None:
        self.in_flight += 1

    def end(self) -> None:
        self.in_flight -= 1
        self._last = time.monotonic()
        self.last_at = clock.now()

    def idle_seconds(self) -> float | None:
        """Seconds since the last request ended; ``None`` while one is in progress."""
        return None if self.in_flight else time.monotonic() - self._last


def _refusal(kind: str, message: str) -> Response:
    body = ErrorBody(error=ErrorDetail(type=kind, message=message))
    return Response(
        body.model_dump_json(exclude_none=True).encode(),
        status_code=dict(HTTP_STATUS)[kind],
        media_type="application/json",
    )


def _headers(scope: Scope) -> dict[bytes, bytes]:
    """The request's headers by lowercased name; the first of a repeated one."""
    found: dict[bytes, bytes] = {}
    for name, value in scope["headers"]:
        found.setdefault(name.lower(), value)
    return found


def _write_refusal(headers: dict[bytes, bytes]) -> Response | None:
    """The answer refusing a write that lacks the headers a cross-origin page cannot send."""
    if not _is_json(headers.get(b"content-type")):
        return _refusal(FORBIDDEN, "a write needs Content-Type: application/json")
    if headers.get(CLIENT_HEADER) != b"1":
        return _refusal(FORBIDDEN, "a write needs the header Squads-Client: 1")
    return None


def _is_json(content_type: bytes | None) -> bool:
    if content_type is None:
        return False
    return content_type.split(b";", 1)[0].strip().lower() == b"application/json"


class Admission:
    """Wraps *app*. *tcp_ports* maps the port of each TCP listener to its kind (``cli`` or
    ``browser``); a connection that arrived on the Unix socket carries no port."""

    def __init__(self, app: ASGIApp, tcp_ports: Mapping[int, str], activity: Activity) -> None:
        self._app = app
        self._ports = dict(tcp_ports)
        self._activity = activity

    def refusal(self, scope: Scope) -> Response | None:
        """The answer refusing the request, or ``None`` when it may be routed."""
        headers = _headers(scope)
        server: Any = scope.get("server")
        port: object = server[1] if server and len(server) == 2 else None
        method: str = scope["method"]
        origin = headers.get(b"origin")
        if isinstance(port, int):
            kind = self._ports.get(port)
            host = headers.get(b"host", b"").decode("latin-1").lower()
            if kind is None or host not in (
                f"127.0.0.1:{port}",
                f"localhost:{port}",
                f"[::1]:{port}",
            ):
                return _refusal(MISDIRECTED, "the Host header does not name this listener")
            if kind == BROWSER and scope["path"] == COMMANDS_PATH:
                return _refusal("not_found", "no such route")
            if kind == CLI and origin is not None:
                return _refusal(FORBIDDEN, "this listener refuses a request that has an Origin")
            if (
                kind == BROWSER
                and method not in ("GET", "HEAD")
                and (origin is None or origin.decode("latin-1").lower() != f"http://{host}")
            ):
                return _refusal(FORBIDDEN, "a write needs an Origin equal to this listener's")
        if isinstance(port, int) and method not in ("GET", "HEAD"):
            return _write_refusal(headers)
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._app(scope, receive, send)
            return
        if scope["type"] != "http":
            await send({"type": "websocket.close", "code": 1008})
            return
        refused = self.refusal(scope)
        if refused is not None:
            await refused(scope, receive, send)
            return
        self._activity.begin()
        try:
            await self._app(scope, receive, send)
        finally:
            self._activity.end()
