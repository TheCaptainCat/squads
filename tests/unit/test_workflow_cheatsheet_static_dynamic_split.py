"""The static (non-generated) cheatsheet sections — Retype, Remove vs. Cancel, Ref kinds —
are present and byte-identical whether the active spec is bundled-only or has a custom type
added; the generic (spec-derived) parts append around them without disturbing them. The one
deliberate exception is the "Valid targets:" retype-list line, which IS spec-derived (a custom
type appears in it) — everything from "Status behaviour:" onward must never change.
"""

from pathlib import Path

from squads._models._item import VALID_REF_KINDS
from squads._rendering._engine import render
from squads._workflow import bundled_spec, load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

_DOCS_STABILITY = Path(__file__).parents[2] / "docs" / "stability.md"

_STATIC_SECTIONS = ["## Retype", "## Remove vs. Cancel", "## Ref kinds"]
_STATIC_RETYPE_INTRO = (
    "Reclassify a work item to a different type — the sequence number (and durable identity) is"
)
_STATIC_REFKINDS_INTRO = (
    "The vocabulary is closed — exactly nine kinds, no custom extensions in 1.0."
)


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


def test_the_ref_kind_cheatsheet_table_has_one_row_per_valid_ref_kind() -> None:
    """The reference claimed eight kinds and eight table rows while
    ``VALID_REF_KINDS`` already held nine (missing ``scopes``) — a count correction, not a
    vocabulary change. Pinning the cheatsheet's row count to the live set's size, rather than a
    literal ``9``, is what keeps this from drifting silently again."""
    rendered = render("workflow.md.j2", spec=bundled_spec())
    ref_kinds_section = rendered[rendered.find("## Ref kinds") :]
    table_rows = [
        ln for ln in ref_kinds_section.splitlines() if ln.startswith("| `") and ln.endswith("|")
    ]
    assert len(table_rows) == len(VALID_REF_KINDS)
    assert "`scopes`" in ref_kinds_section


def test_docs_stability_states_the_same_ref_kind_count_as_the_live_vocabulary() -> None:
    assert len(VALID_REF_KINDS) == 9  # pins the word below to the actual count
    text = _DOCS_STABILITY.read_text(encoding="utf-8")
    assert "The nine built-in kinds are frozen" in text
    assert "`scopes`" in text
    assert "The eight built-in kinds" not in text
