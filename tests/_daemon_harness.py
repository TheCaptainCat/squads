"""Serve a squad's daemon application on a thread of the test process, and call it as a client.

The application is served by uvicorn on a loopback socket the harness binds, exactly as the daemon
serves its own. A call goes through `http.client`, so a test asserts the whole response and reads
state back through the CLI. The thread shares the test process's environment, working directory and
streams; the application reads none of them for a value a request carries.
"""

import http.client
import json
import os
import socket
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import uvicorn
from typer._click import Command

from squads._daemon._app import build_app
from squads._daemon._state import DaemonState, RetirementCheck, never_retiring
from squads._paths import SquadPaths
from squads._spec_documents import spec_sources
from tests._squads import FROZEN

#: Sent with every call unless a test overrides it, so a write is stamped with the frozen clock.
DEFAULT_HEADERS = {"Squads-At": FROZEN.isoformat()}


@dataclass(frozen=True)
class Reply:
    """A whole response: its status, its headers (names lowercased) and its body."""

    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


@dataclass
class Served:
    """A daemon application being served: where it listens and how to call it."""

    host: str
    port: int
    state: DaemonState

    def request(
        self,
        method: str,
        target: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        *,
        raw_body: bytes | None = None,
    ) -> Reply:
        """Call the application and return the whole response."""
        sent = {**DEFAULT_HEADERS, **(headers or {})}
        payload = raw_body
        if method != "GET":
            sent.setdefault("Content-Type", "application/json")
            sent.setdefault("Squads-Client", "1")
            if payload is None:
                payload = json.dumps(body or {}).encode()
        conn = http.client.HTTPConnection(self.host, self.port, timeout=60)
        try:
            conn.request(method, target, body=payload, headers=sent)
            response = conn.getresponse()
            return Reply(
                response.status,
                {k.lower(): v for k, v in response.getheaders()},
                response.read(),
            )
        finally:
            conn.close()

    def get(self, target: str, headers: dict[str, str] | None = None) -> Reply:
        return self.request("GET", target, headers=headers)


def new_state(paths: SquadPaths) -> DaemonState:
    """The identity of a daemon serving the squad at *paths*."""
    return DaemonState(
        pid=os.getpid(),
        version="test",
        root=paths.root,
        squad_dir=paths.squad_dir.resolve(),
        started_at=datetime.now(UTC),
        sources=spec_sources(paths.squad_dir),
    )


@contextmanager
def serve_squad(
    paths: SquadPaths,
    *,
    retirement_check: RetirementCheck = never_retiring,
    command: Command | None = None,
    clock: Callable[[], datetime | None] = lambda: None,
) -> Generator[Served]:
    """Serve the squad at *paths* until the block ends. *command* is the command tree the
    endpoint serves in place of the CLI's, and *clock* the time its commands run on."""
    state = new_state(paths)
    app = build_app(state, retirement_check, command=command, clock=clock)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    config = uvicorn.Config(
        app, log_level="warning", access_log=False, loop="asyncio", http="h11", lifespan="off"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = 100
        while not server.started and deadline:
            threading.Event().wait(0.05)
            deadline -= 1
        assert server.started, "the application did not start"
        yield Served(host, port, state)
    finally:
        server.should_exit = True
        thread.join(timeout=30)
        sock.close()
