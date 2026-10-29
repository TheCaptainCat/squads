"""``LocalApi``: operations run in this process, against the squad the request resolves."""

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from squads import __version__
from squads._api._api import Grant, Mode, Operation
from squads._api._response import Response
from squads._context import get_context
from squads._errors import SchemaGateError, SquadsError
from squads._index._store import enter_read_scope, exit_read_scope
from squads._language import resolve_working_language
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._paths import SquadPaths, resolve
from squads._services._bindings import handler_for
from squads._services._service import Service, compose_service
from squads._spec_documents import SpecSources, spec_sources


def check_grant(paths: SquadPaths, grant: Grant | None) -> None:
    """Refuse when the squad's schema differs from the package's and *grant* does not cover
    that direction."""
    disk = paths.config.schema_version
    if disk == SCHEMA_VERSION:
        return
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
        """Run *op* on *req*; the squad's working-language notice joins the warnings."""
        paths: SquadPaths | None = None
        unresolved: SquadsError | None = None
        try:
            paths = resolve(client_cwd=get_context().client_cwd)
        except SquadsError as exc:
            if op.mode is not Mode.VOCABULARY:
                raise
            unresolved = exc
        if paths is not None:
            check_grant(paths, op.grant)
        svc = self._service(op.mode, paths, unresolved)
        token = enter_read_scope()
        try:
            response = await handler_for(op)(svc, req)
        finally:
            exit_read_scope(token)
        _, notice = resolve_working_language(svc.paths.config.working_language)
        if notice is None:
            return response
        return response.model_copy(update={"warnings": [*response.warnings, notice]})
