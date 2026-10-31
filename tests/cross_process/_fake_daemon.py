"""A stand-in for a daemon, on the socket a client looks for: it answers who it is and does
something else with every other request."""

import json
import os
import socket
import threading

from squads._endpoint import Endpoint


class SilentDaemon:
    """Answers who it is; a daemon that took any other request holds it and never replies, or, with
    *hang_up*, closes the connection at once. ``requests`` counts the other requests."""

    def __init__(self, endpoint: Endpoint, *, hang_up: bool = False) -> None:
        """Listen where a client looks for the daemon of *endpoint*: its Unix socket, or, where
        the client reaches a loopback port, a port its record file lists."""
        self.hang_up = hang_up
        self.requests = 0
        self.identity = json.dumps(
            {"pid": os.getpid(), "squad_dir": str(endpoint.squad_dir)}
        ).encode()
        if endpoint.transport == "unix":
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.bind(str(endpoint.files.socket))
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(("127.0.0.1", 0))
            port = self.sock.getsockname()[1]
            endpoint.files.info.write_text(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "version": "fake",
                        "squad_dir": str(endpoint.squad_dir),
                        "listeners": [
                            {"transport": "tcp", "address": f"127.0.0.1:{port}", "kind": "cli"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
        self.sock.listen(8)
        self.received = threading.Event()
        self.held: list[socket.socket] = []
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            head = conn.recv(4096)
            if head.startswith(b"GET /v1/daemon "):
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                    b"Connection: close\r\nContent-Length: %d\r\n\r\n%s"
                    % (len(self.identity), self.identity)
                )
                conn.close()
            else:
                self.requests += 1
                if self.hang_up:
                    conn.close()
                else:
                    self.held.append(conn)
                self.received.set()

    def close(self) -> None:
        self.sock.close()
        for conn in self.held:
            conn.close()
