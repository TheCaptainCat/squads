"""``ItemSpec.validators`` — the per-type extend-only assignment surface over the category
default bundle — and its Plane-1 (load-time) catalog-membership check: an unknown validator
name fails closed, and a ``:<param>`` suffix is only well-formed on a name in
``PARAMETERIZED_VALIDATOR_NAMES``. Engine wiring (a type's own additions actually extend its
effective set) lives alongside the routing-task parity tests in ``tests/service/``.
"""

from datetime import UTC, datetime

import pytest

from squads._errors import SquadsError
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._services._validators import ValidatorEngine
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, WorkflowSpec

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
    }


def test_bundled_spec_declares_epics_no_parent_addition_only() -> None:
    """``epic`` is the one built-in type with a ``validators`` addition — its own ``no_parent``,
    enforcing the work-root constraint (``records``' ``no_parent`` comes from the category
    bundle instead, not a per-type addition)."""
    spec = bundled_spec()
    assert spec.items["epic"].validators == ["no_parent"]
    assert all(ts.validators == [] for t, ts in spec.items.items() if t != "epic")


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
