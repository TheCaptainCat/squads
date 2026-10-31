"""The CLI's client of the daemon: the headers an invocation sends, the connection to the daemon
its endpoint names and the ``HttpApi`` built from them."""

import http.client
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

import squads
from squads._api._api import Api, Operation
from squads._api._client import Connect, HttpApi
from squads._api._http import (
    ACTOR_HEADER,
    AT_HEADER,
    CLIENT_DIR_HEADER,
    PARENT_SESSION_HEADER,
    SESSION_HEADER,
)
from squads._api._response import Response
from squads._api._vocabulary import VocabularyHash
from squads._cli import _common as common
from squads._cli._calls import local_api
from squads._context import get_context
from squads._daemon_link import connection
from squads._daemon_start import ensure, failure_line
from squads._endpoint import Endpoint, endpoint_for, read_record


def context_headers(*, with_client_dir: bool = True) -> dict[str, str]:
    """The headers the invocation's context declares: the actor of ``--as``, the forged time of
    ``--at``, the session lineage and the directory paths in messages are spelled from (left out
    for a squad hosted elsewhere, whose messages are spelled from its root). A header whose value
    the invocation does not set is left out."""
    from squads import _clock
    from squads._paths import process_dir

    ctx = get_context()
    start = ctx.start_dir if ctx.start_dir is not None else process_dir()
    declared = {
        ACTOR_HEADER: ctx.actor_override,
        AT_HEADER: _clock.iso(ctx.clock_override) if ctx.clock_override is not None else None,
        SESSION_HEADER: ctx.session_id,
        PARENT_SESSION_HEADER: ctx.parent_session_id,
        CLIENT_DIR_HEADER: str(start) if with_client_dir else None,
    }
    return {name: value for name, value in declared.items() if value is not None}


def endpoint_name(endpoint: Endpoint) -> str:
    """How a message names the squad's endpoint."""
    if endpoint.transport == "unix":
        return str(endpoint.files.socket)
    record = read_record(endpoint)
    address = record.address("tcp", "cli") if record is not None else None
    return address or str(endpoint.files.info)


def build_http_api(
    endpoint: Endpoint,
    *,
    local: Callable[[], Api] | None,
    vocabulary: Callable[[], VocabularyHash] | None = None,
    restart: Callable[[], bool] | None = None,
) -> HttpApi:
    """The ``HttpApi`` of this invocation for the daemon of *endpoint*, falling back to *local*
    for what the daemon does not serve or declines. *vocabulary* is the hash of the documents the
    command was parsed with; by default the checkout's own. *restart* starts the daemon again when
    it has gone, for a squad that has a local mode."""

    def connect(timeout: float) -> http.client.HTTPConnection | None:
        return connection(endpoint, read_record(endpoint), timeout)

    def checkout_vocabulary() -> VocabularyHash:
        return common.invocation_sources(endpoint.squad_dir).vocabulary()

    def waiting(text: str) -> None:
        common.err_console.print(text, soft_wrap=True)

    def resolve() -> tuple[Connect, str]:
        """The endpoint of the squad resolved again, for the retry a hosted squad gets."""
        fresh = endpoint_for(endpoint.root) or endpoint
        return (
            lambda timeout: connection(fresh, read_record(fresh), timeout),
            endpoint_name(fresh),
        )

    return HttpApi(
        connect=connect,
        restart=restart if endpoint.local_mode else None,
        endpoint=endpoint_name(endpoint),
        headers=lambda: context_headers(with_client_dir=endpoint.local_mode),
        resolve=None if endpoint.local_mode else resolve,
        vocabulary=vocabulary or checkout_vocabulary,
        package_version=squads.__version__,
        local=local if endpoint.local_mode else None,
        waiting=waiting,
    )


#: Seconds a failed daemon start is not tried again within one invocation.
RETRY_AFTER = 30.0


class SelectedApi:
    """The API a long session of the terminal UI calls, chosen on the first call that needs one:
    the squad's daemon, found or started, or this process when there is no squad, the daemon is
    off or it could not be had (one line on stderr says why). Each call looks again when the
    last choice was made for want of a daemon, so a long session does not stay local once one can
    be started."""

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
        endpoint = endpoint_for(self._client_cwd or common.process_dir())
        if not self._usable(endpoint) or endpoint is None:
            return local_api()
        if not self._start(endpoint):
            self._by_default = True
            return local_api()
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
