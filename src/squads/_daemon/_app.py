"""The daemon's HTTP application: one route per operation of the table, the daemon's own routes and
the answers they share."""

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Route, compile_path

from squads._api._api import Operation
from squads._api._dto._daemon import (
    DaemonIdentity,
    DaemonStopping,
    ListenerIdentity,
    VocabularyIdentity,
)
from squads._api._errors import ErrorBody, ErrorDetail, error_body, error_message, http_status
from squads._api._http import RequestMetadata, request_metadata
from squads._api._ops import CONDITIONAL_WRITES, ROUTED_OPERATIONS
from squads._api._response import Response as Envelope
from squads._api._vocabulary import VocabularyHash
from squads._daemon._openapi import build_document
from squads._daemon._request import request_dto
from squads._daemon._state import DaemonState, RetirementCheck, never_retiring
from squads._errors import SchemaMismatchError, SquadsError, VocabularyMismatchError
from squads._models._schema import SCHEMA_VERSION
from squads._services._local_api import LocalApi
from squads._services._service import RequestScope

_log = logging.getLogger("squads.daemon")
# A handler of its own keeps logging's last resort from writing a traceback to stderr.
_log.addHandler(logging.NullHandler())


#: The answer to a request that arrived while the daemon's configuration had changed: nothing ran.
def retiring_body() -> dict[str, str]:
    return {"not_executed": "retiring"}


def _json(content: bytes, status: int = 200, headers: dict[str, str] | None = None) -> Response:
    return Response(content, status_code=status, media_type="application/json", headers=headers)


def _failure(exc: BaseException) -> Response:
    """The error body answering *exc*, with its status."""
    if isinstance(exc, SquadsError):
        body = error_body(exc, error_message(exc))
    else:
        _log.error("unhandled error in a request", exc_info=exc)
        body = error_body(exc, "internal error; the traceback is in the daemon's log")
    return _json(body.model_dump_json(exclude_none=True).encode(), http_status(body.error.type))


class Retiring(Exception):  # a signal, not a failure
    """The daemon's configuration changed, so the request is declined before it runs."""


class Application:
    """The state the daemon's routes share: the squad's documents, the request scope, the
    operation API and the vocabulary the daemon serves."""

    def __init__(self, state: DaemonState, retirement_check: RetirementCheck) -> None:
        self.state = state
        self.retiring = retirement_check
        self.vocabulary: VocabularyHash = state.sources.vocabulary()
        self.scope = RequestScope(state.root, state.squad_dir, state.sources)
        self.api = LocalApi(sources=lambda _squad_dir: state.sources)

    def identity(self) -> DaemonIdentity:
        state = self.state
        deadline = state.idle_deadline()
        return DaemonIdentity(
            pid=state.pid,
            version=state.version,
            schema_version=SCHEMA_VERSION,
            squad_dir=str(state.squad_dir),
            started_at=state.started_at.isoformat(),
            idle_deadline=deadline.isoformat() if deadline is not None else None,
            listeners=[
                ListenerIdentity(transport=ln.transport, address=ln.address, kind=ln.kind)
                for ln in state.listeners
            ],
            vocabulary=VocabularyIdentity(
                hash=self.vocabulary.hash, documents=self.vocabulary.documents
            ),
        )

    def retire(self) -> Response:
        """Answer that the daemon's configuration changed, and ask the process to exit."""
        return JSONResponse(
            retiring_body(), status_code=503, background=BackgroundTask(self.state.stop)
        )

    @staticmethod
    def check_schema(meta: RequestMetadata) -> Response | None:
        """The refusal of a request whose schema is not the daemon's, or ``None``. It needs no
        squad state, so it is answered on arrival, ahead of the queue."""
        if meta.schema is not None and meta.schema != SCHEMA_VERSION:
            return _failure(SchemaMismatchError(meta.schema, SCHEMA_VERSION))
        return None

    def gate(self, meta: RequestMetadata) -> Callable[[], None]:
        """The check a request runs when its turn comes, before its handler: the daemon's
        configuration must not have changed since it started (a vocabulary that differs from a
        daemon whose configuration changed is answered ``retiring``), then the request's
        vocabulary must be the daemon's."""

        def check() -> None:
            if self.retiring():
                raise Retiring
            if meta.vocabulary is not None and meta.vocabulary != self.vocabulary.hash:
                raise VocabularyMismatchError(self.vocabulary.documents)

        return check


def _answer(envelope: Envelope[Any], etag: str | None, handler_ms: float) -> Response:
    headers = {"Server-Timing": f"handler;dur={handler_ms:.1f}"}
    if etag is not None:
        headers["ETag"] = etag
    return _json(envelope.model_dump_json().encode(), headers=headers)


def _operation_endpoint(
    app: Application, op: Operation[Any, Any]
) -> Callable[[Request], Awaitable[Response]]:
    """The one endpoint every operation's route is served by: it refuses a client that is not
    the daemon's, validates the request DTO, runs the operation in the request scope and writes
    the envelope or the error."""

    async def endpoint(request: Request) -> Response:
        meta = request_metadata(request.headers)
        refused = app.check_schema(meta)
        if refused is not None:
            return refused
        try:
            req: BaseModel = await request_dto(op, request)
            answered = await app.scope.run(
                meta,
                lambda: app.api.call(op, req),
                conditional=op.name in CONDITIONAL_WRITES,
                gate=app.gate(meta),
            )
        except Retiring:
            return app.retire()
        except Exception as exc:  # every failure has an answer
            return _failure(exc)
        return _answer(answered.value, answered.etag, answered.handler_ms)

    return endpoint


def _daemon_routes(app: Application) -> list[BaseRoute]:
    async def identity(_request: Request) -> Response:  # noqa: RUF029 — an endpoint is async
        return _json(app.identity().model_dump_json().encode())

    async def stop(_request: Request) -> Response:  # noqa: RUF029 — an endpoint is async
        return Response(
            DaemonStopping(stopping=True).model_dump_json().encode(),
            media_type="application/json",
            background=BackgroundTask(app.state.stop),
        )

    @functools.cache
    def document() -> bytes:
        import json

        return json.dumps(build_document(SCHEMA_VERSION)).encode()

    async def openapi(_request: Request) -> Response:  # noqa: RUF029 — an endpoint is async
        return _json(document())

    return [
        Route("/v1/daemon", identity, methods=["GET"], name="daemon.identity"),
        Route("/v1/daemon/stop", stop, methods=["POST"], name="daemon.stop"),
        Route("/v1/openapi.json", openapi, methods=["GET"], name="openapi"),
    ]


def _served() -> list[tuple[str, str]]:
    """Every method and path template the daemon serves."""
    served = [(op.route[0], op.route[1]) for op in ROUTED_OPERATIONS]
    return [
        *served,
        ("GET", "/v1/daemon"),
        ("POST", "/v1/daemon/stop"),
        ("GET", "/v1/openapi.json"),
    ]


def allowed_methods(path: str) -> list[str]:
    """The methods the daemon serves at *path*, sorted, with ``HEAD`` beside ``GET``."""
    methods: set[str] = set()
    for method, template in _served():
        regex, _, _ = compile_path(template)
        if regex.match(path):
            methods.add(method)
            if method == "GET":
                methods.add("HEAD")
    return sorted(methods)


async def _http_error(request: Request, exc: Exception) -> Response:  # noqa: RUF029 — a handler is async
    """A request no route took: the error body of an unknown route or a method it lacks, which
    names every method the path does serve."""
    assert isinstance(exc, HTTPException)
    kind = "not_found" if exc.status_code == 404 else "invalid"
    message = "no such route" if exc.status_code == 404 else "method not allowed on this route"
    body = ErrorBody(error=ErrorDetail(type=kind, message=message))
    headers = None
    if exc.status_code == 405:
        headers = {"Allow": ", ".join(allowed_methods(request.url.path))}
    return _json(body.model_dump_json(exclude_none=True).encode(), exc.status_code, headers)


def build_app(state: DaemonState, retirement_check: RetirementCheck = never_retiring) -> Starlette:
    """The Starlette application serving the squad *state* describes: every operation at its
    route, the daemon's identity and stop, and the OpenAPI document. *retirement_check* says
    whether the daemon's configuration changed; a request that finds it so is answered
    ``retiring``."""
    app = Application(state, retirement_check)
    routes: list[BaseRoute] = [
        Route(op.route[1], _operation_endpoint(app, op), methods=[op.route[0]], name=op.name)
        for op in ROUTED_OPERATIONS
    ]
    routes += _daemon_routes(app)
    return Starlette(routes=routes, exception_handlers={HTTPException: _http_error})
