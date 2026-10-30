"""The sockets the daemon binds itself: the Unix socket of the CLI on POSIX, the loopback CLI port
on native Windows, and the browser listener when it is enabled."""

import contextlib
import pathlib
import socket
from dataclasses import dataclass, field

from squads._daemon._admission import BROWSER, CLI
from squads._daemon._state import Listener
from squads._endpoint import Endpoint

LOOPBACK = "127.0.0.1"
LOOPBACK_V6 = "::1"


@dataclass
class Bound:
    """The sockets bound, the listeners they make and the kind each TCP port serves."""

    sockets: list[socket.socket] = field(default_factory=list[socket.socket])
    listeners: list[Listener] = field(default_factory=list[Listener])
    ports: dict[int, str] = field(default_factory=dict[int, str])

    def close(self) -> None:
        for sock in self.sockets:
            with contextlib.suppress(OSError):
                sock.close()
        self.sockets.clear()


def _bind_unix(path: str) -> socket.socket:
    """A listening Unix socket at *path*, readable and writable by its owner only. The caller
    holds the daemon's lock, so whatever file is there is a dead daemon's."""
    with contextlib.suppress(FileNotFoundError):
        pathlib.Path(path).unlink()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(path)
        pathlib.Path(path).chmod(0o600)
        sock.listen(128)
    except OSError:
        sock.close()
        raise
    sock.setblocking(False)
    return sock


def _bind_loopback(family: socket.AddressFamily, host: str, port: int) -> socket.socket:
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.listen(128)
    except OSError:
        sock.close()
        raise
    sock.setblocking(False)
    return sock


def _add_tcp(bound: Bound, kind: str, *, ipv6: bool) -> None:
    """Bind a loopback port for *kind* and, when *ipv6*, the same port on ``::1`` if this host
    can; never an address that is not loopback."""
    first = _bind_loopback(socket.AF_INET, LOOPBACK, 0)
    port: int = first.getsockname()[1]
    bound.sockets.append(first)
    bound.listeners.append(Listener("tcp", f"{LOOPBACK}:{port}", kind))
    bound.ports[port] = kind
    if ipv6 and socket.has_ipv6:
        try:
            second = _bind_loopback(socket.AF_INET6, LOOPBACK_V6, port)
        except OSError:
            return
        bound.sockets.append(second)
        bound.listeners.append(Listener("tcp", f"[{LOOPBACK_V6}]:{port}", kind))


def bind_listeners(endpoint: Endpoint) -> Bound:
    """Bind every listener the endpoint's settings call for. On failure nothing stays bound."""
    bound = Bound()
    try:
        if endpoint.transport == "unix":
            path = str(endpoint.files.socket)
            bound.sockets.append(_bind_unix(path))
            bound.listeners.append(Listener("unix", path, CLI))
        else:
            _add_tcp(bound, CLI, ipv6=False)
        if endpoint.settings.browser:
            _add_tcp(bound, BROWSER, ipv6=True)
    except OSError:
        bound.close()
        raise
    return bound
