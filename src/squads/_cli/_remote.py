"""The CLI's client of the daemon: the headers an invocation sends, the connection to the daemon
its endpoint names and the ``HttpApi`` built from them."""

import http.client
from collections.abc import Callable

import squads
from squads._api._api import Api
from squads._api._client import Connect, HttpApi
from squads._api._http import (
    ACTOR_HEADER,
    AT_HEADER,
    CLIENT_DIR_HEADER,
    PARENT_SESSION_HEADER,
    SESSION_HEADER,
)
from squads._api._vocabulary import VocabularyHash
from squads._cli import _common as common
from squads._context import get_context
from squads._daemon_link import connection
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
) -> HttpApi:
    """The ``HttpApi`` of this invocation for the daemon of *endpoint*, falling back to *local*
    for what the daemon does not serve or declines. *vocabulary* is the hash of the documents the
    command was parsed with; by default the checkout's own."""

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

    def restart() -> bool:
        """The daemon is gone (stopped, idle, retired): start it again, or say why not."""
        from squads._daemon_start import ensure, failure_line

        reason = ensure(endpoint)
        if reason is not None:
            common.err_console.print(common.e(failure_line(reason)), soft_wrap=True)
        return reason is None

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
