"""A client's view of a daemon, on the standard library alone: find it, ask who it is, ask it to
stop and wait for its files to go. Shared by ``sq daemon`` and the remote client."""

import http.client
import json
import socket
import sys
import time

from squads._endpoint import DaemonRecord, Endpoint, read_record

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any

#: Seconds a client waits for a daemon to answer an identity or stop request.
ANSWER_TIMEOUT = 5.0


class UnixConnection(http.client.HTTPConnection):
    """An HTTP connection over the Unix socket at *path*."""

    def __init__(self, path: str, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self._path)
        except OSError:
            sock.close()
            raise
        self.sock = sock


def connection(
    endpoint: Endpoint, record: DaemonRecord | None, timeout: float = ANSWER_TIMEOUT
) -> http.client.HTTPConnection | None:
    """A connection to the daemon's CLI listener, or ``None`` when there is none to reach."""
    if endpoint.transport == "unix":
        if not endpoint.files.socket.exists():
            return None
        return UnixConnection(str(endpoint.files.socket), timeout)
    address = record.address("tcp", "cli") if record is not None else None
    if address is None:
        return None
    host, _, port = address.rpartition(":")
    return http.client.HTTPConnection(host, int(port), timeout=timeout)


def _call(
    endpoint: Endpoint, record: DaemonRecord | None, method: str, target: str
) -> dict[str, Any] | None:
    conn = connection(endpoint, record)
    if conn is None:
        return None
    headers = {"Content-Type": "application/json", "Squads-Client": "1"}
    try:
        conn.request(method, target, body=b"{}" if method != "GET" else None, headers=headers)
        reply = conn.getresponse()
        document: Any = json.loads(reply.read())
        return document if reply.status == 200 and isinstance(document, dict) else None  # pyright: ignore[reportUnknownVariableType]
    except OSError, http.client.HTTPException, ValueError:
        return None
    finally:
        conn.close()


def daemon_identity(endpoint: Endpoint) -> dict[str, Any] | None:
    """What ``GET /v1/daemon`` answers, or ``None`` when no daemon of this endpoint answers.
    Over a port, which an unrelated process may have reused, the pid and squad path must be the
    ones ``<key>.json`` records."""
    record = read_record(endpoint)
    identity = _call(endpoint, record, "GET", "/v1/daemon")
    if identity is None:
        return None
    if endpoint.identity_check == "pid-and-path" and (
        record is None
        or identity.get("pid") != record.pid
        or identity.get("squad_dir") != record.squad_dir
    ):
        return None
    return identity


def unanswering_daemon(endpoint: Endpoint) -> str | None:
    """Why a daemon that holds the lock cannot be asked anything, or ``None`` when nothing holds
    it (no daemon runs) or the daemon answers. Call it after :func:`daemon_identity` found none."""
    if lock_is_free(endpoint):
        return None
    record = read_record(endpoint)
    pid = f" (pid {record.pid})" if record is not None else ""
    return (
        f"a daemon{pid} holds {endpoint.files.lock} but does not answer; it may be starting, "
        "or it needs to be ended from outside"
    )


def ask_to_stop(endpoint: Endpoint) -> bool:
    """Ask the daemon to exit; whether it said it would."""
    return _call(endpoint, read_record(endpoint), "POST", "/v1/daemon/stop") is not None


def lock_is_free(endpoint: Endpoint) -> bool:
    """Whether no process holds the daemon's lock, so a daemon whose socket refuses connections is
    dead. A lock file nobody created is free. The probe takes the lock the way the daemon's
    ``filelock`` does (``flock`` on POSIX, a one-byte range lock on Windows), so the two see each
    other."""
    try:
        with endpoint.files.lock.open("rb") as held:
            return _take(held.fileno())
    except OSError:  # missing, or not one this user can open: nothing here to wait for
        return True


def _take(fd: int) -> bool:
    """Whether the exclusive lock of *fd* was free; closing *fd* gives it back."""
    if sys.platform == "win32":  # pragma: no cover
        import msvcrt

        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
        except OSError:
            return False
        return True
    import errno
    import fcntl

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        # contention, as ``filelock`` reads it: some filesystems report EACCES for a held lock
        return exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK)
    return True


def wait_until_gone(endpoint: Endpoint, seconds: float) -> bool:
    """Wait until the daemon's files are gone, or its lock is free and only its log remains (a
    crash leaves the log). Whether they went within *seconds*."""
    deadline = time.monotonic() + seconds
    while True:
        gone = not any(p.exists() for p in endpoint.files.all())
        if gone or (not endpoint.files.socket.exists() and lock_is_free(endpoint)):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)
