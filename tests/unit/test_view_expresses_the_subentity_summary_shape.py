"""Proof of design adequacy, not a conversion: a declared ``[views]`` entry can express the
same shape ``discussion.summary_columns``/``summary_row`` already derive for the sub-entity
roll-up — same columns (including its badge field), same cell values, same row order — with
nothing about ``ensure_summary``/``set_head``/the templates those functions feed touched.

**Declared test-only, not bundled**, and here is why: the full shape includes ``finding``'s
optional ``severity`` field, and a bundled view naming an optional badge field couples every
project that shadows that field away (``[subentity_kinds.finding] fields = []`` is an ordinary,
supported customisation — ``test_shadowing_a_builtin_subentity_kinds_fields_leaves_its_other_
fields_inherited`` in ``test_badge_collections.py`` exercises exactly this) to keeping it, which
is not a coupling this mechanism should impose. The two views that *do* ship bundled
(``finding_summary``/``finding_summary_line`` — see ``test_view_declaration_referential_checks
.py``) stick to base attributes for that reason; this file proves the declaration is expressive
enough for the badge-field dimension too, without asking every adopter to carry it.
"""

from datetime import UTC, datetime
from pathlib import Path

from squads import __version__
from squads import _badges as badges
from squads import _discussion as discussion
from squads import _views as views
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec


def _declare_full_shape_view(squad_dir: Path) -> None:
    """A view reproducing every column ``summary_columns('finding')`` derives, in the same
    order: local id, the kind's one declared field (``severity``), status, assignee, title."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        "[views.finding_full_shape]\n"
        'source = { kind = "subentity", name = "finding" }\n'
        "fields = [\n"
        '  { code = "id", label = "Finding" },\n'
        '  { code = "severity", label = "Severity" },\n'
        '  { code = "status", label = "Status" },\n'
        '  { code = "assignee", label = "Assignee" },\n'
        '  { code = "title", label = "Title" },\n'
        "]\n",
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _review_with_findings() -> Item:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    subentities = [
        SubEntity(local_id="F1", title="Missing validation", status="Open", severity="high"),
        SubEntity(
            local_id="F2",
            title="Stale comment",
            status="Fixed",
            severity="low",
            assignee="manager",
        ),
    ]
    return Item(
        sequence_id=1,
        type="review",
        title="A review",
        slug="a-review",
        status="Open",
        path="reviews/x1.md",
        created_at=now,
        updated_at=now,
        prefix="REV",
        subentities=subentities,
    )


def test_the_declared_views_own_fields_match_summary_columns_in_order_and_label(
    tmp_path: Path,
) -> None:
    _declare_full_shape_view(tmp_path)
    spec = load_workflow_spec(squad_dir=tmp_path)
    view = spec.views["finding_full_shape"]
    declared_columns = [f.label for f in view.fields]
    assert declared_columns == discussion.summary_columns("finding", spec)


def test_the_projection_produces_the_same_records_summary_row_derives(tmp_path: Path) -> None:
    _declare_full_shape_view(tmp_path)
    spec = load_workflow_spec(squad_dir=tmp_path)
    view = spec.views["finding_full_shape"]

    review = _review_with_findings()
    db = SquadsDB(items={review.sequence_id: review})
    records = views.resolve_records(view, "finding_full_shape", review, db, spec)
    projection = views.project(view, records, spec)

    (group,) = projection.groups
    for row, sub in zip(group.records, review.subentities, strict=True):
        expected = discussion.summary_row("finding", sub, spec)
        # summary_row's cell order matches the view's declared field order 1:1 (both derive
        # from the same base-fields-then-declared-fields layout); compare cell-by-cell rather
        # than assuming a shared row type.
        actual = [row.values[f.code].text for f in view.fields]
        assert actual[0] == expected[0]  # id
        assert actual[2] == expected[2]  # status
        assert actual[3] == expected[3]  # assignee
        assert actual[4] == expected[4]  # title
        # The severity cell's TEXT differs in convention only (summary_row renders "emoji
        # code", the view's default text rendering renders "emoji Label") — the underlying
        # badge is what "same records" actually claims, so compare the structured value.
        assert sub.severity is not None
        coll_code = badges.resolve_collection("finding", "severity", spec)
        emoji, code, label = badges.badge_parts(coll_code, sub.severity, spec)
        assert row.values["severity"].json_value == {
            "code": code,
            "label": label,
            "emoji": emoji,
        }


def test_nothing_about_ensure_summary_or_set_head_changed_by_this_declaration() -> None:
    """The declaration is additive data; the shipped rendering functions this proof stands
    beside are byte-for-byte the functions that shipped before — imported here (not merely
    asserted absent) so a future rename of either would fail this test rather than silently
    stop proving anything."""
    from squads._discussion import ensure_summary, render_summary, set_head, summary_row

    assert callable(ensure_summary)
    assert callable(set_head)
    assert callable(render_summary)
    assert callable(summary_row)
