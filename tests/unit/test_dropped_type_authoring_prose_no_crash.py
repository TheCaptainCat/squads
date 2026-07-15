"""A second instance of the F1 genericity-failure family (the sibling instance is the per-item
skill's frozen-lifecycle fallback, tests/integration/test_item_skill_body_generation.py): the
workflow cheatsheet and the CLAUDE.md section both render without crashing when a type the
authoring-prose logic expects to exist (e.g. "task") has been dropped from the active spec —
that type's own authoring bullet simply disappears, everything else renders unaffected. Also:
a custom type with a declared sub-entity kind appears in the rendered sub-entities summary,
proving that participation is derived from the spec rather than hardcoded to the three
bundled hosts (feature/task/review).
"""

from squads._rendering._engine import render
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec


def test_dropping_task_from_the_spec_does_not_crash_the_workflow_cheatsheet() -> None:
    base = bundled_spec()
    dropped = {k: v for k, v in base.items.items() if k != "task"}
    spec = base.model_copy(update={"items": dropped})
    rendered = render("workflow.md.j2", spec=spec)
    authoring_section = rendered.split("## Type-command aliases")[0]
    assert "Tech lead" not in authoring_section  # task's only lane owner, no longer authored
    assert "**Product owner** → `sq create epic" in authoring_section  # others unaffected


def test_dropping_task_from_the_spec_does_not_crash_the_claude_md_section() -> None:
    base = bundled_spec()
    dropped = {k: v for k, v in base.items.items() if k != "task"}
    spec = base.model_copy(update={"items": dropped})
    rendered = render(
        "claude/claude_section.md.j2",
        squad_dir="squads",
        roles=[],
        operators=[],
        default_role_full_name="Catherine Manager",
        default_role_slug="manager",
        spec=spec,
        board_lines=[],
    )
    assert "The **product owner** authors **epics**" in rendered  # rendered past the crash


def test_a_custom_type_with_a_subentity_kind_appears_in_the_generic_summary_line() -> None:
    base = bundled_spec()
    new_items = dict(base.items)
    new_items["incident"] = base.items["bug"].model_copy(
        update={
            "prefix": "INC",
            "folder": "incidents",
            "aliases": ["inc"],
            "subentity_kind": "finding",
        }
    )
    spec = WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": {**base.alias_to_type, "inc": "incident"},
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    rendered = render("workflow.md.j2", spec=spec)
    summary_line = next(ln for ln in rendered.splitlines() if "Sub-entities are tracked too" in ln)
    assert "`incident` → `finding`" in summary_line
