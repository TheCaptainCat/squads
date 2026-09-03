"""``squads._views`` — the projection engine: source resolution, the uniform record shape,
grouping, ordering, and the ``--json`` contract. Pure-model tests (no service, no index file)
since every function here takes an already-built ``Item``/``SubEntity``/``SquadsDB`` and the
active spec — the same cost shape ``sq tree``/``sq blocked`` have.
"""

from datetime import UTC, datetime
from typing import cast

import pytest

from squads import _views as views
from squads._errors import SquadsError
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._workflow import bundled_spec
from squads._workflow._models import ViewField, ViewSource, ViewSpec

SPEC = bundled_spec()
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _item(
    seq: int,
    item_type: str,
    title: str,
    status: str,
    *,
    prefix: str,
    parent: str | None = None,
    assignee: str | None = None,
    refs: list[str] | None = None,
    subentities: list[SubEntity] | None = None,
) -> Item:
    folder = SPEC.items[item_type].folder
    return Item(
        sequence_id=seq,
        type=item_type,
        title=title,
        slug=title.lower().replace(" ", "-"),
        status=status,
        path=f"{folder}/x{seq}.md",
        created_at=_NOW,
        updated_at=_NOW,
        prefix=prefix,
        parent=parent,
        assignee=assignee,
        refs=refs or [],
        subentities=subentities or [],
    )


def _db(*items: Item) -> SquadsDB:
    return SquadsDB(items={it.sequence_id: it for it in items})


def _finding(
    local_id: str, title: str, *, severity: str = "medium", assignee: str | None = None
) -> SubEntity:
    return SubEntity(
        local_id=local_id, title=title, status="Open", severity=severity, assignee=assignee
    )


# --------------------------------------------------------------------------- subentity source


def test_subentity_source_projects_the_items_own_subentities() -> None:
    review = _item(
        1,
        "review",
        "A review",
        "Open",
        prefix="REV",
        subentities=[_finding("F1", "First", severity="high"), _finding("F2", "Second")],
    )
    view = ViewSpec(
        source=ViewSource(kind="subentity", name="finding"),
        fields=[
            ViewField(code="id", label="Finding"),
            ViewField(code="severity", label="Severity"),
        ],
    )
    records = views.resolve_records(view, "probe", review, _db(review), SPEC)
    projection = views.project(view, records, SPEC)

    (group,) = projection.groups
    assert [r.values["id"].text for r in group.records] == ["F1", "F2"]
    assert group.records[0].values["severity"].json_value == {
        "code": "high",
        "label": "High",
        "emoji": "🟠",
    }


def test_subentity_source_refuses_when_the_item_hosts_a_different_kind() -> None:
    task = _item(1, "task", "A task", "Draft", prefix="TASK")
    view = ViewSpec(
        source=ViewSource(kind="subentity", name="finding"),
        fields=[ViewField(code="id", label="Finding")],
    )
    with pytest.raises(SquadsError, match="hosts"):
        views.resolve_records(view, "probe", task, _db(task), SPEC)


def test_subentity_source_with_no_subentities_projects_zero_records() -> None:
    review = _item(1, "review", "A review", "Open", prefix="REV")
    view = ViewSpec(
        source=ViewSource(kind="subentity", name="finding"),
        fields=[ViewField(code="id", label="Finding")],
    )
    records = views.resolve_records(view, "probe", review, _db(review), SPEC)
    projection = views.project(view, records, SPEC)
    assert projection.records() == []
    assert projection.groups == [views.ViewGroup(key=None, records=[])]


# --------------------------------------------------------------------------- ref source


def test_ref_source_resolves_bare_and_explicit_kind_refs_by_inversion() -> None:
    target = _item(1, "feature", "Target feature", "Draft", prefix="FEAT")
    bare = _item(2, "task", "Bare ref", "Draft", prefix="TASK", refs=["FEAT-1"])
    explicit = _item(3, "task", "Explicit ref", "Draft", prefix="TASK", refs=["FEAT-1:related"])
    other_kind = _item(4, "task", "Other kind", "Draft", prefix="TASK", refs=["FEAT-1:depends-on"])
    unrelated = _item(5, "task", "No ref", "Draft", prefix="TASK")
    db = _db(target, bare, explicit, other_kind, unrelated)

    view = ViewSpec(
        source=ViewSource(kind="ref", name="related"),
        fields=[ViewField(code="id", label="Item")],
    )
    records = views.resolve_records(view, "probe", target, db, SPEC)
    assert {r.identity for r in records} == {"TASK-2", "TASK-3"}


def test_ref_source_never_matches_across_a_shared_sequence_number() -> None:
    """A ``BUG`` and a ``TASK`` sharing sequence 1 must not cross-match — the same width-
    tolerant, type-prefix-aware comparison ``SquadsDB.backrefs`` uses."""
    feat = _item(1, "feature", "Feature one", "Draft", prefix="FEAT")
    bug = _item(1, "bug", "Bug one (same sequence)", "Open", prefix="BUG")
    referencer = _item(
        2, "task", "Refers to the bug, not the feature", "Draft", prefix="TASK", refs=["BUG-1"]
    )
    db = _db(feat, bug, referencer)

    view = ViewSpec(
        source=ViewSource(kind="ref", name="related"),
        fields=[ViewField(code="id", label="Item")],
    )
    assert views.resolve_records(view, "probe", feat, db, SPEC) == []
    (matched,) = views.resolve_records(view, "probe", bug, db, SPEC)
    assert matched.identity == "TASK-2"


# --------------------------------------------------------------------------- subtree source


def test_subtree_source_projects_descendants_of_the_declared_type_only() -> None:
    feat = _item(1, "feature", "Umbrella", "Draft", prefix="FEAT")
    t1 = _item(2, "task", "Task A", "Draft", prefix="TASK", parent="FEAT-1")
    t2 = _item(3, "task", "Task B", "Draft", parent="TASK-2", prefix="TASK")  # grandchild
    bug = _item(4, "bug", "A bug, not a task", "Open", prefix="BUG", parent="FEAT-1")
    db = _db(feat, t1, t2, bug)

    view = ViewSpec(
        source=ViewSource(kind="subtree", name="task"),
        fields=[ViewField(code="id", label="Item")],
        order_by=["id"],
    )
    records = views.resolve_records(view, "probe", feat, db, SPEC)
    assert [r.identity for r in records] == ["TASK-2", "TASK-3"]


def test_subtree_source_finds_nothing_outside_the_subtree() -> None:
    feat = _item(1, "feature", "Umbrella", "Draft", prefix="FEAT")
    unrelated_task = _item(2, "task", "Not a child", "Draft", prefix="TASK")
    db = _db(feat, unrelated_task)
    view = ViewSpec(
        source=ViewSource(kind="subtree", name="task"), fields=[ViewField(code="id", label="Item")]
    )
    assert views.resolve_records(view, "probe", feat, db, SPEC) == []


# --------------------------------------------------------------------------- uniform record shape


def _consume_generic(projection: views.Projection) -> list[dict[str, object]]:
    """A consumer that has never seen this view: reads only ``.fields``/``.groups`` off the
    projection, branching on nothing view-specific — the property every source must share."""
    return [
        {f.code: rec.values[f.code].json_value for f in projection.fields}
        for group in projection.groups
        for rec in group.records
    ]


@pytest.mark.parametrize(
    "make_projection",
    [
        pytest.param(
            lambda: views.project(
                ViewSpec(
                    source=ViewSource(kind="subentity", name="finding"),
                    fields=[
                        ViewField(code="id", label="Id"),
                        ViewField(code="status", label="Status"),
                    ],
                ),
                views.resolve_records(
                    ViewSpec(
                        source=ViewSource(kind="subentity", name="finding"),
                        fields=[],
                    ),
                    "probe",
                    (
                        review := _item(
                            1,
                            "review",
                            "R",
                            "Open",
                            prefix="REV",
                            subentities=[_finding("F1", "t")],
                        )
                    ),
                    _db(review),
                    SPEC,
                ),
                SPEC,
            ),
            id="subentity",
        ),
        pytest.param(
            lambda: views.project(
                ViewSpec(
                    source=ViewSource(kind="ref", name="related"),
                    fields=[
                        ViewField(code="id", label="Id"),
                        ViewField(code="status", label="Status"),
                    ],
                ),
                views.resolve_records(
                    ViewSpec(source=ViewSource(kind="ref", name="related"), fields=[]),
                    "probe",
                    (target := _item(1, "feature", "F", "Draft", prefix="FEAT")),
                    _db(target, _item(2, "task", "T", "Draft", prefix="TASK", refs=["FEAT-1"])),
                    SPEC,
                ),
                SPEC,
            ),
            id="ref",
        ),
    ],
)
def test_one_consumer_reads_every_source_without_branching(make_projection) -> None:
    projection = make_projection()
    rows = _consume_generic(projection)
    assert rows and all("id" in row and "status" in row for row in rows)


# --------------------------------------------------------------------------- grouping + ordering


def test_group_by_buckets_by_the_declared_fields_resolved_value() -> None:
    root = _item(0, "feature", "Root", "Draft", prefix="FEAT")
    t1 = _item(1, "task", "Alpha", "Draft", prefix="TASK", parent="FEAT-0")
    t2 = _item(2, "task", "Beta", "InProgress", prefix="TASK", parent="FEAT-0")
    t3 = _item(3, "task", "Gamma", "Draft", prefix="TASK", parent="FEAT-0")
    view = ViewSpec(
        source=ViewSource(kind="subtree", name="task"),
        fields=[ViewField(code="id", label="Id"), ViewField(code="status_role", label="Role")],
        group_by="status_role",
        order_by=["id"],
    )
    db = _db(root, t1, t2, t3)
    records = views.resolve_records(view, "probe", root, db, SPEC)
    projection = views.project(view, records, SPEC)

    by_key = {g.key: [r.values["id"].text for r in g.records] for g in projection.groups}
    assert by_key["pending"] == ["TASK-1", "TASK-3"]
    assert "active" in by_key
    assert by_key["active"] == ["TASK-2"]


def test_order_by_sorts_within_group_and_is_stable_with_no_order_by() -> None:
    review = _item(
        1,
        "review",
        "R",
        "Open",
        prefix="REV",
        subentities=[_finding("F1", "Zebra"), _finding("F2", "Apple")],
    )
    unordered = ViewSpec(
        source=ViewSource(kind="subentity", name="finding"),
        fields=[ViewField(code="id", label="Id"), ViewField(code="title", label="Title")],
    )
    ordered = ViewSpec(
        source=ViewSource(kind="subentity", name="finding"),
        fields=[ViewField(code="id", label="Id"), ViewField(code="title", label="Title")],
        order_by=["title"],
    )
    records = views.resolve_records(unordered, "probe", review, _db(review), SPEC)

    unordered_proj = views.project(unordered, records, SPEC)
    ordered_proj = views.project(ordered, records, SPEC)

    assert [r.values["id"].text for r in unordered_proj.records()] == ["F1", "F2"]  # file order
    assert [r.values["id"].text for r in ordered_proj.records()] == ["F2", "F1"]  # Apple < Zebra


def test_order_by_on_id_sorts_by_sequence_number_across_a_digit_boundary() -> None:
    """Both source resolvers already sort numerically (``number_for_id``); ``order_by =
    ["id"]`` must not re-sort lexicographically and throw that away."""
    root = _item(0, "feature", "Root", "Draft", prefix="FEAT")
    t9 = _item(9, "task", "Ninth", "Draft", prefix="TASK", parent="FEAT-0")
    t15 = _item(15, "task", "Fifteenth", "Draft", prefix="TASK", parent="FEAT-0")
    t100 = _item(100, "task", "Hundredth", "Draft", prefix="TASK", parent="FEAT-0")
    view = ViewSpec(
        source=ViewSource(kind="subtree", name="task"),
        fields=[ViewField(code="id", label="Id")],
        order_by=["id"],
    )
    db = _db(root, t9, t15, t100)
    records = views.resolve_records(view, "probe", root, db, SPEC)
    projection = views.project(view, records, SPEC)
    assert [r.values["id"].text for r in projection.records()] == ["TASK-9", "TASK-15", "TASK-100"]


def test_order_by_on_id_alone_interleaves_types_by_number_not_by_type() -> None:
    """``order_by = ["id"]`` alone (no ``"type"`` first) orders purely on the number, so a
    group spanning several types comes out interleaved by number rather than grouped by
    type — the ``order_by = ["type", "id"]`` shape the bundled roll-up declares is what
    avoids this, deliberately, when a caller wants types kept together instead."""
    t5 = _item(5, "task", "Task five", "Draft", prefix="TASK")
    b3 = _item(3, "bug", "Bug three", "Open", prefix="BUG")
    t9 = _item(9, "task", "Task nine", "Draft", prefix="TASK")
    view = ViewSpec(
        source=ViewSource(kind="ref", name="related"),
        fields=[ViewField(code="id", label="Id")],
        order_by=["id"],
    )
    # `resolve_records` isn't used here — a `ref` source's own records are `Item`s of any
    # declared type, but `project()` only ever needs the already-resolved records, so this
    # builds them directly rather than routing three items' forward refs through a `SquadsDB`
    # whose `items` dict is keyed by the very sequence number this test wants two records to
    # share... except it can't: that dict is `dict[int, Item]`, so two items can never
    # actually collide on one sequence number in a real index (the global counter's job) —
    # this test is about interleaving different numbers, not a same-number tie.
    records = [views._record_from_item(it) for it in (t5, b3, t9)]
    projection = views.project(view, records, SPEC)
    assert [r.values["id"].text for r in projection.records()] == ["BUG-3", "TASK-5", "TASK-9"]


def test_sort_key_tie_breaks_a_shared_sequence_number_by_prefix() -> None:
    """A defensive contract on ``_sort_key`` itself, not a scenario a real index can produce
    (``SquadsDB.items`` is ``dict[int, Item]`` — two items can never share a sequence number):
    if two records' ``id`` cells ever did carry the same number, the tie-break is the prefix,
    so the function stays fully deterministic rather than depending on input order."""
    bug_cell = views.Cell(text="BUG-1", json_value="BUG-1")
    feat_cell = views.Cell(text="FEAT-1", json_value="FEAT-1")
    bug_key = views._sort_key("bug", "id", bug_cell, SPEC)
    feat_key = views._sort_key("feature", "id", feat_cell, SPEC)
    assert bug_key < feat_key  # "BUG" < "FEAT"


def test_order_by_on_a_badge_field_follows_the_declared_order_not_the_code() -> None:
    """``severity``'s declared order is critical > high > medium > low > info — alphabetical by
    code would read critical, high, low, medium. An absent value and a code the collection no
    longer recognises (e.g. a badge dropped after the value was stored) both degrade gracefully
    — the same non-crashing discipline ``ItemFilter._meets_min`` already uses — rather than
    raising, one table-driven case rather than one test per branch."""
    root = _item(0, "feature", "Root", "Draft", prefix="FEAT")
    low = _item(1, "bug", "Low severity", "Open", prefix="BUG", parent="FEAT-0")
    low.severity = "low"
    critical = _item(2, "bug", "Critical severity", "Open", prefix="BUG", parent="FEAT-0")
    critical.severity = "critical"
    medium = _item(3, "bug", "Medium severity", "Open", prefix="BUG", parent="FEAT-0")
    medium.severity = "medium"
    unset = _item(4, "bug", "No severity set", "Open", prefix="BUG", parent="FEAT-0")
    stale = _item(5, "bug", "Stale severity code", "Open", prefix="BUG", parent="FEAT-0")
    stale.severity = "no-longer-a-badge"

    view = ViewSpec(
        source=ViewSource(kind="subtree", name="bug"),
        fields=[ViewField(code="id", label="Id"), ViewField(code="severity", label="Severity")],
        order_by=["severity"],
    )
    db = _db(root, low, critical, medium, unset, stale)
    records = views.resolve_records(view, "probe", root, db, SPEC)
    projection = views.project(view, records, SPEC)

    assert [r.values["id"].text for r in projection.records()] == [
        unset.id,  # absent value sorts first
        critical.id,  # then declared order: critical, ...
        medium.id,  # ... medium, ...
        low.id,  # ... low
        stale.id,  # an unrecognised code falls back after every ranked value
    ]


# --------------------------------------------------------------------------- --json contract


def test_projection_json_carries_field_metadata_grouping_and_records_only() -> None:
    review = _item(
        1,
        "review",
        "R",
        "Open",
        prefix="REV",
        subentities=[_finding("F1", "First", severity="critical")],
    )
    view = ViewSpec(
        source=ViewSource(kind="subentity", name="finding"),
        fields=[
            ViewField(code="id", label="Finding"),
            ViewField(code="severity", label="Severity"),
        ],
    )
    records = views.resolve_records(view, "probe", review, _db(review), SPEC)
    projection = views.project(view, records, SPEC)
    payload = views.projection_json(projection)

    assert set(payload) == {"fields", "group_by", "groups"}
    assert payload["fields"] == [
        {"code": "id", "label": "Finding", "type": "text"},
        {"code": "severity", "label": "Severity", "type": "badge"},
    ]
    assert payload["group_by"] is None
    (group,) = cast("list[dict[str, object]]", payload["groups"])
    assert group["key"] is None
    assert group["count"] == 1
    assert group["records"] == [
        {"id": "F1", "severity": {"code": "critical", "label": "Critical", "emoji": "🔴"}}
    ]


def test_group_count_matches_the_records_it_was_computed_from() -> None:
    """``ViewGroup.count`` is the one place ``len(records)`` is computed — both a template's
    ``group.count`` and ``--json``'s ``"count"`` read the same property, so the two documented
    consumers of a projection can never disagree about the shape of the same object again."""
    review = _item(
        1,
        "review",
        "R",
        "Open",
        prefix="REV",
        subentities=[_finding("F1", "First"), _finding("F2", "Second")],
    )
    view = ViewSpec(
        source=ViewSource(kind="subentity", name="finding"),
        fields=[ViewField(code="id", label="Id")],
    )
    records = views.resolve_records(view, "probe", review, _db(review), SPEC)
    projection = views.project(view, records, SPEC)
    (group,) = projection.groups

    assert group.count == 2 == len(group.records)
    payload = views.projection_json(projection)
    (json_group,) = cast("list[dict[str, object]]", payload["groups"])
    assert json_group["count"] == group.count
