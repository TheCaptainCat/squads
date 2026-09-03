"""The static (non-generated) cheatsheet sections — Retype, Remove vs. Cancel, Ref kinds —
are present and byte-identical whether the active spec is bundled-only or has a custom type
added; the generic (spec-derived) parts append around them without disturbing them. The one
deliberate exception is the "Valid targets:" retype-list line, which IS spec-derived (a custom
type appears in it) — everything from "Status behaviour:" onward must never change.

"Static" describes the *narrative*, not every word inside it: the Ref kinds section's table is
generated from the merged spec's declared kinds, and every kind and status name below it is
resolved from the spec too. The byte-identical guarantee therefore holds for a spec that adds a
type (what the custom spec here does) and is not claimed for one that adds a ref kind — which
gains a row, asserted separately below.
"""

from pathlib import Path

from squads._rendering._engine import render
from squads._workflow import bundled_spec, load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, RefKindSpec, WorkflowSpec

_DOCS_STABILITY = Path(__file__).parents[2] / "docs" / "stability.md"

_STATIC_SECTIONS = ["## Retype", "## Remove vs. Cancel", "## Ref kinds"]
_STATIC_RETYPE_INTRO = (
    "Reclassify a work item to a different type — the sequence number (and durable identity) is"
)
_STATIC_REFKINDS_INTRO = "Ref kinds are declared vocabulary. The bundled set is the default;"


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
            "ref_kinds": base.ref_kinds,
        }
    )


def test_static_sections_present_for_both_bundled_and_custom_specs() -> None:
    for spec in (bundled_spec(), _spec_with_incident()):
        rendered = render("workflow.md.j2", spec=spec)
        for header in _STATIC_SECTIONS:
            assert header in rendered


def test_static_prose_from_status_behaviour_onward_is_byte_identical_bundled_vs_custom() -> None:
    bundled_rendered = render("workflow.md.j2", spec=bundled_spec())
    custom_rendered = render("workflow.md.j2", spec=_spec_with_incident())
    marker = "**Status behaviour:**"
    static_bundled = bundled_rendered[bundled_rendered.find(marker) :]
    static_custom = custom_rendered[custom_rendered.find(marker) :]
    assert static_bundled == static_custom


def test_the_valid_targets_line_is_the_one_deliberately_spec_derived_exception() -> None:
    rendered = render("workflow.md.j2", spec=_spec_with_incident())
    line = next(ln for ln in rendered.splitlines() if ln.startswith("Valid targets:"))
    assert "`incident`" in line
    for builtin in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert f"`{builtin}`" in line


def test_retype_and_refkinds_static_intro_lines_are_exact() -> None:
    rendered = render("workflow.md.j2", spec=_spec_with_incident())
    assert _STATIC_RETYPE_INTRO in rendered
    assert _STATIC_REFKINDS_INTRO in rendered


def _ref_kind_table_rows(rendered: str) -> list[str]:
    section = rendered[rendered.find("## Ref kinds") :]
    return [ln for ln in section.splitlines() if ln.startswith("| `") and ln.endswith("|")]


def test_the_ref_kind_cheatsheet_table_has_one_row_per_declared_kind() -> None:
    """The table is generated from the merged spec, so its size is the declared vocabulary's
    size — never a literal. Every declared kind gets a row, including one whose only consumer
    is a declared view naming it rather than an engine binding: a generated table that hides a
    declared entry would need a "hide me" flag nothing declares."""
    spec = bundled_spec()
    rendered = render("workflow.md.j2", spec=spec)
    rows = _ref_kind_table_rows(rendered)
    assert len(rows) == len(spec.ref_kinds)
    for code in spec.ref_kinds:
        assert any(row.startswith(f"| `{code}` |") for row in rows), code


def test_a_declared_extra_ref_kind_gains_a_row_with_no_template_change() -> None:
    """The adopter case the table exists for: a project declaring its own kind sees it in its
    own cheatsheet — and in the skill text its agents read — without touching the template."""
    base = bundled_spec()
    spec = base.model_copy(
        update={
            "ref_kinds": {
                **base.ref_kinds,
                "escalates": RefKindSpec(label="Escalates", hint="A escalates B to an owner"),
            }
        }
    )
    rows = _ref_kind_table_rows(render("workflow.md.j2", spec=spec))
    assert len(rows) == len(base.ref_kinds) + 1
    assert any(row.startswith("| `escalates` | A escalates B to an owner |") for row in rows)
    assert rows[-1].endswith("| Navigation |")


def test_the_ref_kind_table_names_no_kind_or_status_the_template_hard_codes() -> None:
    """The consumer column and the notes under the table are derived, so a squad that renames
    a kind or a status reads its own names — the defect a hand-written row reintroduces."""
    base = bundled_spec()
    renamed = base.model_copy(
        update={
            "ref_kinds": {
                ("linked" if code == "related" else code): kind
                for code, kind in base.ref_kinds.items()
            }
        }
    )
    section = render("workflow.md.j2", spec=renamed)
    section = section[section.find("## Ref kinds") :]
    assert "`linked` here" in section
    assert "`related`" not in section


def test_docs_stability_states_the_declared_ref_kind_policy() -> None:
    text = _DOCS_STABILITY.read_text(encoding="utf-8")
    assert "The nine built-in kinds are frozen" not in text
    assert "Ref kinds are declared vocabulary." in text
    assert "live-corpus refusal" in text
    assert "declared **semantic role**" in text
