"""The squad-creation operations, ``init`` and ``adopt``: they create the squad a service is
composed on, so they take the request's directory and the documents read for it, not a service."""

from collections.abc import Callable
from pathlib import Path

from squads._api._dto._squad import AdoptReport, AdoptRequest, InitReport, InitRequest
from squads._api._response import Response
from squads._context import get_context
from squads._paths import process_dir
from squads._services._corpus_ops import unreadable_lines
from squads._services._service import adopt, init
from squads._spec_documents import SpecSources


async def init_squad(
    sources: Callable[[Path], SpecSources], req: InitRequest
) -> Response[InitReport]:
    """Create a squad in the request's directory and activate its roles."""
    root = get_context().client_cwd
    result = await init(
        root=root,
        squad_dir=req.squad_dir,
        backend=req.backends,
        roles_spec=req.roles,
        no_claude=req.no_claude,
        force=req.force,
        names=req.names or None,
        sources=sources((root or process_dir()) / req.squad_dir),
        _skip_skill_seed=not req.seed_skills,
    )
    paths = result.paths
    return Response(
        data=InitReport(
            squad=str(paths.squad_dir),
            index=str(paths.index_path),
            roles=[r.slug for r in result.roles],
            backends=list(paths.config.active_backends),
            warnings=list(result.warnings),
        )
    )


async def adopt_squad(
    _sources: Callable[[Path], SpecSources], req: AdoptRequest
) -> Response[AdoptReport]:
    """Bring the squad folder in the request's directory under squads, indexing its items; it
    reads the documents of the folder its configuration names, once that is known."""
    result = await adopt(
        root=get_context().client_cwd,
        squad_dir=req.squad_dir,
        backend=req.backends,
        roles_spec=req.roles,
        no_claude=req.no_claude,
        renumber=req.renumber,
    )
    return Response(
        data=AdoptReport(
            squad=str(result.paths.squad_dir),
            imported=result.imported,
            roles=[r.slug for r in result.roles],
            notice=result.repair.strip_notice(),
            unreadable=unreadable_lines(result.repair.unreadable),
            renumbered=list(result.repair.renumber_report),
            warnings=list(result.warnings),
        )
    )
