"""``ItemSpec.order`` — the float-valued display/CLI-registration sequencing flag: bundled work
types carry ascending, gapped (not consecutive) float values in today's logical sequence; an
omitted ``order`` defaults to ``+inf`` (sorts last); and a fractional custom order lands
between two bundled types with zero renumbering of the rest.
"""

import math

from squads._workflow import load_workflow_spec
from squads._workflow._models import ItemSpec, WorkflowSpec


def test_bundled_work_types_carry_ascending_gapped_float_orders() -> None:
    spec = load_workflow_spec()
    sequence = ["epic", "feature", "task", "bug", "decision", "review", "guide"]
    orders = [spec.items[t].order for t in sequence]
    assert orders == sorted(orders)
    assert all(isinstance(o, float) for o in orders)
    assert orders == [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]  # gapped by 10, room to insert


def test_an_omitted_order_defaults_to_positive_infinity_and_sorts_last() -> None:
    assert ItemSpec(prefix="INC", folder="incidents", lifecycle="work").order == math.inf


def test_a_fractional_custom_order_lands_between_two_bundled_types_with_no_renumbering() -> None:
    base = load_workflow_spec()
    new_items = dict(base.items)
    new_items["incident"] = ItemSpec(prefix="INC", folder="incidents", lifecycle="work", order=35.5)
    spec = WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
        }
    )
    ordered = sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t))
    assert ordered.index("task") < ordered.index("incident") < ordered.index("bug")
