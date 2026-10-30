"""Run a squad's daemon, lifecycle and listeners included, on a thread of the test process.

Unlike `tests/_daemon_harness.py`, which serves the bare application, this runs `Daemon` itself: it
takes the lock, binds the CLI listener (and the browser one when the squad's settings ask for it),
writes its record in a runtime directory the test owns and removes its files when it stops. A test
reaches it as a client does, through the endpoint resolution and the daemon's own connection helper.
"""

import http.client
import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from squads._daemon._lifecycle import Daemon
from squads._daemon_link import connection, daemon_identity
from squads._endpoint import Endpoint, endpoint_for, read_record
from squads._paths import SquadPaths


@dataclass
class Running:
    """A daemon being served on a thread: its endpoint, the daemon and the thread."""

    endpoint: Endpoint
    daemon: Daemon
    thread: threading.Thread

    def identity(self) -> dict[str, Any]:
        found = daemon_identity(self.endpoint)
        assert found is not None, "the daemon does not answer"
        return found

    def listener(self, kind: str) -> tuple[str, int]:
        """The loopback host and port of the TCP listener serving *kind*."""
        record = read_record(self.endpoint)
        assert record is not None
        address = record.address("tcp", kind)
        assert address is not None, f"no {kind} listener over TCP"
        host, _, port = address.rpartition(":")
        return host, int(port)

    def get_over_cli(
        self, target: str, method: str = "GET", body: dict[str, Any] | None = None
    ) -> tuple[int, bytes]:
        """One request on the CLI listener, whichever transport that is; a write carries *body*,
        an empty object by default."""
        conn = connection(self.endpoint, read_record(self.endpoint))
        assert conn is not None
        try:
            payload = json.dumps(body or {}) if method != "GET" else None
            conn.request(
                method,
                target,
                body=payload,
                headers={"Content-Type": "application/json", "Squads-Client": "1"},
            )
            reply = conn.getresponse()
            return reply.status, reply.read()
        finally:
            conn.close()

    def over_tcp(
        self,
        kind: str,
        method: str,
        target: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        """One request on a TCP listener with exactly the headers given (a `Host` of its own
        included); its status, headers (names lowercased) and body."""
        host, port = self.listener(kind)
        conn = http.client.HTTPConnection(host, port, timeout=30)
        try:
            conn.request(method, target, body=body, headers=headers or {})
            reply = conn.getresponse()
            return reply.status, {k.lower(): v for k, v in reply.getheaders()}, reply.read()
        finally:
            conn.close()

    def stop(self) -> None:
        self.daemon.stop()
        self.thread.join(timeout=30)

    def wait_until_exited(self) -> None:
        self.thread.join(timeout=30)
        assert not self.thread.is_alive(), "the daemon did not exit"


@contextmanager
def running_daemon(paths: SquadPaths) -> Generator[Running]:
    """Run the daemon of the squad at *paths* until the block ends."""
    endpoint = endpoint_for(paths.root)
    assert endpoint is not None
    started = threading.Event()
    lines: list[str] = []

    def report(line: str) -> None:
        lines.append(line)
        started.set()

    daemon = Daemon(endpoint, report)
    thread = threading.Thread(target=daemon.run, daemon=True)
    thread.start()
    assert started.wait(30), "the daemon reported nothing"
    assert lines[0] == "ready", lines
    running = Running(endpoint, daemon, thread)
    try:
        yield running
    finally:
        running.stop()


def enable_browser(paths: SquadPaths) -> None:
    """Switch the browser listener on in the squad's `.squads.toml`."""
    config = paths.config_path
    config.write_text(
        config.read_text(encoding="utf-8") + "\n[daemon]\nbrowser = true\n", encoding="utf-8"
    )
