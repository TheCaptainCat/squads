"""``sq workflow``'s alias table for a custom type: the canonical name/alias/example-command
row, alongside every bundled type's own row (nothing is displaced); the custom type's
lifecycle in the table is auto-linearized straight from the live spec (ties the linearizer,
tests/unit/test_linearize_lifecycle.py, into this rendering path); and the raw rendered
markdown carries no ANSI escapes.
"""

from squads._rendering._engine import render
from squads._workflow import bundled_spec, linearize_lifecycle, load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

_EXPECTED_INCIDENT_LIFECYCLE = "Open → Done (+ WontFix)"


def _spec_with_incident() -> WorkflowSpec:
    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open", transitions={"Open": ["Done", "WontFix"], "Done": [], "WontFix": ["Open"]}
    )
    incident = ItemSpec(prefix="INC", folder="incidents", lifecycle="triage", aliases=["inc"])
    return WorkflowSpec.model_validate(
        {
            "items": {**base.items, "incident": incident},
            "statuses": base.statuses,
            "lifecycles": {**base.lifecycles, "triage": triage},
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": {**base.alias_to_type, "inc": "incident"},
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
        }
    )


def test_custom_type_alias_and_example_appear_in_the_table() -> None:
    rendered = render("workflow.md.j2", spec=_spec_with_incident())
    assert "| `incident` |" in rendered
    assert "`inc`" in rendered
    assert "`sq inc <n> show`" in rendered


def test_every_bundled_type_alias_still_present_alongside_the_custom_type() -> None:
    rendered = render("workflow.md.j2", spec=_spec_with_incident())
    for canonical, alias in [
        ("epic", "e"),
        ("feature", "f"),
        ("task", "t"),
        ("bug", "b"),
        ("decision", "d"),
        ("review", "r"),
        ("guide", "g"),
    ]:
        assert f"| `{canonical}` |" in rendered
        assert f"`{alias}`" in rendered


def test_the_custom_types_table_lifecycle_is_auto_linearized_from_the_live_spec() -> None:
    spec = _spec_with_incident()
    lifecycle_str = linearize_lifecycle(spec.machine_for("incident"))
    assert lifecycle_str == _EXPECTED_INCIDENT_LIFECYCLE


def test_raw_rendered_markdown_carries_no_ansi_escapes() -> None:
    rendered = render("workflow.md.j2", spec=bundled_spec())
    assert "\x1b[" not in rendered
