"""``sq mine`` matches a slug that owns an item OR one of its sub-entities; default visibility
is evaluated per matched reason (item-level on the item's own status, sub-entity-level on that
sub-entity's own status) and the row shows when at least one reason is open. ``sq workload``
counts sub-entity assignments as separate, additive columns alongside the existing item counts.
"""

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------------- mine: basics


async def test_mine_surfaces_an_item_via_a_sub_entity_assignment_alone(svc):
    """An actor owning only a subtask (parent unassigned) still sees the parent item."""
    task = (await create_item(svc, "task", "parent")).item
    await svc.add_subtask(task.id, "child", assignee="manager")

    rows = await svc.mine("manager")
    assert [r.item.id for r in rows] == [task.id]
    assert [s.local_id for s in rows[0].matched_subentities] == ["ST1"]


async def test_mine_excludes_an_item_whose_sub_entities_are_assigned_elsewhere(svc):
    await svc.add_dev("python")  # registers python-dev
    task = (await create_item(svc, "task", "parent")).item
    await svc.add_subtask(task.id, "child", assignee="python-dev")

    assert await svc.mine("manager") == []


async def test_mine_matched_subentities_lists_every_assigned_sub_regardless_of_status(svc):
    """The matched-sub-entity list is not pruned by the visibility predicate: a settled sub
    assigned to the slug still appears in the reason list, even when it isn't why the row
    itself is visible."""
    task = (await create_item(svc, "task", "parent", assignee="manager")).item
    await svc.add_subtask(task.id, "open child", assignee="manager", status="Todo")
    await svc.add_subtask(task.id, "done child", assignee="manager", status="Done")

    rows = await svc.mine("manager")
    assert {s.local_id for s in rows[0].matched_subentities} == {"ST1", "ST2"}


async def test_mine_all_flag_bypasses_the_visibility_predicate(svc):
    task = (await create_item(svc, "task", "parent", status="Done", assignee="manager")).item

    assert await svc.mine("manager") == []
    rows = await svc.mine("manager", include_closed=True)
    assert [r.item.id for r in rows] == [task.id]


async def test_mine_operator_slug_matches_a_sub_entity_assignee_identically(svc):
    op = await svc.add_operator("Alice Tester")
    task = (await create_item(svc, "task", "parent")).item
    await svc.add_subtask(task.id, "child", assignee=op.extra["slug"])

    rows = await svc.mine(op.extra["slug"])
    assert [r.item.id for r in rows] == [task.id]


@pytest.mark.parametrize(
    ("kind", "parent_type", "add"),
    [("story", "feature", "add_story"), ("finding", "review", "add_finding")],
)
async def test_mine_surfaces_a_sub_entity_match_across_kinds_other_than_subtask(
    svc, kind, parent_type, add
):
    parent = (await create_item(svc, parent_type, "parent")).item
    await getattr(svc, add)(parent.id, "child", assignee="manager")

    rows = await svc.mine("manager")
    assert [r.item.id for r in rows] == [parent.id]


# -------------------------------------------------------------- mine: the visibility matrix

# (item_assigned, item_open, sub_assigned, sub_open, expect_visible_by_default) — abstract shape,
# resolved to concrete status names per kind below. "open"/"settled" stand in for each kind's own
# OPEN and SETTLED-hidden example, deliberately reusing the same shape across kinds to show the
# predicate is evaluated per-entity, not by a shared literal.
_VISIBILITY_SHAPE = [
    # item-only match: exactly today's item-level behaviour.
    pytest.param(True, True, False, True, True, id="item-open-only"),
    pytest.param(True, False, False, True, False, id="item-settled-only"),
    # sub-only match: a sub-entity-only assignment, both directions.
    pytest.param(False, True, True, True, True, id="sub-open-only"),
    pytest.param(False, True, True, False, False, id="sub-settled-only"),
    pytest.param(False, False, True, True, True, id="sub-open-only-parent-also-settled"),
    pytest.param(False, False, True, False, False, id="sub-settled-only-parent-also-settled"),
    # both match: the row shows if EITHER reason is open (ruling's two directional cases).
    pytest.param(True, False, True, True, True, id="both-settled-parent-open-sub"),
    pytest.param(True, True, True, False, True, id="both-open-parent-settled-sub"),
    pytest.param(True, False, True, False, False, id="both-settled"),
    pytest.param(True, True, True, True, True, id="both-open"),
]

# (kind, parent_type, add_verb, sub_open_status, sub_settled_status) — the kind axis the matrix
# above was never crossed with. `finding` runs twice: once against its `done`-role settled
# status (Verified) and once against its `retired`-role one (WontFix) — both settled+hidden,
# but a different role object, and the one place this release has repeatedly been bitten on is
# an assumption baked in for one role that silently mis-handles the other. `Fixed` (the finding
# kind's OPEN status) carries the `active` role — still open work — while `Verified`/`WontFix`
# are both settled; item-level parent status is each parent type's own lifecycle (task/feature:
# InProgress/Done; review: InReview/Approved), independent of the sub-entity kind under test.
_KIND_MATRIX = [
    pytest.param(
        "subtask", "task", "add_subtask", "Todo", "Done", "InProgress", "Done", id="subtask"
    ),
    pytest.param("story", "feature", "add_story", "Todo", "Done", "InProgress", "Done", id="story"),
    pytest.param(
        "finding",
        "review",
        "add_finding",
        "Fixed",
        "Verified",
        "InReview",
        "Approved",
        id="finding-verified",
    ),
    pytest.param(
        "finding",
        "review",
        "add_finding",
        "Fixed",
        "WontFix",
        "InReview",
        "Approved",
        id="finding-wontfix",
    ),
]

_KIND_MATRIX_FIELDS = (
    "kind",
    "parent_type",
    "add_verb",
    "sub_open_status",
    "sub_settled_status",
    "item_open_status",
    "item_settled_status",
)


@pytest.mark.parametrize(_KIND_MATRIX_FIELDS, _KIND_MATRIX)
@pytest.mark.parametrize(
    ("item_assigned", "item_open", "sub_assigned", "sub_open", "expect_visible"),
    _VISIBILITY_SHAPE,
)
async def test_mine_default_visibility_follows_whichever_reason_is_open(
    svc,
    kind,
    parent_type,
    add_verb,
    sub_open_status,
    sub_settled_status,
    item_open_status,
    item_settled_status,
    item_assigned,
    item_open,
    sub_assigned,
    sub_open,
    expect_visible,
):
    item_status = item_open_status if item_open else item_settled_status
    sub_status = sub_open_status if sub_open else sub_settled_status
    parent = (
        await create_item(
            svc,
            parent_type,
            "parent",
            status=item_status,
            assignee="manager" if item_assigned else None,
        )
    ).item
    await getattr(svc, add_verb)(
        parent.id,
        "child",
        status=sub_status,
        assignee="manager" if sub_assigned else None,
    )

    ids = {r.item.id for r in await svc.mine("manager")}
    assert (parent.id in ids) is expect_visible, (
        f"{kind}/{sub_status} under {parent_type}/{item_status}: expected visible={expect_visible}"
    )
    # --all always includes a matched row (item or sub side), independent of status.
    ids_all = {r.item.id for r in await svc.mine("manager", include_closed=True)}
    assert parent.id in ids_all


# ------------------------------------------------------- mine vs workload: settled vs hidden


async def test_mine_and_workload_deliberately_disagree_on_an_in_force_status(svc):
    """`mine` reads `hidden_by_default` (matches `sq list`/`sq tree`); `workload` reads
    `is_open` (a settled/not-settled census). They coincide for every bundled sub-entity
    lifecycle, but the bundled `in_force` role — settled, yet not hidden — already lives on an
    ITEM lifecycle (`Accepted` decisions, `Published` guides): settled work still shows in the
    default `mine` queue while counting closed in `workload`. Pinned so a future change that
    makes the two predicates agree does so on purpose, not by accident."""
    decision = (await create_item(svc, "decision", "an accepted decision", assignee="manager")).item
    await svc.set_status(decision.id, "Accepted")

    assert {r.item.id for r in await svc.mine("manager")} == {decision.id}

    row = next(r for r in await svc.workload() if r.assignee == "manager")
    assert row.open == 0
    assert row.closed == 1


async def test_mine_excludes_a_roster_category_item_matching_workloads_own_guard(svc):
    """`workload` has always excluded roster-category items; `mine` sat right beneath it with
    no equivalent guard. No CLI verb sets `assignee` on a role/skill/operator today, so this
    isn't reachable through normal usage — but the service layer itself doesn't block it, and
    the two functions should agree on the same question rather than one enforcing the exclusion
    and the other silently omitting it."""
    role = await svc.create(
        "role", "Some Role", author="manager", slug="some-role", assignee="manager"
    )
    assert role.item.assignee == "manager"

    assert await svc.mine("manager") == []


# ---------------------------------------------------------------------------------- workload


async def test_workload_gives_a_sub_entity_only_assignee_their_own_row(svc):
    task = (await create_item(svc, "task", "parent")).item
    await svc.add_subtask(task.id, "child", assignee="manager")

    rows = {r.assignee: r for r in await svc.workload()}
    assert rows["manager"].open == 0  # no item of their own
    assert rows["manager"].closed == 0
    assert rows["manager"].subentity_open == 1
    assert rows["manager"].subentity_total == 1


async def test_workload_item_and_sub_entity_counts_are_independent_for_the_same_actor(svc):
    """An actor owning both a parent item and one of its sub-entities is counted once in the
    item columns and once in the sub-entity columns — never merged into one number."""
    task = (await create_item(svc, "task", "parent", assignee="manager")).item
    await svc.add_subtask(task.id, "child", assignee="manager")

    row = next(r for r in await svc.workload() if r.assignee == "manager")
    assert row.open == 1
    assert row.total == 1
    assert row.subentity_open == 1
    assert row.subentity_total == 1


async def test_workload_sub_entity_counts_split_open_and_closed_via_the_spec_predicate(svc):
    task = (await create_item(svc, "task", "parent")).item
    await svc.add_subtask(task.id, "open child", assignee="manager", status="Todo")
    await svc.add_subtask(task.id, "done child", assignee="manager", status="Done")

    row = next(r for r in await svc.workload() if r.assignee == "manager")
    assert row.subentity_open == 1
    assert row.subentity_closed == 1
    assert row.subentity_total == 2
