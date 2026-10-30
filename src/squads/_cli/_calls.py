"""How a command reaches its operation: the API an invocation selects, the call, and the
notices and omissions a response carries."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from squads import _spans as spans
from squads._api._api import Api, Operation
from squads._api._response import Response
from squads._cli import _common as common
from squads._context import get_context
from squads._endpoint import Endpoint


def local_api() -> Api:
    """The API that runs operations in this process; the one place the CLI reaches the service
    layer."""
    from squads._services._local_api import LocalApi

    return LocalApi(sources=common.invocation_sources)


#: Seconds a failed daemon start is not tried again within one invocation.
RETRY_AFTER = 30.0


class SelectedApi:
    """The API an invocation's commands call, chosen on the first call that needs one: the squad's
    daemon, found or started, or this process when there is no squad, the daemon is off or it
    could not be had (one line on stderr says why). A command that makes no call, or only a
    local-only one, never contacts a daemon."""

    def __init__(self, client_cwd: Path | None) -> None:
        self._client_cwd = client_cwd
        self._chosen: Api | None = None
        #: Whether this process answers because a daemon could not be had, rather than by choice.
        self._by_default = False
        #: When a daemon last failed to start, so the next try waits (``time.monotonic``).
        self._failed_at: float | None = None
        #: The lines already said, so a reason is said once per invocation.
        self._said: set[str] = set()

    def _say(self, line: str) -> None:
        if line not in self._said:
            self._said.add(line)
            common.err_console.print(common.e(line), soft_wrap=True)

    def _start(self, endpoint: Endpoint) -> bool:
        """Have a daemon of *endpoint* serve, starting one unless a start failed less than
        :data:`RETRY_AFTER` seconds ago; a failure is said once per reason."""
        import time

        from squads._daemon_start import ensure, failure_line

        if self._failed_at is not None and time.monotonic() - self._failed_at < RETRY_AFTER:
            return False
        reason = ensure(endpoint)
        if reason is None:
            self._failed_at = None
            return True
        self._failed_at = time.monotonic()
        self._say(failure_line(reason))
        return False

    def _usable(self, endpoint: Endpoint | None) -> bool:
        """Whether the squad's settings, read now, let a daemon be used; an unusable setting is
        said once."""
        if endpoint is None:
            return False
        if not endpoint.enabled:
            for problem in endpoint.problems:
                self._say(f"warning: {problem}")
        return endpoint.enabled

    def _restart(self) -> bool:
        """The daemon has gone (stopped, idle, retired): start it again under the settings as they
        are now, so a switch turned off meanwhile keeps it off."""
        from squads._endpoint import endpoint_for

        endpoint = endpoint_for(self._client_cwd or common.process_dir())
        return self._usable(endpoint) and endpoint is not None and self._start(endpoint)

    def reselect(self) -> None:
        """Forget a choice of this process that was made for want of a daemon, so the next call
        looks for one again: a long session does not stay local once a daemon can be started."""
        if self._by_default:
            self._chosen = None
            self._by_default = False

    @property
    def handler_ms(self) -> float | None:
        """The handler time the daemon reported for the last call, when it answered."""
        return getattr(self._chosen, "handler_ms", None)

    @property
    def declined(self) -> bool:
        """Whether the daemon declined the last call because its configuration changed."""
        return bool(getattr(self._chosen, "declined", False))

    def _choose(self) -> Api:
        from squads._endpoint import endpoint_for

        endpoint = endpoint_for(self._client_cwd or common.process_dir())
        if not self._usable(endpoint) or endpoint is None:
            return local_api()
        if not self._start(endpoint):
            self._by_default = True
            return local_api()
        from squads._cli._remote import build_http_api

        return build_http_api(endpoint, local=local_api, restart=self._restart)

    async def call[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        if op.local_only:
            return await local_api().call(op, req)
        if self._chosen is None:
            self._chosen = self._choose()
        return await self._chosen.call(op, req)

    def call_sync[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        """:meth:`call` without an event loop when the chosen API needs none."""
        if not op.local_only:
            if self._chosen is None:
                self._chosen = self._choose()
            sync = getattr(self._chosen, "call_sync", None)
            if sync is not None:
                return sync(op, req)
        import asyncio

        return asyncio.run(self.call(op, req))


def session_api(prior: Api | None, client_cwd: Path | None = None) -> Api:
    """The API the next call of a long session goes through: the invocation's, looking for a daemon
    again when the last choice was made for want of one."""
    api = invocation_api(prior, client_cwd)
    reselect = getattr(api, "reselect", None)
    if reselect is not None:
        reselect()
    return api


def select_api(client_cwd: Path | None = None) -> Api:
    """The API an invocation started in *client_cwd* calls."""
    return SelectedApi(client_cwd)


def invocation_api(prior: Api | None, client_cwd: Path | None = None) -> Api:
    """The API an invocation starts with: *prior* when the context it replaces already carries
    one (a harness hands the root callback its own), else the one selected."""
    return prior if prior is not None else select_api(client_cwd)


def call[Req: BaseModel, Res](op: Operation[Req, Res], req: Req) -> Response[Res]:
    """Make the one call a command makes, through the invocation's API."""
    api = get_context().api
    if api is None:
        api = select_api(get_context().client_cwd)
    with spans.span("api_call"):
        sync = getattr(api, "call_sync", None)
        if sync is not None:
            response = sync(op, req)
        else:
            import asyncio

            response = asyncio.run(api.call(op, req))
    handled = getattr(api, "handler_ms", None)
    if handled is not None:
        spans.value("handler", handled)
    spans.mark("call_done")
    return response


def print_warnings(response: Response[Any]) -> None:
    """Each warning of *response* on stderr, once per invocation."""
    common.print_notices(response.warnings)


def print_json(op: Operation[Any, Any], response: Response[Any]) -> None:
    """The one JSON document ``--json`` prints: ``data``, or the field of it *op* names. The
    response's warnings go to stderr first, so stdout holds the document alone."""
    print_warnings(response)
    data: BaseModel = response.data
    dumped = data.model_dump(mode="json")
    common.print_json_clean(json.dumps(dumped if op.json_field is None else dumped[op.json_field]))


def finish(response: Response[Any], *, json_out: bool) -> None:
    """Name what a partial read left out, then exit ``4``; nothing when it left nothing out."""
    common.report_omissions(list(response.omitted), json_out=json_out)
