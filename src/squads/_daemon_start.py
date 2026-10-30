"""Finding a squad's daemon, or starting one, on the standard library alone.

``ensure`` is what a command that wants the daemon calls first: it returns ``None`` once a daemon of
the endpoint's key answers, and otherwise the reason one could not be had, for the caller to print
as one line before it runs locally. A daemon whose socket refuses connections while its lock is free
is dead, and its files are removed.
"""

import contextlib
import os
import subprocess
import sys
import threading
import time

from squads._daemon_link import daemon_identity, lock_is_free
from squads._endpoint import Endpoint, runtime_dir_problem

#: Seconds a client waits for a spawned daemon to say it serves.
START_WAIT = 5.0

#: The start report of a daemon that lost the race for the lock: another one serves.
_ALREADY_RUNNING = "error: already running"

_WINDOWS_FLAGS = (
    getattr(subprocess, "DETACHED_PROCESS", 0)
    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    | getattr(subprocess, "CREATE_NO_WINDOW", 0)
)


def failure_line(reason: str) -> str:
    """The one line a command prints on stderr when it runs locally for want of a daemon."""
    return (
        f"warning: the daemon could not be used ({reason}); running locally. "
        "Set SQUADS_DAEMON=off or `enabled = false` under [daemon] in .squads.toml to stop trying."
    )


def discard_stale(endpoint: Endpoint) -> None:
    """Remove the socket and record of a daemon that is gone: nothing answers and the lock is
    free. A daemon still starting holds the lock, so its files stay."""
    if daemon_identity(endpoint) is not None or not lock_is_free(endpoint):
        return
    for path in (endpoint.files.socket, endpoint.files.info):
        with contextlib.suppress(OSError):
            path.unlink()


def _spawn(endpoint: Endpoint) -> tuple[subprocess.Popen[bytes], int]:
    """Start ``sq daemon run`` for the endpoint, detached from this terminal; returns the process
    and the read end of the pipe it reports on."""
    read, write = os.pipe()
    argument = str(write)
    command = [sys.executable, "-m", "squads", "-C", str(endpoint.root), "daemon", "run"]
    devnull = subprocess.DEVNULL
    try:
        if sys.platform == "win32":  # pragma: no cover
            import msvcrt

            handle = msvcrt.get_osfhandle(write)  # pyright: ignore[reportUnknownMemberType]
            os.set_handle_inheritable(handle, True)
            argument = str(handle)
            startup = subprocess.STARTUPINFO(lpAttributeList={"handle_list": [handle]})  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
            process = subprocess.Popen(
                [*command, "--report-fd", argument],
                stdin=devnull,
                stdout=devnull,
                stderr=devnull,
                creationflags=_WINDOWS_FLAGS,
                startupinfo=startup,
            )
        else:
            process = subprocess.Popen(
                [*command, "--report-fd", argument],
                stdin=devnull,
                stdout=devnull,
                stderr=devnull,
                pass_fds=(write,),
                start_new_session=True,
            )
    except OSError:
        os.close(read)
        raise
    finally:
        os.close(write)
    return process, read


def _first_line(read: int, seconds: float) -> str | None:
    """The first line the child reports, ``""`` when it closes the pipe without one, ``None`` when
    *seconds* pass first."""
    lines: list[str] = []

    def reader() -> None:
        with os.fdopen(read, "rb") as pipe:
            lines.append(pipe.readline().decode(errors="replace").strip())

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    thread.join(seconds)
    return lines[0] if lines else None


def _wait_for_identity(endpoint: Endpoint, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if daemon_identity(endpoint) is not None:
            return True
        time.sleep(0.05)
    return daemon_identity(endpoint) is not None


def ensure(endpoint: Endpoint, wait: float = START_WAIT) -> str | None:
    """Make sure a daemon of the endpoint's key serves, starting one if none does.

    Returns ``None`` when one answers, otherwise why none could be had: a spawn error, the failure
    line the child reported, an unusable runtime directory, or no answer within *wait* seconds.
    """
    if daemon_identity(endpoint) is not None:
        return None
    problem = runtime_dir_problem(endpoint)
    if problem is not None:
        return problem
    discard_stale(endpoint)
    try:
        process, read = _spawn(endpoint)
    except OSError as exc:
        return f"cannot start the daemon: {exc.strerror or exc}"
    return _outcome(endpoint, _first_line(read, wait), process, wait)


def _outcome(
    endpoint: Endpoint, line: str | None, process: subprocess.Popen[bytes], wait: float
) -> str | None:
    """``None`` when what the child reported means a daemon serves, else the reason."""
    if line in ("ready", _ALREADY_RUNNING):
        return None if _wait_for_identity(endpoint, wait) else "the daemon did not answer"
    if line is None:
        return f"no answer within {wait:g} seconds"
    if line.startswith("error: "):
        return line.removeprefix("error: ")
    return f"the daemon exited without reporting (exit {process.poll()})"
