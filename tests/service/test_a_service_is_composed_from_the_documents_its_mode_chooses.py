"""One table: the service ``compose_service`` builds holds the workflow spec and playbook its mode
chooses, over a squad whose overrides do or do not load, and opens the squad it was given.

Each row says what the normal mode does with the squad (builds, or which refusal) and then which
spec and playbook the mode that follows holds. The roles row is the one where the normal mode
builds although the roles override is broken: the catalog is read only when something asks for
it, so a command that never reads it still runs.
"""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from _helpers import make_service
from squads import __version__
from squads._errors import PlaybookConfigError, SquadsError
from squads._interactions._playbook import get_playbook_spec
from squads._paths import SquadPaths
from squads._services._service import (
    BYPASS_FALLBACKS,
    Mode,
    Service,
    compose_first_of,
    compose_service,
)
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio

_STAMP = f"# squads:override-base:{__version__}\n"


def _put(paths: SquadPaths, name: str, body: str) -> None:
    override = paths.squad_dir / ".overrides" / name
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(_STAMP + body, encoding="utf-8")


_INCIDENT = '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "guide"\n'
_INCIDENT_PLAYBOOK = (
    '[types.incident]\noverview = "An incident."\nlifecycle = "Draft -> Active"\n'
    'commands = ["sq create incident"]\nroles = [{ slug = "qa", authors = true }]\n'
)


async def _customised(paths: SquadPaths) -> None:
    _put(paths, "workflow.toml", _INCIDENT)
    _put(paths, "playbook.toml", _INCIDENT_PLAYBOOK)


async def _prefix_clash(paths: SquadPaths) -> None:
    """A live task whose type the workflow override re-prefixes: the index check refuses it, and
    a playbook override sits beside it."""
    await make_service(paths).create("task", "Live", author="manager")
    _put(paths, "workflow.toml", '[items.task]\nprefix = "TSK"\n')
    _put(paths, "playbook.toml", '[types.task]\noverview = "Overridden."\n')


async def _broken_playbook(paths: SquadPaths) -> None:
    _put(paths, "workflow.toml", _INCIDENT)
    _put(paths, "playbook.toml", "[types.incident\nnot toml")


async def _broken_workflow(paths: SquadPaths) -> None:
    _put(paths, "workflow.toml", "[items.broken\nnot toml ===")


async def _broken_roles(paths: SquadPaths) -> None:
    _put(paths, "roles.toml", "[[roles\nnot toml")


async def _broken_roles_beside_a_playbook(paths: SquadPaths) -> None:
    _put(paths, "roles.toml", "[[roles\nnot toml")
    _put(paths, "playbook.toml", '[types.task]\noverview = "Overridden."\n')


@dataclass(frozen=True)
class _Row:
    squad: Callable[[SquadPaths], Awaitable[None]]
    #: What the normal mode raises, by exact class; ``None`` when it builds the service.
    normal_refusal: type[SquadsError] | None
    #: The mode, or the tuple of modes tried in order, composed after the normal one.
    then: Mode | tuple[Mode, ...]
    spec: str  # "bundled" or "merged"
    playbook: str
    catalog_loads: bool = True


_ROWS = {
    "normal": _Row(_customised, None, Mode.NORMAL, "merged", "merged"),
    "index cross-check skipped": _Row(
        _prefix_clash, SquadsError, Mode.INDEX_CHECK_SKIPPED, "merged", "bundled"
    ),
    "playbook override that fails to load": _Row(
        _broken_playbook, PlaybookConfigError, Mode.PLAYBOOK_UNAVAILABLE, "merged", "bundled"
    ),
    "workflow override that fails to load": _Row(
        _broken_workflow, SquadsError, BYPASS_FALLBACKS, "bundled", "bundled"
    ),
    "roles override that fails to load": _Row(
        _broken_roles, None, Mode.NORMAL, "bundled", "bundled", catalog_loads=False
    ),
    "roles override that fails to load beside a playbook override": _Row(
        _broken_roles_beside_a_playbook,
        None,
        Mode.NORMAL,
        "bundled",
        "merged",
        catalog_loads=False,
    ),
}


def _which(svc: Service) -> tuple[str, str]:
    return (
        "bundled" if svc.spec is bundled_spec() else "merged",
        "bundled" if svc.playbook is get_playbook_spec() else "merged",
    )


@pytest.mark.parametrize("name", list(_ROWS))
async def test_service_composition_by_mode(name: str, project: SquadPaths) -> None:
    row = _ROWS[name]
    await row.squad(project)

    if row.normal_refusal is None:
        compose_service(project)
    else:
        with pytest.raises(SquadsError) as refused:
            compose_service(project)
        assert type(refused.value) is row.normal_refusal

    modes = row.then if isinstance(row.then, tuple) else (row.then,)
    svc = compose_first_of(project, modes)

    assert _which(svc) == (row.spec, row.playbook)
    # It opens the squad it was given: its store is that squad's index and lists its items.
    assert svc.store.index_path == project.index_path
    index = json.loads(project.index_path.read_text(encoding="utf-8"))
    assert sorted(it.sequence_id for it in await svc.list_items()) == sorted(
        int(key) for key in index["items"]
    )
    if row.catalog_loads:
        svc.catalog()
    else:
        with pytest.raises(SquadsError):
            svc.catalog()


async def test_repair_runs_after_a_cross_check_refusal_beside_a_playbook_override(
    project: SquadPaths, invoke: Any
) -> None:
    """A workflow override shrinks the priority codes under a live task, so every command but
    ``sq repair`` is refused by the index check; repair runs beside a playbook override."""
    await make_service(project).create("task", "Urgent", author="manager", priority="urgent")
    _put(
        project,
        "workflow.toml",
        '[collections.priority]\nlabel = "Priority"\n'
        'badges = [{ code = "high", label = "High" }, { code = "low", label = "Low" }]\n',
    )
    _put(project, "playbook.toml", '[types.task]\noverview = "Overridden."\n')

    refused = await invoke(["list"])
    repaired = await invoke(["repair"])

    assert refused.exit_code == 1, refused.output
    assert repaired.exit_code == 0, repaired.output
    assert "rebuilt index" in repaired.output
