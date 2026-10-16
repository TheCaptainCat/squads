"""The five selectable squad-global members, driven directly over small in-memory corpora: parent
outcomes, dependency cycles, and the active-item measures (WIP, unassigned, staleness)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._services import _validators
from squads._services._results import CheckIssue
from squads._services._validators import SQUAD_GLOBAL_CATALOG, SquadGlobalContext
from squads._workflow import bundled_spec
from squads._workflow._models import RoleSpec, SquadSpec, WorkflowSpec

_NOW = datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)


def _item(
    seq: int,
    item_type: str = "task",
    status: str = "InProgress",
    *,
    parent: str | None = None,
    refs: tuple[str, ...] = (),
    assignee: str | None = None,
    updated: datetime = _NOW,
    subentities: tuple[SubEntity, ...] = (),
) -> Item:
    prefix = BUILTIN_PREFIX[item_type]
    return Item(
        sequence_id=seq,
        type=item_type,
        prefix=prefix,
        title=f"item {seq}",
        slug=f"item-{seq}",
        status=status,
        path=f"{BUILTIN_FOLDER[item_type]}/{prefix}-{seq:06d}-item-{seq}.md",
        created_at=_NOW,
        updated_at=updated,
        parent=parent,
        refs=list(refs),
        assignee=assignee,
        subentities=list(subentities),
    )


def _id(seq: int, item_type: str = "task") -> str:
    return f"{BUILTIN_PREFIX[item_type]}-{seq:06d}"


def _shown(seq: int) -> str:
    """The id an item displays, as a finding names it."""
    return f"{BUILTIN_PREFIX['task']}-{seq}"


def _run(
    project: Any,
    name: str,
    entry: str,
    items: list[Item],
    *,
    spec: WorkflowSpec | None = None,
    now: datetime = _NOW,
) -> list[CheckIssue]:
    base = spec if spec is not None else bundled_spec()
    selected = base.model_copy(update={"squad": SquadSpec(validators=[entry])})
    db = SquadsDB(counter=max((i.sequence_id for i in items), default=0))
    for it in items:
        db.items[it.sequence_id] = it
    ctx = SquadGlobalContext(index=db, on_disk={}, spec=selected, paths=project, now=now)
    return SQUAD_GLOBAL_CATALOG[name](ctx)


def _spec_with_running_role() -> WorkflowSpec:
    """A spec where the role named ``active`` is not live and ``InReview`` rests under a live
    role of another name, so a match on the name and a match on the flag disagree."""
    base = bundled_spec()
    roles = {
        **base.roles,
        "active": base.roles["active"].model_copy(update={"live": False}),
        "running": RoleSpec(settled=False, hidden=False, color="positive", live=True),
    }
    statuses = {
        **base.statuses,
        "InReview": base.statuses["InReview"].model_copy(update={"role": "running"}),
    }
    return base.model_copy(update={"roles": roles, "statuses": statuses})


def _spec_with_wrapped_role() -> WorkflowSpec:
    """A spec where ``Blocked`` rests under a settled role of a name other than ``done``."""
    base = bundled_spec()
    roles = {**base.roles, "wrapped": RoleSpec(settled=True, hidden=False, color="muted")}
    statuses = {
        **base.statuses,
        "Blocked": base.statuses["Blocked"].model_copy(update={"role": "wrapped"}),
    }
    return base.model_copy(update={"roles": roles, "statuses": statuses})


# ----------------------------------------------------------------- children_settled_with_parent

_OPEN_STORY = SubEntity(local_id="US1", title="story", status="Todo")


@dataclass(frozen=True)
class Parent:
    id: str
    parent_type: str
    parent_status: str
    children: tuple[str, ...]  # statuses of the children
    findings: int
    spec: str = "bundled"  # "wrapped": Blocked rests under a settled role of another name
    sub_only: bool = False


PARENTS = [
    Parent("settled-no-children", "feature", "Done", (), 0),
    Parent("settled-all-children-settled", "feature", "Done", ("Done", "Done"), 0),
    Parent("settled-one-open-child", "feature", "Done", ("Done", "InProgress"), 1),
    Parent("settled-several-open-children", "feature", "Done", ("Draft", "Ready", "Done"), 1),
    Parent("settled-cancelled-child", "feature", "Done", ("Cancelled",), 0),
    Parent("cancelled-parent-open-child", "feature", "Cancelled", ("Draft",), 1),
    Parent("open-parent-open-child", "feature", "InProgress", ("Draft",), 0),
    Parent("epic-parent", "epic", "Done", ("Draft",), 1),
    Parent("milestone-parent", "milestone", "Done", ("Draft",), 1),
    Parent("child-settled-under-another-role-name", "feature", "Done", ("Blocked",), 0, "wrapped"),
    Parent("child-open-under-bundled-roles", "feature", "Done", ("Blocked",), 1),
    Parent("open-sub-entities-only", "feature", "Done", (), 0, sub_only=True),
]


@pytest.mark.parametrize("row", PARENTS, ids=lambda r: r.id)
async def test_parent_status_by_children(project, row: Parent) -> None:
    parent = _item(
        1,
        row.parent_type,
        row.parent_status,
        subentities=(_OPEN_STORY,) if row.sub_only else (),
    )
    kids = [
        _item(10 + n, "task", status, parent=parent.id) for n, status in enumerate(row.children)
    ]
    spec = _spec_with_wrapped_role() if row.spec == "wrapped" else None

    issues = _run(
        project,
        "children_settled_with_parent",
        "children_settled_with_parent",
        [parent, *kids],
        spec=spec,
    )

    assert len(issues) == row.findings
    for issue in issues:
        assert issue.item == parent.id
        assert issue.level == "warn"
        assert parent.status in issue.message


async def test_the_open_children_are_named_in_the_message_and_counted(project) -> None:
    parent = _item(1, "feature", "Done")
    kids = [_item(n, "task", "Draft", parent=parent.id) for n in range(2, 9)]

    (issue,) = _run(
        project, "children_settled_with_parent", "children_settled_with_parent", [parent, *kids]
    )

    assert "7 open children" in issue.message
    assert _shown(2) in issue.message and "and 2 more" in issue.message


async def test_a_parent_is_reported_once_however_many_children_are_open(project) -> None:
    parent = _item(1, "feature", "Done")
    kids = [_item(n, "task", "Draft", parent=parent.id) for n in range(2, 6)]

    assert (
        len(
            _run(
                project,
                "children_settled_with_parent",
                "children_settled_with_parent",
                [parent, *kids],
            )
        )
        == 1
    )


# ---------------------------------------------------------------------------- dependency_acyclic


def _chain(edges: list[tuple[int, int, str]], count: int) -> list[Item]:
    """*count* tasks; each ``(a, b, kind)`` puts ``b:kind`` on item ``a``."""
    refs: dict[int, list[str]] = {}
    for a, b, kind in edges:
        refs.setdefault(a, []).append(f"{_id(b)}:{kind}")
    return [_item(n, refs=tuple(refs.get(n, ()))) for n in range(1, count + 1)]


@dataclass(frozen=True)
class Graph:
    id: str
    count: int
    edges: tuple[tuple[int, int, str], ...]
    paths: tuple[tuple[int, ...], ...]  # the expected path around each cycle


GRAPHS = [
    Graph("two-cycle", 2, ((1, 2, "depends-on"), (2, 1, "depends-on")), ((1, 2, 1),)),
    Graph(
        "three-cycle",
        3,
        ((1, 2, "depends-on"), (2, 3, "depends-on"), (3, 1, "depends-on")),
        ((1, 2, 3, 1),),
    ),
    Graph(
        "three-cycle-in-blocks",
        3,
        ((1, 2, "blocks"), (2, 3, "blocks"), (3, 1, "blocks")),
        ((1, 3, 2, 1),),
    ),
    Graph("self-block", 1, ((1, 1, "blocks"),), ((1, 1),)),
    Graph("self-depends-on", 1, ((1, 1, "depends-on"),), ((1, 1),)),
    Graph(
        "diamond",
        4,
        ((1, 2, "depends-on"), (1, 3, "depends-on"), (2, 4, "depends-on"), (3, 4, "depends-on")),
        (),
    ),
    # 1 depends-on 2 and 1 blocks 2 (so 2 depends on 1): a cycle only if orientation is honoured.
    Graph("mixed-blocks-and-depends-on", 2, ((1, 2, "depends-on"), (1, 2, "blocks")), ((1, 2, 1),)),
    # 1 blocks 2 and 2 blocks 3: 2 depends on 1, 3 depends on 2 -- a chain, never a cycle.
    Graph("blocks-chain", 3, ((1, 2, "blocks"), (2, 3, "blocks")), ()),
    Graph("related-cycle", 2, ((1, 2, "related"), (2, 1, "related")), ()),
    Graph("targets-cycle", 2, ((1, 2, "targets"), (2, 1, "targets")), ()),
    Graph("long-chain", 6, tuple((n, n + 1, "depends-on") for n in range(1, 6)), ()),
    Graph(
        "two-disjoint-cycles",
        4,
        ((1, 2, "depends-on"), (2, 1, "depends-on"), (3, 4, "blocks"), (4, 3, "blocks")),
        ((1, 2, 1), (3, 4, 3)),
    ),
    Graph(
        "cycle-with-a-tail",
        4,
        ((1, 2, "depends-on"), (2, 3, "depends-on"), (3, 2, "depends-on"), (3, 4, "depends-on")),
        ((2, 3, 2),),
    ),
]


@pytest.mark.parametrize("row", GRAPHS, ids=lambda r: r.id)
async def test_graph_shape_by_cycles(project, row: Graph) -> None:
    issues = _run(
        project, "dependency_acyclic", "dependency_acyclic", _chain(list(row.edges), row.count)
    )

    assert [i.message for i in issues] == [
        "dependency cycle: " + " -> ".join(_shown(n) for n in path) for path in row.paths
    ]
    assert all(i.item == "" and i.level == "warn" for i in issues)


async def test_a_two_thousand_node_chain_closing_on_itself_is_one_cycle(project) -> None:
    size = 2000
    edges = [(n, n + 1, "depends-on") for n in range(1, size)] + [(size, 1, "depends-on")]

    issues = _run(project, "dependency_acyclic", "dependency_acyclic", _chain(edges, size))

    assert len(issues) == 1
    assert issues[0].message.count("TASK-") == size + 1


async def test_a_group_larger_than_its_path_names_the_other_items(project) -> None:
    edges = [(1, 2, "depends-on"), (2, 1, "depends-on"), (2, 3, "depends-on"), (3, 2, "depends-on")]

    (issue,) = _run(project, "dependency_acyclic", "dependency_acyclic", _chain(edges, 3))

    assert issue.message == (
        f"dependency cycle: {_shown(1)} -> {_shown(2)} -> {_shown(1)} (also involving {_shown(3)})"
    )


async def test_a_cycle_among_settled_items_is_reported_like_any_other(project) -> None:
    items = [
        _item(1, status="Done", refs=(f"{_id(2)}:depends-on",)),
        _item(2, status="Cancelled", refs=(f"{_id(1)}:depends-on",)),
    ]

    (issue,) = _run(project, "dependency_acyclic", "dependency_acyclic", items)

    assert issue.message == f"dependency cycle: {_shown(1)} -> {_shown(2)} -> {_shown(1)}"


async def test_a_message_counts_in_the_singular_when_there_is_one(project) -> None:
    (wip,) = _run(
        project, "wip_limit", "wip_limit:1", [_item(1, assignee="a"), _item(2, assignee="a")]
    )
    (one,) = _run(project, "unassigned_active", "unassigned_active:0", [_item(1)])
    (stale,) = _run(
        project, "stale_active", "stale_active:1", [_item(1, updated=_NOW - timedelta(days=9))]
    )
    (kid,) = _run(
        project,
        "children_settled_with_parent",
        "children_settled_with_parent",
        [_item(1, "feature", "Done"), _item(2, parent=_id(1, "feature"), status="Draft")],
    )

    assert "holds 2 active items" in wip.message
    assert "1 active item has no assignee" in one.message
    assert "more than 1 day)" in stale.message
    assert "1 open child:" in kid.message


async def test_an_edge_to_an_item_that_does_not_exist_is_not_a_cycle(project) -> None:
    items = [_item(1, refs=(f"{_id(99)}:depends-on",))]

    assert _run(project, "dependency_acyclic", "dependency_acyclic", items) == []


async def test_an_edge_written_at_another_id_width_still_closes_the_cycle(project) -> None:
    items = [
        _item(1, refs=("TASK-2:depends-on",)),
        _item(2, refs=("TASK-000001:depends-on",)),
    ]

    assert len(_run(project, "dependency_acyclic", "dependency_acyclic", items)) == 1


# ------------------------------------------------------------------------- active-item counting


@dataclass(frozen=True)
class Resting:
    id: str
    item_type: str
    status: str
    counted: bool
    spec: str = "bundled"


RESTING = [
    Resting("work-live", "task", "InProgress", True),
    Resting("work-live-review", "task", "InReview", True),
    Resting("work-draft", "task", "Draft", False),
    Resting("work-blocked", "task", "Blocked", False),
    Resting("work-settled", "task", "Done", False),
    Resting("work-cancelled", "task", "Cancelled", False),
    Resting("bug-live", "bug", "InProgress", True),
    Resting("review-live", "review", "InReview", True),
    Resting("role-active", "role", "Active", False),
    Resting("skill-active", "skill", "Active", False),
    Resting("operator-active", "operator", "Active", False),
    Resting("contract-active", "contract", "Active", False),
    Resting("records-live", "milestone", "InProgress", False),
    # A live role under another name counts; a role named `active` that is not live does not.
    Resting("live-role-under-another-name", "task", "InReview", True, "running"),
    Resting("role-named-active-not-live", "task", "InProgress", False, "running"),
]

_MEASURES = [
    ("wip_limit", "wip_limit:0", "alice"),
    ("unassigned_active", "unassigned_active:0", None),
    ("stale_active", "stale_active:1", None),
]


@pytest.mark.parametrize("measure", _MEASURES, ids=lambda m: m[0])
@pytest.mark.parametrize("row", RESTING, ids=lambda r: r.id)
async def test_active_item_counting_by_measure(project, row: Resting, measure) -> None:
    name, entry, assignee = measure
    old = _NOW - timedelta(days=30)
    item = _item(1, row.item_type, row.status, assignee=assignee, updated=old)
    spec = _spec_with_running_role() if row.spec == "running" else None

    issues = _run(project, name, entry, [item], spec=spec)

    assert len(issues) == (1 if row.counted else 0)


# ----------------------------------------------------------------------------------- wip_limit


@pytest.mark.parametrize(("held", "flagged"), [(0, False), (2, False), (3, False), (4, True)])
async def test_wip_limit_boundary_is_more_than_the_limit(project, held: int, flagged: bool) -> None:
    items = [_item(n, assignee="alice") for n in range(1, held + 1)]

    issues = _run(project, "wip_limit", "wip_limit:3", items)

    assert (len(issues) == 1) is flagged
    if flagged:
        assert issues[0].item == ""
        assert "alice holds 4 active items (limit 3)" in issues[0].message


async def test_two_assignees_over_the_cap_give_two_findings_in_slug_order(project) -> None:
    items = [_item(n, assignee="zoe") for n in range(1, 4)]
    items += [_item(n, assignee="bob") for n in range(4, 7)]
    items += [_item(7, assignee="carol")]

    issues = _run(project, "wip_limit", "wip_limit:2", items)

    assert [i.message.split(" holds")[0] for i in issues] == ["bob", "zoe"]


async def test_wip_limit_skips_unassigned_items_and_settled_ones(project) -> None:
    items = [_item(n) for n in range(1, 6)] + [_item(6, status="Done", assignee="alice")]

    assert _run(project, "wip_limit", "wip_limit:1", items) == []


# ---------------------------------------------------------------------------- unassigned_active


@pytest.mark.parametrize(
    ("limit", "unassigned", "flagged"),
    [(0, 0, False), (0, 1, True), (2, 2, False), (2, 3, True)],
)
async def test_unassigned_active_boundary_is_more_than_the_limit(
    project, limit: int, unassigned: int, flagged: bool
) -> None:
    items = [_item(n) for n in range(1, unassigned + 1)] + [_item(50, assignee="alice")]

    issues = _run(project, "unassigned_active", f"unassigned_active:{limit}", items)

    assert (len(issues) == 1) is flagged
    if flagged:
        assert issues[0].item == ""
        noun = "item has" if unassigned == 1 else "items have"
        assert f"{unassigned} active {noun} no assignee (limit {limit})" in issues[0].message
        assert "alice" not in issues[0].message


# ------------------------------------------------------------------------------- stale_active


@pytest.mark.parametrize(
    ("age_days", "flagged"), [(0, False), (29, False), (30, False), (31, True), (400, True)]
)
async def test_stale_active_boundary_is_more_than_the_days(
    project, age_days: int, flagged: bool
) -> None:
    item = _item(1, updated=_NOW - timedelta(days=age_days))

    issues = _run(project, "stale_active", "stale_active:30", [item])

    assert [i.item for i in issues] == ([item.id] if flagged else [])
    assert all(i.level == "warn" for i in issues)


async def test_stale_active_reads_the_instant_it_is_handed_and_calls_no_clock(
    project, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode() -> datetime:
        raise AssertionError("a member must not read the clock")

    monkeypatch.setattr(_validators.clock, "now", explode)
    item = _item(1, updated=_NOW - timedelta(days=10))

    assert len(_run(project, "stale_active", "stale_active:5", [item], now=_NOW)) == 1
    assert (
        _run(project, "stale_active", "stale_active:5", [item], now=_NOW - timedelta(days=9)) == []
    )


# --------------------------------------------------------------------- level and selection reading


@pytest.mark.parametrize(
    ("entry", "level"),
    [("wip_limit:1", "warn"), ("wip_limit:1@warn", "warn"), ("wip_limit:1@error", "error")],
)
async def test_a_finding_carries_its_selections_level(project, entry: str, level: str) -> None:
    items = [_item(n, assignee="alice") for n in range(1, 4)]

    (issue,) = _run(project, "wip_limit", entry, items)

    assert issue.level == level


async def test_a_member_that_is_not_selected_reports_nothing_even_when_run_directly(
    project,
) -> None:
    items = [_item(n, assignee="alice") for n in range(1, 9)]
    spec = bundled_spec()
    db = SquadsDB(counter=8)
    for it in items:
        db.items[it.sequence_id] = it
    ctx = SquadGlobalContext(index=db, on_disk={}, spec=spec, paths=project, now=_NOW)

    for name in ("wip_limit", "unassigned_active", "stale_active"):
        assert SQUAD_GLOBAL_CATALOG[name](ctx) == []
