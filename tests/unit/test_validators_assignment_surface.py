"""``ItemSpec.validators`` — the per-type extend-only assignment surface over the category
default bundle — and its Plane-1 (load-time) checks: an unknown validator name fails closed, a
``:<param>`` suffix is only well-formed on a name in ``PARAMETERIZED_VALIDATOR_NAMES``, and an
``@<level>`` suffix must name a declared level no lower than the member's declared floor, if it
has one. Engine wiring lives elsewhere: each named validator's own behaviour, including how a
declared level and threshold actually change what it reports, in
``tests/service/test_validator_catalog_lift.py``, and a type's own additions extending its
effective set in ``tests/service/test_records_epic_no_parent_enforcement.py``.
"""

from datetime import UTC, datetime

import pytest

from squads._errors import SquadsError
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._services._validators import ValidatorEngine
from squads._workflow import bundled_spec
from squads._workflow._models import (
    ItemSpec,
    WorkflowSpec,
    parse_validator_entry,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _spec_dict(base: WorkflowSpec, items: dict[str, ItemSpec]) -> dict[str, object]:
    return {
        "items": items,
        "statuses": dict(base.statuses),
        "lifecycles": dict(base.lifecycles),
        "prefix_to_type": dict(base.prefix_to_type),
        "alias_to_type": dict(base.alias_to_type),
        "collections": dict(base.collections),
        "subentity_kinds": dict(base.subentity_kinds),
        "roles": dict(base.roles),
        "ref_kinds": dict(base.ref_kinds),
        "views": dict(base.views),
    }


def test_bundled_spec_declares_only_epics_and_skills_validators_additions() -> None:
    """Exactly two built-in types carry a ``validators`` addition, each for its own reason:
    ``epic``'s own ``no_parent`` (enforcing the work-root constraint — ``records``' own
    ``no_parent`` comes from the category bundle instead, not a per-type addition), and
    ``skill``'s own ``item_skill_shadowed`` (the ``roster`` category bundle is empty, so a
    declared type's skill losing its generated guidance to authored content has to be reported
    from the one type that can name the check itself).

    ``feature`` is the near miss, and the reason this is asserted over the whole item table
    rather than for ``epic``/``skill`` alone: it declares a ``ref_rules`` entry targeting
    ``contract`` and selects **no** validator over it. Typing that edge is bundled; requiring a
    delivered feature to carry one is a per-project call made in an override, not a default
    every squad inherits."""
    spec = bundled_spec()
    assert spec.items["epic"].validators == ["no_parent"]
    assert spec.items["skill"].validators == ["item_skill_shadowed"]
    assert spec.items["feature"].validators == []
    assert any(rr.target == "contract" for rr in spec.items["feature"].ref_rules)
    assert all(ts.validators == [] for t, ts in spec.items.items() if t not in ("epic", "skill"))


def test_an_unknown_validator_name_fails_closed_at_load() -> None:
    base = bundled_spec()
    items = {**base.items, "task": base.items["task"].model_copy(update={"validators": ["nope"]})}
    with pytest.raises(SquadsError, match="unknown validator"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_a_param_on_a_non_parameterized_validator_fails_closed_at_load() -> None:
    """``parent_in`` reads the structured ``parents`` field — no param — per the architect's
    pin; the seed-catalog colon notation is documentary shorthand only."""
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(update={"validators": ["parent_in:feature"]}),
    }
    with pytest.raises(SquadsError, match="takes no param"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_a_param_on_subentity_title_max_is_well_formed() -> None:
    """The one seed validator whose threshold isn't already a structured field."""
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(update={"validators": ["subentity_title_max:50"]}),
    }
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))
    assert spec.items["task"].validators == ["subentity_title_max:50"]


def test_a_param_on_ref_rule_target_present_is_well_formed() -> None:
    """The other parameterized name — nothing bundled selects it, so this surface is where its
    accepted shape is pinned: the param names the target item type, and the type carrying the
    addition already declares a ``ref_rules`` entry with that target (both conditions are
    checked at load, see ``_check_ref_rule_targets``)."""
    base = bundled_spec()
    items = {
        **base.items,
        "feature": base.items["feature"].model_copy(
            update={"validators": ["ref_rule_target_present:contract"]}
        ),
    }
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))
    assert spec.items["feature"].validators == ["ref_rule_target_present:contract"]


def test_a_bare_catalog_name_addition_is_accepted() -> None:
    base = bundled_spec()
    items = {
        **base.items,
        "decision": base.items["decision"].model_copy(update={"validators": ["no_parent"]}),
    }
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))
    assert spec.items["decision"].validators == ["no_parent"]


def test_the_engine_actually_runs_a_types_own_validators_addition() -> None:
    """Proves the assignment surface reaches the engine, not just the spec model: a ``work``
    type's own ``validators`` addition (``no_parent`` on ``bug`` — not in the ``work`` category
    bundle) fires in both ``report()`` and ``gate()`` for a parented instance of that type."""
    base = bundled_spec()
    items = {
        **base.items,
        "bug": base.items["bug"].model_copy(update={"validators": ["no_parent"]}),
    }
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))

    parent = Item(
        sequence_id=1,
        type="task",
        prefix="TASK",
        title="p",
        slug="p",
        status="Draft",
        path="tasks/TASK-000001-p.md",
        created_at=_NOW,
        updated_at=_NOW,
    )
    bug = Item(
        sequence_id=2,
        type="bug",
        prefix="BUG",
        title="b",
        slug="b",
        status="Open",
        parent=parent.id,
        path="bugs/BUG-000002-b.md",
        created_at=_NOW,
        updated_at=_NOW,
    )
    db = SquadsDB(counter=2)
    db.add(parent)
    db.add(bug)

    engine = ValidatorEngine(spec=spec, squad_global={})
    issues = engine.report(db, {})
    assert any(i.item == bug.id and "no parent" in i.message for i in issues)
    with pytest.raises(SquadsError, match="no parent"):
        engine.gate(bug, db)


# --------------------------------------------------------------------------- parse_validator_entry


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("no_parent", ("no_parent", None, None)),
        ("subentity_title_max:80", ("subentity_title_max", "80", None)),
        ("parent_present@warn", ("parent_present", None, "warn")),
        ("subentity_title_max:80@warn", ("subentity_title_max", "80", "warn")),
    ],
)
def test_parse_validator_entry_splits_every_well_formed_shape(
    entry: str, expected: tuple[str, str | None, str | None]
) -> None:
    assert parse_validator_entry(entry) == expected


def test_parse_validator_entry_does_not_accept_a_reversed_composition() -> None:
    """``name@level:param`` is not the grammar — the level separator is split first, so the
    ``:param`` half ends up glued onto what this function treats as the level string, which
    then fails the Plane-1 level check rather than being silently accepted in the wrong order."""
    bare, param, level = parse_validator_entry("parent_present@warn:80")
    assert (bare, param) == ("parent_present", None)
    assert level == "warn:80"


def test_an_at_sign_in_a_ref_rule_target_present_param_mis_splits() -> None:
    """Pins the failure mode ``_LEVEL_SEP``'s own docstring documents: nothing constrains an
    item-type name's character set, so a target type named with ``@`` in it is read as a
    param/level pair instead of one target — the ``@`` is not param-safe for this member's
    param the way it is for a validator name or ``subentity_title_max``'s integer."""
    assert parse_validator_entry("ref_rule_target_present:x@y") == (
        "ref_rule_target_present",
        "x",
        "y",
    )


# --------------------------------------------------------------------------- level suffix


def test_a_declared_level_with_no_param_is_well_formed() -> None:
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(update={"validators": ["parent_present@warn"]}),
    }
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))
    assert spec.items["task"].validators == ["parent_present@warn"]


def test_a_declared_level_composed_with_a_param_is_well_formed() -> None:
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(
            update={"validators": ["subentity_title_max:80@warn"]}
        ),
    }
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))
    assert spec.items["task"].validators == ["subentity_title_max:80@warn"]


def test_an_unknown_level_fails_closed_at_load() -> None:
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(update={"validators": ["parent_present@critical"]}),
    }
    with pytest.raises(SquadsError, match="unknown level"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_a_reversed_level_param_composition_fails_closed_as_an_unknown_level() -> None:
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(
            update={"validators": ["subentity_title_max@warn:80"]}
        ),
    }
    with pytest.raises(SquadsError, match="unknown level"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_a_duplicate_bare_validator_in_one_types_own_list_fails_closed_at_load() -> None:
    base = bundled_spec()
    items = {
        **base.items,
        "decision": base.items["decision"].model_copy(
            update={"validators": ["no_parent", "no_parent@warn"]}
        ),
    }
    with pytest.raises(SquadsError, match="more than once"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


# ----------------------------------------------------- repeated selection vs repeated bare name


def test_two_entries_of_a_parameterized_member_with_different_params_load_clean() -> None:
    """The multi-target-type pattern ``ref_rule_target_present`` is designed for: one entry per
    target type. Two entries naming the same bare validator are refused only when they select
    the same thing — different params is two independent selections, not a repeat."""
    from squads._workflow._models import RefRule

    base = bundled_spec()
    items = {
        **base.items,
        "feature": base.items["feature"].model_copy(
            update={
                "validators": [
                    "ref_rule_target_present:contract",
                    "ref_rule_target_present:decision",
                ],
                "ref_rules": [
                    *base.items["feature"].ref_rules,
                    RefRule(kind="addresses", target="decision"),
                ],
            }
        ),
    }
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))
    assert spec.items["feature"].validators == [
        "ref_rule_target_present:contract",
        "ref_rule_target_present:decision",
    ]


def test_two_entries_of_a_parameterized_member_with_the_same_param_fails_closed_at_load() -> None:
    """Same bare name, same param — nothing decides which of the two entries wins, so this is
    a genuine duplicate, unlike the different-param case above."""
    base = bundled_spec()
    items = {
        **base.items,
        "feature": base.items["feature"].model_copy(
            update={
                "validators": [
                    "ref_rule_target_present:contract",
                    "ref_rule_target_present:contract",
                ]
            }
        ),
    }
    with pytest.raises(SquadsError, match="more than once"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_two_differently_thresholded_subentity_title_max_entries_fail_closed_at_load() -> None:
    """``subentity_title_max`` is parameterized but NOT in
    ``MULTI_SELECTION_VALIDATOR_NAMES`` — unlike ``ref_rule_target_present``, its own resolver
    (``WorkflowSpec.item_subentity_title_max``) returns on the first matching entry rather than
    unioning every one, so a second, differently-thresholded entry is not an independent
    selection. It is refused the same as any other repeat, not silently accepted as one that
    would resolve to 50 and leave 80 permanently inert."""
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(
            update={"validators": ["subentity_title_max:50", "subentity_title_max:80"]}
        ),
    }
    with pytest.raises(SquadsError, match="more than once"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_two_entries_of_a_non_parameterized_member_are_still_a_duplicate_regardless_of_level() -> (
    None
):
    """A member outside ``PARAMETERIZED_VALIDATOR_NAMES`` has no param to differ on — a repeat
    is always the same selection, whatever ``@<level>`` suffix each copy carries. Same case as
    the bare-vs-bare duplicate test above, phrased with two different level suffixes to show
    the level plays no part in the identity."""
    base = bundled_spec()
    items = {
        **base.items,
        "decision": base.items["decision"].model_copy(
            update={"validators": ["no_parent@warn", "no_parent@error"]}
        ),
    }
    with pytest.raises(SquadsError, match="more than once"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_the_refusal_names_the_reason_for_a_differing_param_on_a_single_selection_member() -> None:
    """Two visibly different entries of ``subentity_title_max`` are refused as one selection —
    the message must say *why* rather than just asserting they're "the same selection": this
    member reads only its first matching entry, so a second would be silently inert."""
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(
            update={"validators": ["subentity_title_max:50", "subentity_title_max:80"]}
        ),
    }
    with pytest.raises(SquadsError, match="resolves only its first matching entry"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_the_refusal_names_the_reason_for_a_differing_level_with_no_param_involved() -> None:
    """Two ``no_parent`` entries differing only by ``@<level>`` give the other reason: no param
    is involved here, so the message must point at the level suffix instead of at param
    resolution — a single explanation for both cases would be wrong for one of them."""
    base = bundled_spec()
    items = {
        **base.items,
        "decision": base.items["decision"].model_copy(
            update={"validators": ["no_parent@warn", "no_parent@error"]}
        ),
    }
    with pytest.raises(SquadsError, match="does not make two entries independent selections"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


# --------------------------------------------------------------------------- declared floor


@pytest.mark.parametrize("entry", ["parent_acyclic@warn", "subentity_container_marker@warn"])
def test_a_floor_member_refuses_a_level_below_its_floor(entry: str) -> None:
    base = bundled_spec()
    items = {**base.items, "task": base.items["task"].model_copy(update={"validators": [entry]})}
    with pytest.raises(SquadsError, match="floor"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


@pytest.mark.parametrize("entry", ["parent_acyclic@error", "subentity_container_marker@error"])
def test_a_floor_member_accepts_a_level_at_its_floor(entry: str) -> None:
    base = bundled_spec()
    items = {**base.items, "task": base.items["task"].model_copy(update={"validators": [entry]})}
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))
    assert spec.items["task"].validators == [entry]


@pytest.mark.parametrize(
    "entry",
    [
        "parent_present@warn",  # the deliberate exception this dimension exists to unlock
        "item_status_valid@warn",
        "parent_in@warn",
    ],
)
def test_a_member_with_no_floor_accepts_a_level_lower_than_its_default(entry: str) -> None:
    base = bundled_spec()
    items = {**base.items, "task": base.items["task"].model_copy(update={"validators": [entry]})}
    spec = WorkflowSpec.model_validate(_spec_dict(base, items))
    assert spec.items["task"].validators == [entry]


def test_parent_present_carries_no_floor_entry() -> None:
    from squads._workflow._models import VALIDATOR_LEVEL_FLOOR

    assert "parent_present" not in VALIDATOR_LEVEL_FLOOR


# --------------------------------------------------------------------------- threshold param


@pytest.mark.parametrize("param", ["0", "-5", "abc", "12.5"])
def test_a_non_positive_integer_subentity_title_max_param_fails_closed_at_load(
    param: str,
) -> None:
    base = bundled_spec()
    items = {
        **base.items,
        "task": base.items["task"].model_copy(
            update={"validators": [f"subentity_title_max:{param}"]}
        ),
    }
    with pytest.raises(SquadsError, match="non-positive-integer"):
        WorkflowSpec.model_validate(_spec_dict(base, items))
