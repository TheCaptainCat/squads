"""``sq workflow types`` — the type-catalog machine surface.

Default prints a human Rich table; ``--json`` emits the frozen bare-array shape
(``{type, order, prefix, reserved}``) in ascending resolved order, type-name tiebreak.
The byte-identical golden is pinned in ``tests/cli/test_json_output_shape.py``
(``tests/goldens/workflow_types.json``) — this module covers the field-set/model
contract, the null-order representation, and the human table.
"""

import json
import math

import pytest

from squads._cli._workflow_cmd import (
    TYPE_CATALOG_FIELDS,
    _type_catalog,  # pyright: ignore[reportPrivateUsage]
)
from squads._workflow import load_workflow_spec
from squads._workflow._models import ItemSpec, WorkflowSpec

pytestmark = pytest.mark.anyio


# ─── CLI surface ────────────────────────────────────────────────────────────────


async def test_default_output_is_a_human_table_with_every_declared_type(project, invoke) -> None:
    result = await invoke(["workflow", "types"])
    assert result.exit_code == 0
    for col in ("Type", "Order", "Prefix", "Reserved"):
        assert col in result.output
    for t in (
        "epic",
        "feature",
        "task",
        "bug",
        "decision",
        "review",
        "guide",
        "role",
        "skill",
        "operator",
    ):
        assert t in result.output


async def test_json_emits_a_bare_array_of_every_declared_type_in_ascending_order(
    project, invoke
) -> None:
    result = await invoke(["workflow", "types", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert isinstance(rows, list)
    types = [r["type"] for r in rows]
    # bundled default: epic..guide=10..70 (work), role/skill/operator=80..100 (reserved).
    assert types == [
        "epic",
        "feature",
        "task",
        "bug",
        "decision",
        "review",
        "guide",
        "role",
        "skill",
        "operator",
    ]
    orders = [r["order"] for r in rows]
    assert orders == sorted(orders)


async def test_json_reserved_flag_matches_the_meta_types(project, invoke) -> None:
    result = await invoke(["workflow", "types", "--json"])
    rows = {r["type"]: r for r in json.loads(result.output)}
    for t in ("role", "skill", "operator"):
        assert rows[t]["reserved"] is True
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert rows[t]["reserved"] is False


async def test_json_prefix_matches_the_spec(project, invoke) -> None:
    result = await invoke(["workflow", "types", "--json"])
    rows = {r["type"]: r for r in json.loads(result.output)}
    spec = load_workflow_spec()
    for t, ts in spec.items.items():
        assert rows[t]["prefix"] == ts.prefix


# ─── field-set / model contract ─────────────────────────────────────────────────


def test_frozen_field_set_is_exactly_type_order_prefix_reserved() -> None:
    assert TYPE_CATALOG_FIELDS == ("type", "order", "prefix", "reserved")


def test_every_catalog_row_has_exactly_the_frozen_field_set() -> None:
    spec = load_workflow_spec()
    for row in _type_catalog(spec):
        assert set(row.keys()) == set(TYPE_CATALOG_FIELDS)


def test_order_and_prefix_and_is_meta_are_real_itemspec_fields() -> None:
    """The catalog's ``order``/``prefix`` are read verbatim off ``ItemSpec``, and
    ``reserved`` mirrors ``ItemSpec.is_meta`` — guards against a stray field name that
    doesn't actually trace back to the model."""
    assert "order" in ItemSpec.model_fields
    assert "prefix" in ItemSpec.model_fields
    assert "is_meta" in ItemSpec.model_fields


# ─── null-order representation (unordered/custom type) ─────────────────────────


def _spec_with_unordered_custom_type() -> WorkflowSpec:
    base = load_workflow_spec()
    new_items = dict(base.items)
    new_items["incident"] = ItemSpec(prefix="INC", folder="incidents", lifecycle="work")
    return WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )


def test_an_unordered_type_serializes_order_as_null_and_sorts_last() -> None:
    spec = _spec_with_unordered_custom_type()
    assert math.isinf(spec.items["incident"].order)
    rows = _type_catalog(spec)
    assert rows[-1]["type"] == "incident"
    assert rows[-1]["order"] is None
    # every other (explicitly-ordered) row keeps a real JSON number, never null.
    for row in rows[:-1]:
        assert row["order"] is not None


def test_null_order_round_trips_through_json_dumps() -> None:
    spec = _spec_with_unordered_custom_type()
    rows = _type_catalog(spec)
    dumped = json.loads(json.dumps(rows))
    incident = next(r for r in dumped if r["type"] == "incident")
    assert incident["order"] is None
