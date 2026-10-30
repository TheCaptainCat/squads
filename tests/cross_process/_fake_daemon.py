"""A stand-in for a daemon, on the socket a client looks for: it answers who it is and does
something else with every other request."""

import json
import socket
import threading
from pathlib import Path


class SilentDaemon:
    """Answers who it is; a daemon that took any other request holds it and never replies, or, with
    *hang_up*, closes the connection at once. ``requests`` counts the other requests."""

    IDENTITY = json.dumps({"pid": 1, "squad_dir": "x"}).encode()

    def __init__(self, path: Path, *, hang_up: bool = False) -> None:
        self.hang_up = hang_up
        self.requests = 0
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(str(path))
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
                    % (len(self.IDENTITY), self.IDENTITY)
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
