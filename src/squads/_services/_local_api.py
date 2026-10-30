"""``LocalApi``: operations run in this process, against the squad the request resolves."""

from collections.abc import Awaitable, Callable
from pathlib import Path

from pydantic import BaseModel

from squads import _spans as spans
from squads._api._api import Grant, Mode, Operation
from squads._api._response import Response
from squads._context import NoticeLog, get_context, rebind
from squads._errors import SchemaGateError, SquadsError
from squads._index._store import read_scope
from squads._language import resolve_working_language
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._paths import SquadPaths, resolve
from squads._services._bindings import handler_for, local_handler_for
from squads._services._service import Service, compose_service
from squads._spec_documents import SpecSources, spec_sources


def check_grant(paths: SquadPaths, grant: Grant | None) -> None:
    """Refuse when the squad's schema differs from the package's and *grant* does not cover
    that direction."""
    disk = paths.config.schema_version
    if disk == SCHEMA_VERSION:
        return
    from squads import __version__

    behind = schema_tuple(disk) < schema_tuple(SCHEMA_VERSION)
    if grant is not None and grant.covers(behind=behind):
        return
    if behind:
        raise SchemaGateError(
            f"this squad is at schema v{disk}; squads {__version__} expects v{SCHEMA_VERSION}. "
            "Run sq migrate up to upgrade it (see `sq migrate help`)."
        )
    raise SchemaGateError(
        f"this squad is at schema v{disk}, newer than squads {__version__} "
        f"(v{SCHEMA_VERSION}). Upgrade the squads package."
    )


def _language(notice: str | None) -> tuple[str, ...]:
    """The working-language notice as a tuple of at most one."""
    return () if notice is None else (notice,)


class LocalApi:
    """Runs each operation on a service composed for its mode, inside a read scope; a service
    that holds what its mode asks for is kept for the instance's lifetime, one that fell back is
    composed again on the next call."""

    def __init__(self, sources: Callable[[Path], SpecSources] = spec_sources) -> None:
        self._sources = sources
        self._services: dict[Mode, Service] = {}

    def _service(
        self, mode: Mode, paths: SquadPaths | None, unresolved: SquadsError | None
    ) -> Service:
        cached = self._services.get(mode) if paths is not None else None
        if cached is not None:
            return cached
        ctx = get_context()
        with spans.span("compose"):
            svc = compose_service(
                paths,
                mode,
                resolved_spec=ctx.active_spec,
                sources=self._sources(paths.squad_dir) if paths is not None else None,
                spec_error=ctx.spec_error,
                unresolved=unresolved,
                base=ctx.client_cwd,
            )
        if svc.refusal is None:
            self._services[mode] = svc
        return svc

    async def call[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        """Run *op* on *req*. The notices the engine raised while it ran, then the squad's
        working-language notice, join the warnings, or the refusal's when the call is refused
        past the schema gate. A local-only operation creates the squad, so it runs whether one
        resolves or not, and gets no service."""
        log = get_context().notices
        if log is None:
            log = NoticeLog()
            rebind(notices=log)
        raised_before = len(log.notices)
        paths: SquadPaths | None = None
        unresolved: SquadsError | None = None
        notice: str | None = None
        with spans.span("resolve_squad"):
            try:
                paths = resolve(client_cwd=get_context().client_cwd)
            except SquadsError as exc:
                if op.mode is not Mode.VOCABULARY and not op.local_only:
                    raise
                unresolved = exc
            if paths is not None:
                check_grant(paths, op.grant)
                notice = resolve_working_language(paths.config.working_language)[1]
        try:
            if op.local_only:
                response = await self._scoped(local_handler_for(op)(self._sources, req))
            else:
                svc = self._service(op.mode, paths, unresolved)
                with spans.span("operation"):
                    response = await self._scoped(handler_for(op)(svc, req))
        except SquadsError as exc:
            exc.warnings = (*exc.warnings, *log.notices[raised_before:], *_language(notice))
            raise
        extra = [*log.notices[raised_before:], *_language(notice)]
        if not extra:
            return response
        return response.model_copy(update={"warnings": [*response.warnings, *extra]})

    @staticmethod
    async def _scoped[Res](call: Awaitable[Response[Res]]) -> Response[Res]:
        """Await *call* inside a read scope."""
        with read_scope():
            return await call
