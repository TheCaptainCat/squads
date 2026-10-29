"""A sub-entity head shows the declared fields and the mapping under the target kind's label, and a
template reading a name it no longer receives fails naming it. No command re-renders a head, so the
renderer is called directly, on the override squad's spec and templates."""

from typing import Any

import pytest

from squads import _discussion as discussion
from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._workflow._loader import load_workflow_spec


def _head(override_project, **state: Any) -> str:
    spec = load_workflow_spec(override_project.squad_dir)
    opened = markers.open_marker(discussion.body_tag("action", "AC1"))
    closed = markers.close_marker(discussion.body_tag("action", "AC1"))
    text = f"### AC1 — Draft it\n\n{opened}\nBody\n{closed}\n"
    return discussion.set_head(
        text,
        "action",
        "AC1",
        spec=spec,
        from_squad=override_project.squad_dir,
        **state,
    )


def test_a_head_shows_the_declared_fields_and_the_mapping_under_the_target_kinds_label(
    override_project,
) -> None:
    head = _head(
        override_project,
        status="Todo",
        field_values={"impact": "large"},
        mapping="OC1 — Fifty active teams",
        assignee_name="Catherine Manager",
    )
    assert "**Impact:** 🔴 Large" in head
    assert "**Outcome:** OC1 — Fifty active teams" in head
    assert "Implements" not in head
    assert "Severity" not in head


def test_a_head_template_reading_a_removed_name_fails_naming_it(override_project) -> None:
    templates = override_project.squad_dir / ".overrides" / "templates" / "subentities"
    templates.mkdir(parents=True)
    (templates / "head.md.j2").write_text("{{ severity_label }}\n", encoding="utf-8")
    with pytest.raises(SquadsError, match="'severity_label' is undefined"):
        _head(override_project, status="Todo")
