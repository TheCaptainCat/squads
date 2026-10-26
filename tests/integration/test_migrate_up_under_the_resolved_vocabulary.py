"""``sq migrate up`` validates every index load under the vocabulary the squad's own overrides
declare, whatever schema the squad is stamped at: a squad whose valid override declares a type,
a status, a sub-entity status or a badge code, carried by one item, migrates to the current
schema and keeps that item with its own value.

One table of (squad source and stamped schema) by (what the override alone declares), driven
through ``Service.run_pending_migrations`` and through ``sq migrate up``.
"""

import shutil
import tomllib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from _helpers import make_service
from squads import __version__, _aio
from squads._models._config import SquadsConfig
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from squads._rendering._engine import invalidate_squad_dir
from squads._services import _service as service
from squads._services._service import Service
from squads._spec_documents import resolve_playbook
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"

_WORK_TRANSITIONS = """\
Draft = ["Ready", "InProgress", "Cancelled", "Triaged"]
Ready = ["InProgress", "Blocked", "Cancelled"]
InProgress = ["InReview", "Blocked", "Done", "Cancelled"]
InReview = ["InProgress", "Done", "Blocked", "Cancelled"]
Blocked = ["Ready", "InProgress", "Cancelled"]
Done = ["InProgress"]
Cancelled = ["Draft"]
Triaged = ["InProgress", "Cancelled"]
"""

_SUBENTITY_TRANSITIONS = """\
Todo = ["InProgress", "Blocked", "Cancelled", "Parked"]
InProgress = ["Done", "Blocked", "Cancelled"]
Blocked = ["InProgress", "Cancelled"]
Done = ["InProgress"]
Cancelled = ["Todo"]
Parked = ["Todo", "Cancelled"]
"""

_INCIDENT = """\
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "guide"
"""

_PLAYBOOK_INCIDENT = """\
[types.incident]
overview = "An incident."
lifecycle = "Draft -> Active -> Archived"
commands = ["sq create incident \\"...\\" --author manager"]
roles = [{ slug = "manager", authors = true }]
"""


@dataclass(frozen=True)
class Family:
    """What an override alone declares, the one item that carries it, and how to read it back."""

    workflow: str
    carry: Callable[[Service, str], Awaitable[str]]
    read: Callable[[Any], str]
    expected: str
    playbook: str = ""
    compiled: str = ""


async def _carry_type(svc: Service, author: str) -> str:
    return (await svc.create("incident", "An incident", author=author)).item.id


async def _carry_status(svc: Service, author: str) -> str:
    return (await svc.create("task", "A triaged task", status="Triaged", author=author)).item.id


async def _carry_subentity_status(svc: Service, author: str) -> str:
    task = (await svc.create("task", "A task with a parked subtask", author=author)).item
    await svc.add_subtask(task.id, "Parked work", status="Parked")
    return task.id


async def _carry_badge(svc: Service, author: str) -> str:
    return (
        await svc.create("task", "A task with a custom badge", priority="now", author=author)
    ).item.id


async def _carry_plain(svc: Service, author: str) -> str:
    return (await svc.create("task", "A plain task", author=author)).item.id


FAMILIES: dict[str, Family] = {
    "type": Family(_INCIDENT, _carry_type, lambda it: it.type, "incident"),
    "status": Family(
        f'[statuses.Triaged]\nrole = "active"\n[lifecycles.work]\ninitial = "Draft"\n'
        f"[lifecycles.work.transitions]\n{_WORK_TRANSITIONS}",
        _carry_status,
        lambda it: it.status,
        "Triaged",
    ),
    "subentity-status": Family(
        f'[statuses.Parked]\nrole = "blocked"\n[lifecycles.subentity]\ninitial = "Todo"\n'
        f"[lifecycles.subentity.transitions]\n{_SUBENTITY_TRANSITIONS}",
        _carry_subentity_status,
        lambda it: it.subentities[0].status,
        "Parked",
    ),
    "badge": Family(
        '[collections.priority]\nlabel = "Priority"\nordered = true\nbadges = [\n'
        '  { code = "urgent", label = "Urgent" },\n  { code = "now", label = "Now" },\n'
        '  { code = "low", label = "Low" },\n]\n',
        _carry_badge,
        lambda it: it.priority,
        "now",
    ),
    "none": Family("", _carry_plain, lambda it: it.type, "task"),
    "type-and-playbook": Family(
        _INCIDENT,
        _carry_type,
        lambda it: it.type,
        "incident",
        playbook=_PLAYBOOK_INCIDENT,
        compiled="authors **incidents** (`sq create incident`)",
    ),
}

#: (label, kind, schema): a frozen aged corpus, or a fresh squad built without skill seeding
#: and stamped back to a schema whose runner allocates skill ids from legacy skill files.
SOURCES: dict[str, tuple[str, str]] = {
    "corpus-0.8": ("corpus", "v0_8"),
    "corpus-0.11": ("corpus", "v0_11"),
    "corpus-0.14": ("corpus", "v0_14"),
    "built-0.4": ("built", "0.4"),
    "built-0.8": ("built", "0.8"),
    "built-0.11": ("built", "0.11"),
}


def _paths_at(root: Path) -> SquadPaths:
    with (root / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    return SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)


def _stamped(paths: SquadPaths) -> str:
    with paths.config_path.open("rb") as fh:
        return tomllib.load(fh)["schema_version"]


async def _squad_from(source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SquadPaths:
    kind, which = SOURCES[source]
    if kind == "corpus":
        root = tmp_path / which
        shutil.copytree(_CORPUS_DIR / which, root)
        return _paths_at(root)
    monkeypatch.chdir(tmp_path)
    built = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    text = await _aio.read_text(built.paths.config_path)
    text = text.replace(f'schema_version = "{SCHEMA_VERSION}"', f'schema_version = "{which}"')
    await _aio.write_text(built.paths.config_path, text)
    return _paths_at(tmp_path)


def _service_for(paths: SquadPaths) -> Service:
    invalidate_squad_dir(paths.squad_dir)
    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    return make_service(
        paths,
        spec=spec,
        playbook=resolve_playbook(spec, paths.squad_dir),
    )


def _author_of(paths: SquadPaths) -> str:
    """The corpus fixtures register a single role; a fresh minimal squad registers `manager`."""
    corpus_role = paths.squad_dir / "agents/roles/ROLE-000001-dev-agent.md"
    return "dev-agent" if corpus_role.exists() else "manager"


async def _carry_family(paths: SquadPaths, family: Family) -> str:
    overrides = paths.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    header = f"# squads:override-base:{__version__}\n"
    author = _author_of(paths)
    if family.workflow:
        (overrides / "workflow.toml").write_text(header + family.workflow, encoding="utf-8")
    if family.playbook:
        (overrides / "playbook.toml").write_text(header + family.playbook, encoding="utf-8")
    return await family.carry(_service_for(paths), author)


async def _assert_item_kept(paths: SquadPaths, item_id: str, family: Family, source: str) -> None:
    assert _stamped(paths) == SCHEMA_VERSION
    if family.compiled and SOURCES[source][0] == "built":
        # only the playbook override can produce this line, and only a squad whose roster holds
        # the role it names has it compiled; the aged corpora register a different role
        assert family.compiled in (paths.root / "CLAUDE.md").read_text(encoding="utf-8")
    migrated = _service_for(_paths_at(paths.root))
    item = await migrated.get(item_id)
    assert family.read(item) == family.expected


@pytest.mark.parametrize("family_name", FAMILIES)
@pytest.mark.parametrize("source", SOURCES)
async def test_the_service_migrates_a_squad_whose_override_declares_the_vocabulary_its_item_uses(
    source: str,
    family_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    frozen_time,
) -> None:
    family = FAMILIES[family_name]
    paths = await _squad_from(source, tmp_path, monkeypatch)
    item_id = await _carry_family(paths, family)

    run = await _service_for(paths).run_pending_migrations()

    assert run.applied
    await _assert_item_kept(paths, item_id, family, source)


@pytest.mark.parametrize("family_name", FAMILIES)
@pytest.mark.parametrize("source", SOURCES)
async def test_the_cli_migrates_a_squad_whose_override_declares_the_vocabulary_its_item_uses(
    source: str,
    family_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    frozen_time,
    invoke,
) -> None:
    family = FAMILIES[family_name]
    paths = await _squad_from(source, tmp_path, monkeypatch)
    item_id = await _carry_family(paths, family)
    monkeypatch.chdir(paths.root)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    await _assert_item_kept(paths, item_id, family, source)
