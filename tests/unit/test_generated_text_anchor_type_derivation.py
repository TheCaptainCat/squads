"""``cheatsheet_anchor_type`` (the generic "Common commands" example anchor) and
``first_ordered_field`` (the generic "priority axis" discovery) — both replace a template
that used to probe one hardcoded type ("task") for text that should survive that type's own
drop, since other types still carry the same capability.
"""

from squads._badges import first_ordered_field
from squads._interactions import cheatsheet_anchor_type
from squads._workflow import bundled_spec


def test_anchor_type_is_task_on_the_bundled_spec() -> None:
    """task is the only bundled type with a sub-entity kind, a required parent, AND an
    ordered field — it should win on score even though it isn't first by declared order."""
    assert cheatsheet_anchor_type(bundled_spec()) == "task"


def test_anchor_type_falls_back_when_task_is_dropped() -> None:
    base = bundled_spec()
    dropped = {k: v for k, v in base.items.items() if k != "task"}
    spec = base.model_copy(update={"items": dropped})
    # feature is the next-best scorer (sub-entity kind + ordered field, no required parent).
    assert cheatsheet_anchor_type(spec) == "feature"


def test_anchor_type_is_none_when_every_non_roster_type_is_dropped() -> None:
    base = bundled_spec()
    roster_only = {k: v for k, v in base.items.items() if v.category == "roster"}
    spec = base.model_copy(update={"items": roster_only})
    assert cheatsheet_anchor_type(spec) is None


def test_first_ordered_field_survives_dropping_the_type_it_used_to_be_read_from() -> None:
    base = bundled_spec()
    bundled_field = first_ordered_field(base)
    assert bundled_field is not None
    assert bundled_field.code == "priority"

    dropped = {k: v for k, v in base.items.items() if k != "task"}
    spec = base.model_copy(update={"items": dropped})
    # Every surviving non-roster type still declares the identical priority field, so
    # dropping task must not delete the axis from generated prose.
    survived_field = first_ordered_field(spec)
    assert survived_field is not None
    assert survived_field.code == "priority"


def test_first_ordered_field_is_none_when_no_type_declares_an_ordered_collection() -> None:
    base = bundled_spec()
    unordered_items = {
        t: (ts.model_copy(update={"fields": []}) if ts.category != "roster" else ts)
        for t, ts in base.items.items()
    }
    spec = base.model_copy(update={"items": unordered_items})
    assert first_ordered_field(spec) is None
