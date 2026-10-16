"""``sq check`` runs the always-on squad-global members plus the squad's selection, once per run
and never at the create/update gate. Driven over a real corpus through the service and the CLI."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest

from _helpers import create_item
from squads import __version__
from squads import _clock as clock
from squads._rendering._engine import invalidate_squad_dir
from squads._services import _validators
from squads._services._results import CheckIssue
from squads._services._service import Service
from squads._services._validators import SquadGlobalContext, ValidatorEngine
from squads._workflow import load_workflow_spec
from squads._workflow._models import SELECTABLE_SQUAD_GLOBAL_NAMES

pytestmark = pytest.mark.anyio

_MEMBER_MARKERS = {
    "children_settled_with_parent": "open child",
    "dependency_acyclic": "dependency cycle",
    "wip_limit": "active items (limit",
    "unassigned_active": "have no assignee",
    "stale_active": "untouched since",
}


def _select(project: Any, entries: list[str]) -> Service:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    listed = ", ".join(f'"{e}"' for e in entries)
    (overrides / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n[squad]\nvalidators = [{listed}]\n",
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


async def _corpus(svc: Service) -> str:
    """A settled feature with an open child, a two-item dependency cycle, three active tasks of
    which two are unassigned and one is held by a registered assignee. Returns an offending id."""
    feature = (await create_item(svc, "feature", "Parent")).item
    child = (await create_item(svc, "task", "Child", parent=feature.id)).item
    other = (await create_item(svc, "task", "Other")).item
    third = (await create_item(svc, "task", "Third")).item
    await svc.add_ref(other.id, child.id, kind="depends-on")
    await svc.add_ref(child.id, other.id, kind="depends-on")
    for it in (child, other, third):
        await svc.set_status(it.id, "InProgress", force=True)
    await svc.update(third.id, assignee="manager")
    await svc.set_status(feature.id, "Done", force=True)
    return other.id


def _markers(issues: list[CheckIssue]) -> set[str]:
    return {
        name for name, marker in _MEMBER_MARKERS.items() if any(marker in i.message for i in issues)
    }


@dataclass(frozen=True)
class Run:
    id: str
    entries: tuple[str, ...]
    ran: frozenset[str]
    levels: frozenset[str]
    exit_code: int


RUNS = [
    Run("nothing-selected", (), frozenset(), frozenset(), 0),
    Run(
        "one-member",
        ("children_settled_with_parent",),
        frozenset({"children_settled_with_parent"}),
        frozenset({"warn"}),
        0,
    ),
    Run(
        "all-five",
        (
            "children_settled_with_parent",
            "dependency_acyclic",
            "wip_limit:1",
            "unassigned_active:0",
            "stale_active:1",
        ),
        frozenset({"children_settled_with_parent", "dependency_acyclic", "unassigned_active"}),
        frozenset({"warn"}),
        0,
    ),
    Run(
        "one-at-error",
        ("dependency_acyclic@error",),
        frozenset({"dependency_acyclic"}),
        frozenset({"error"}),
        3,
    ),
    Run(
        "one-at-error-among-warns",
        ("children_settled_with_parent", "unassigned_active:0@error"),
        frozenset({"children_settled_with_parent", "unassigned_active"}),
        frozenset({"warn", "error"}),
        3,
    ),
]


@pytest.mark.parametrize("row", RUNS, ids=lambda r: r.id)
async def test_selection_by_run(project, invoke, row: Run) -> None:
    svc = _select(project, list(row.entries))
    await _corpus(svc)

    issues = await svc.check()
    result = await invoke(["check"])

    squad_issues = [i for i in issues if any(m in i.message for m in _MEMBER_MARKERS.values())]
    assert _markers(issues) == row.ran
    assert {i.level for i in squad_issues} == row.levels
    assert result.exit_code == row.exit_code, result.output


@pytest.mark.parametrize("row", RUNS, ids=lambda r: r.id)
async def test_no_selection_at_any_level_changes_a_writes_outcome(project, row: Run) -> None:
    svc = _select(project, list(row.entries))
    offender = await _corpus(svc)

    await svc.update(offender, title="Retitled")
    created = (await create_item(svc, "task", "Late")).item
    await svc.set_status(created.id, "InProgress", force=True)

    assert (await svc.get(offender)).title == "Retitled"


async def test_the_gate_never_evaluates_a_squad_global_member(project) -> None:
    svc = _select(project, ["wip_limit:1@error"])
    await _corpus(svc)
    calls: list[str] = []

    def counted(ctx: SquadGlobalContext) -> list[CheckIssue]:
        calls.append("ran")
        return []

    engine = ValidatorEngine(
        spec=svc.spec, paths=project, squad_global={name: counted for name in ("wip_limit",)}
    )
    db = await svc.store.load()
    engine.gate(next(iter(db.items.values())), db)

    assert calls == []


async def test_a_squad_that_selects_nothing_gets_the_issues_it_got_before(project) -> None:
    svc = _select(project, [])
    await _corpus(svc)
    issues = await svc.check()

    always_on_only = {
        name: member
        for name, member in _validators.SQUAD_GLOBAL_CATALOG.items()
        if name not in SELECTABLE_SQUAD_GLOBAL_NAMES
    }
    db = await svc.store.load()
    before = ValidatorEngine(
        spec=svc.spec, paths=project, playbook=svc.playbook, squad_global=always_on_only
    ).report(db, {})

    assert _markers(issues) == set()
    assert all(i in issues for i in before if "index" not in i.message)


async def test_two_runs_over_an_unchanged_corpus_agree_when_nothing_is_selected(project) -> None:
    svc = _select(project, [])
    await _corpus(svc)

    first = await svc.check()
    second = await svc.check()

    assert first == second


async def test_the_clock_is_read_once_per_run_and_every_item_is_measured_against_it(
    project, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc = _select(project, ["stale_active:5"])
    await _corpus(svc)
    base = clock.now() + timedelta(days=6)
    reads: list[int] = []

    def drifting() -> Any:
        reads.append(1)
        return base + timedelta(days=len(reads) * 100)

    monkeypatch.setattr(_validators.clock, "now", drifting)
    db = await svc.store.load()
    engine = ValidatorEngine(spec=svc.spec, paths=project, playbook=svc.playbook)

    issues = engine.report(db, {})

    assert len(reads) == 1
    stale = [i for i in issues if "untouched since" in i.message]
    assert len(stale) == 3


async def test_a_clean_squad_with_every_member_selected_reports_none_of_them(project) -> None:
    svc = _select(
        project,
        [
            "children_settled_with_parent",
            "dependency_acyclic",
            "wip_limit:3",
            "unassigned_active:0",
            "stale_active:30",
        ],
    )
    await create_item(svc, "task", "Quiet")

    assert _markers(await svc.check()) == set()
