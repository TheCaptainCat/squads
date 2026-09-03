"""The workflow cheatsheet's ``## Type lifecycles`` table is the lifecycle surface agents read.

It carries one row per declared non-roster type, with the type's own linearized machine, and it
must follow the *active* spec: a renamed or custom type shows up with its own lifecycle, and the
bundled name it replaced does not leak. The cheatsheet carries no diagram of any kind — the
markup rendered as raw text in the agent-facing skill, where it read as noise beside the prose
that already said the same thing.
"""

from squads._rendering._engine import render
from squads._workflow import bundled_spec
from squads._workflow._models import Lifecycle, WorkflowSpec


def _lifecycles_section(rendered: str) -> str:
    return rendered.split("## Type lifecycles")[1]


def test_the_cheatsheet_embeds_no_diagram_markup() -> None:
    rendered = render("workflow.md.j2", spec=bundled_spec())
    assert "```mermaid" not in rendered
    assert "flowchart" not in rendered
    assert "stateDiagram" not in rendered


def test_every_non_roster_type_has_a_lifecycle_row_and_no_roster_type_does() -> None:
    spec = bundled_spec()
    section = _lifecycles_section(render("workflow.md.j2", spec=spec))
    for item_type in spec.non_roster_types():
        assert f"| `{item_type}` |" in section, item_type
    for roster_type in ("role", "skill", "operator"):
        assert f"| `{roster_type}` |" not in section


def test_a_row_carries_the_types_own_prefix_and_linearized_machine() -> None:
    section = _lifecycles_section(render("workflow.md.j2", spec=bundled_spec()))
    assert "| `GUIDE` | `guide` | `Draft → Published → Deprecated` |" in section
    assert (
        "| `ADR` | `decision` | `Proposed → Accepted → Superseded (+ Rejected, Deprecated)` |"
    ) in section


def _renamed_task_spec() -> WorkflowSpec:
    """The bundled spec with ``task`` renamed to ``ticket`` (same lifecycle/prefix shape,
    different key/prefix/alias) — nothing else references ``task`` as a parent, so this is a
    clean rename."""
    base = bundled_spec()
    items = {k: v for k, v in base.items.items() if k != "task"}
    items["ticket"] = base.items["task"].model_copy(update={"prefix": "TCK", "aliases": ["tk"]})
    prefix_to_type = {k: v for k, v in base.prefix_to_type.items() if v != "task"}
    prefix_to_type["TCK"] = "ticket"
    alias_to_type = {k: v for k, v in base.alias_to_type.items() if v != "task"}
    alias_to_type["tk"] = "ticket"
    return WorkflowSpec.model_validate(
        {
            "items": items,
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": prefix_to_type,
            "alias_to_type": alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
            "ref_kinds": base.ref_kinds,
            "views": base.views,
        }
    )


def test_a_renamed_type_takes_over_its_row_and_the_bundled_name_does_not_leak() -> None:
    section = _lifecycles_section(render("workflow.md.j2", spec=_renamed_task_spec()))
    assert "| `TCK` | `ticket` |" in section
    assert "| `task` |" not in section


def test_a_custom_lifecycle_is_linearized_with_its_own_states() -> None:
    """A small, hand-built machine (distinct from any bundled one), so the row is asserted
    against that machine rather than against the bundled work lifecycle."""
    base = bundled_spec()
    triage = Lifecycle(
        initial="Open", transitions={"Open": ["Done", "WontFix"], "Done": [], "WontFix": ["Open"]}
    )
    items = dict(base.items)
    items["incident"] = base.items["bug"].model_copy(
        update={"prefix": "INC", "folder": "incidents", "aliases": ["inc"], "lifecycle": "triage"}
    )
    spec = WorkflowSpec.model_validate(
        {
            "items": items,
            "statuses": base.statuses,
            "lifecycles": {**base.lifecycles, "triage": triage},
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": {**base.alias_to_type, "inc": "incident"},
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
            "ref_kinds": base.ref_kinds,
            "views": base.views,
        }
    )
    section = _lifecycles_section(render("workflow.md.j2", spec=spec))
    assert "| `INC` | `incident` | `Open → Done (+ WontFix)` |" in section


def test_cheatsheet_rendering_is_deterministic_across_repeated_calls() -> None:
    """Lifecycle.states is a frozenset (hash-seed-ordered) — nothing derived from it may leak
    into the rendered text's ordering, or `sq sync` writes a different file each run."""
    spec = bundled_spec()
    assert render("workflow.md.j2", spec=spec) == render("workflow.md.j2", spec=spec)
