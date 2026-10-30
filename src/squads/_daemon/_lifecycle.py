"""The daemon process: take the lock, bind, serve, retire on a changed configuration, exit idle.

``Daemon.run`` is the whole life of one daemon and returns its exit code. The start report is a
private protocol with whoever spawned it: one line on an inherited pipe, ``ready`` once the daemon
serves or ``error: <why>`` when it cannot, and then the pipe is closed.
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import sys
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import uvicorn
from filelock import FileLock, Timeout

import squads
from squads import _clock as clock
from squads._daemon._admission import Activity, Admission
from squads._daemon._app import build_app
from squads._daemon._listeners import Bound, bind_listeners
from squads._daemon._state import DaemonState
from squads._endpoint import CONFIG_FILENAME, Endpoint, runtime_dir_problem
from squads._errors import SquadsError
from squads._spec_documents import spec_sources

READY = "ready"
ALREADY_RUNNING = "already running"

_log = logging.getLogger("squads.daemon")
_LOGGED = ("squads.daemon", "uvicorn")

#: Reports one line to whoever started the daemon.
type Report = Callable[[str], None]


def pipe_report(fd: int) -> Report:
    """A reporter writing its first line to the inherited pipe *fd* and closing it; on native
    Windows *fd* is the inheritable handle's value."""
    state = {"open": True}

    def report(line: str) -> None:
        if not state["open"]:
            return
        state["open"] = False
        descriptor = fd
        if sys.platform == "win32":  # pragma: no cover
            import msvcrt

            descriptor = msvcrt.open_osfhandle(fd, os.O_WRONLY)  # pyright: ignore[reportUnknownMemberType]
        with contextlib.suppress(OSError):
            os.write(descriptor, f"{line}\n".encode())
        with contextlib.suppress(OSError):
            os.close(descriptor)

    return report


def fingerprint(root: Path, squad_dir: Path) -> str:
    """A digest of the daemon's configuration: the bytes of ``.squads.toml`` and the names and
    bytes of every file under ``<squad-dir>/.overrides/``. Bytes, not modification times, so a
    same-size edit within one timestamp tick is not missed."""
    digest = hashlib.sha256()

    def add(label: str, path: Path) -> None:
        try:
            content = path.read_bytes()
        except OSError:
            content = b"\0absent"
        digest.update(f"{len(label)}:{label}:{len(content)}:".encode())
        digest.update(content)

    add(CONFIG_FILENAME, root / CONFIG_FILENAME)
    overrides = squad_dir / ".overrides"
    if overrides.is_dir():
        for path in sorted(p for p in overrides.rglob("*") if p.is_file()):
            add(path.relative_to(overrides).as_posix(), path)
    return digest.hexdigest()


async def _finished(serving: asyncio.Task[None]) -> None:
    """Wait for the server task; uvicorn ends a start it cannot make with ``SystemExit``."""
    try:
        await serving
    except SystemExit:
        raise SquadsError("the server could not start") from None


class Daemon:
    """One daemon: the lock it holds, the listeners it serves and the files it keeps."""

    def __init__(self, endpoint: Endpoint, report: Report | None = None) -> None:
        self.endpoint = endpoint
        self._report = report
        self._server: uvicorn.Server | None = None
        self._stopping = False
        self._activity = Activity()
        #: Why the daemon did not start, once it has failed to.
        self.failure: str | None = None

    # --- the public surface ---

    def stop(self) -> None:
        """Ask the daemon to exit once the request in progress has finished. Safe from any
        thread."""
        self._stopping = True
        if self._server is not None:
            self._server.should_exit = True

    def run(self) -> int:
        """Serve until stopped, retired or idle; return the exit code (``1`` when the daemon
        could not start, ``0`` otherwise). Nothing is removed unless this call took the lock."""
        endpoint = self.endpoint
        problem = runtime_dir_problem(endpoint)
        if problem is not None:
            return self._fail(problem)
        lock = FileLock(
            str(endpoint.files.lock),
            thread_local=False,
            fallback_to_soft=False,
            preserve_lock_file=True,
        )
        try:
            lock.acquire(timeout=0)
        except Timeout:
            return self._fail(ALREADY_RUNNING)
        except OSError as exc:
            return self._fail(f"cannot take {endpoint.files.lock}: {exc.strerror}")
        try:
            return self._serve()
        finally:
            lock.release()
            with contextlib.suppress(OSError):
                endpoint.files.lock.unlink()

    # --- one life ---

    def _fail(self, reason: str) -> int:
        self.failure = reason
        if self._report is not None:
            self._report(f"error: {reason}")
        return 1

    def _serve(self) -> int:
        endpoint = self.endpoint
        handler = self._open_log()
        bound: Bound | None = None
        clean = False
        try:
            sources = spec_sources(endpoint.squad_dir)
            try:
                sources.workflow()
            except SquadsError as exc:
                return self._fail(f"cannot load the workflow vocabulary: {exc}")
            try:
                bound = bind_listeners(endpoint)
            except OSError as exc:
                return self._fail(f"cannot listen: {exc.strerror or exc}")
            started = clock.now()
            state = DaemonState(
                pid=os.getpid(),
                version=squads.__version__,
                root=endpoint.root,
                squad_dir=endpoint.squad_dir,
                started_at=started,
                sources=sources,
                listeners=list(bound.listeners),
            )
            state.stop = self.stop
            timeout = endpoint.settings.idle_timeout_minutes * 60
            state.idle_deadline = lambda: self._idle_deadline(timeout)
            start_print = fingerprint(endpoint.root, endpoint.squad_dir)
            app = Admission(
                build_app(
                    state,
                    lambda: fingerprint(endpoint.root, endpoint.squad_dir) != start_print,
                ),
                bound.ports,
                self._activity,
            )
            self._write_record(state)
            asyncio.run(self._serve_forever(app, bound, timeout))
        except Exception as exc:
            _log.exception("the daemon failed")
            return self._fail(f"{type(exc).__name__}: {exc}")
        else:
            clean = True
            return 0
        finally:
            if bound is not None:
                bound.close()
            for path in (endpoint.files.socket, endpoint.files.info):
                with contextlib.suppress(OSError):
                    path.unlink()
            self._close_log(handler, remove=clean)

    async def _serve_forever(self, app: Admission, bound: Bound, idle_seconds: int) -> None:
        config = uvicorn.Config(
            app,
            log_config=None,
            access_log=False,
            loop="asyncio",
            http="h11",
            ws="none",
            lifespan="off",
            interface="asgi3",
        )
        server = uvicorn.Server(config)
        self._server = server
        server.should_exit = self._stopping
        serving = asyncio.create_task(server.serve(sockets=list(bound.sockets)))
        # uvicorn offers no event for "started"
        while not server.started and not serving.done():  # noqa: ASYNC110
            await asyncio.sleep(0.01)
        if serving.done():
            await _finished(serving)
            raise SquadsError("the server stopped before it served")
        if self._report is not None:
            self._report(READY)
        watcher = asyncio.create_task(self._watch_idle(idle_seconds))
        try:
            await _finished(serving)
        finally:
            watcher.cancel()

    async def _watch_idle(self, idle_seconds: int) -> None:
        """Stop the server once nothing has asked it anything for *idle_seconds* (``0``: never)."""
        if idle_seconds <= 0:
            return
        while True:
            idle = self._activity.idle_seconds()
            remaining = idle_seconds if idle is None else idle_seconds - idle
            if remaining <= 0:
                self.stop()
                return
            await asyncio.sleep(min(max(remaining, 0.05), 5.0))

    def _idle_deadline(self, idle_seconds: int) -> datetime | None:
        if idle_seconds <= 0:
            return None
        idle = self._activity.idle_seconds() or 0.0
        return clock.now() + timedelta(seconds=max(idle_seconds - idle, 0.0))

    # --- files ---

    def _write_record(self, state: DaemonState) -> None:
        """``<key>.json``, replaced whole so a reader never sees half of it."""
        record = {
            "pid": state.pid,
            "version": state.version,
            "squad_dir": str(state.squad_dir),
            "started_at": state.started_at.isoformat(),
            "listeners": [
                {"transport": ln.transport, "address": ln.address, "kind": ln.kind}
                for ln in state.listeners
            ],
        }
        path = self.endpoint.files.info
        temporary = path.with_name(f"{path.name}.tmp")
        temporary.write_text(json.dumps(record), encoding="utf-8")
        Path(temporary).replace(path)

    def _open_log(self) -> logging.Handler:
        """The daemon's own log for this lifetime, replacing a crashed predecessor's."""
        handler = logging.FileHandler(self.endpoint.files.log, mode="w", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        for name in _LOGGED:
            target = logging.getLogger(name)
            target.addHandler(handler)
            target.setLevel(logging.INFO)
        return handler

    def _close_log(self, handler: logging.Handler, *, remove: bool) -> None:
        for name in _LOGGED:
            logging.getLogger(name).removeHandler(handler)
        handler.close()
        if remove:
            with contextlib.suppress(OSError):
                self.endpoint.files.log.unlink()


def run_daemon(endpoint: Endpoint, report_fd: int | None = None) -> tuple[int, str | None]:
    """Run the daemon of *endpoint* in this process until it exits. Returns the exit code and,
    when it did not start, why. *report_fd* is the pipe the start report goes to, if any."""
    daemon = Daemon(endpoint, pipe_report(report_fd) if report_fd is not None else None)
    return daemon.run(), daemon.failure
