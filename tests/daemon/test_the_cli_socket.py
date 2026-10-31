"""On POSIX the CLI reaches the daemon through a socket only its owner can use, in a directory only
its owner can enter."""

import stat
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Windows has no Unix socket")


def test_the_socket_and_its_directory_belong_to_their_owner_alone(project, run_daemon) -> None:
    running = run_daemon(project)

    socket_mode = stat.S_IMODE(running.endpoint.files.socket.stat().st_mode)
    directory_mode = stat.S_IMODE(running.endpoint.runtime_dir.stat().st_mode)

    assert (oct(socket_mode), oct(directory_mode)) == ("0o600", "0o700")
