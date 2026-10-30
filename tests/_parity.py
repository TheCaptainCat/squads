"""The remote mode of the surface suite: each operation a case calls goes over HTTP to the daemon's
application, served on a thread of the test process against the case's squad. The squad's
application is started again when its configuration changes, and a call that would fall back to
local mode fails the case instead."""

import http.client
from contextlib import ExitStack
from pathlib import Path

from pydantic import BaseModel

from squads._api._api import Operation
from squads._api._client import HttpApi
from squads._api._response import Response
from squads._cli import _calls as calls
from squads._cli._remote import context_headers
from squads._context import get_context
from squads._daemon._lifecycle import fingerprint
from squads._endpoint import Endpoint, endpoint_for
from squads._paths import resolve
from squads._spec_documents import spec_sources
from tests._daemon_harness import Served, serve_squad


class ParityApi:
    """Sends each operation of a case over HTTP, to the application serving its squad."""

    def __init__(self) -> None:
        self._served: dict[Path, tuple[str, Served, ExitStack]] = {}

    def close(self) -> None:
        for _, _, stack in self._served.values():
            stack.close()
        self._served.clear()

    def _application(self, endpoint: Endpoint) -> Served:
        """The application serving *endpoint*'s squad on its current configuration."""
        current = fingerprint(endpoint.root, endpoint.squad_dir)
        held = self._served.get(endpoint.root)
        if held is not None and held[0] == current:
            return held[1]
        if held is not None:
            held[2].close()
        stack = ExitStack()
        served = stack.enter_context(serve_squad(resolve(client_cwd=endpoint.root)))
        self._served[endpoint.root] = (current, served, stack)
        return served

    async def call[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        ctx = get_context()
        endpoint = endpoint_for(ctx.client_cwd or Path.cwd(), environ={}, version="test")
        local = calls.local_api()
        if endpoint is None or op.local_only:
            return await local.call(op, req)
        served = self._application(endpoint)

        def connect(timeout: float) -> http.client.HTTPConnection:
            return http.client.HTTPConnection(served.host, served.port, timeout=timeout)

        api = HttpApi(
            connect=connect,
            endpoint=f"{served.host}:{served.port}",
            headers=context_headers,
            vocabulary=lambda: spec_sources(endpoint.squad_dir).vocabulary(),
            package_version="test",
            local=None,
        )
        return await api.call(op, req)
