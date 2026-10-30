"""The client's probe of the daemon's lock reads the errors the daemon's lock library reads as
contention as a held lock: some filesystems answer a held lock with `EACCES`. No real filesystem
here does, so the system call is made to answer so."""

import errno
import sys

import pytest

from squads import _daemon_link as link
from squads._endpoint import endpoint_for
from squads._paths import SquadPaths


@pytest.mark.skipif(sys.platform == "win32", reason="the probe is flock on POSIX")
@pytest.mark.parametrize(
    ("code", "held"), [(errno.EACCES, True), (errno.EAGAIN, True), (errno.EIO, False)]
)
def test_a_lock_that_the_system_denies_is_held(
    project: SquadPaths, daemon_runtime, monkeypatch: pytest.MonkeyPatch, code: int, held: bool
) -> None:
    import fcntl

    endpoint = endpoint_for(project.root)
    assert endpoint is not None
    endpoint.runtime_dir.mkdir(parents=True)
    endpoint.files.lock.write_text("", encoding="utf-8")

    def refuse(fd: int, operation: int) -> None:
        raise OSError(code, "refused")

    monkeypatch.setattr(fcntl, "flock", refuse)

    assert link.lock_is_free(endpoint) is not held
