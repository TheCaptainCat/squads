"""The workflow cheatsheet (``workflow.md.j2``) embeds two spec-derived Mermaid diagrams: an
item-type hierarchy ``flowchart`` and a per-type lifecycle ``stateDiagram-v2``. Both must be
fenced, reflect the *active* spec (a renamed/custom type shows up, the bundled literal it
replaced does not leak), and render deterministically (no set-iteration-order flakiness).
"""

from squads._rendering._engine import render
from squads._workflow import bundled_spec
from squads._workflow._models import Lifecycle, WorkflowSpec


def _hierarchy_section(rendered: str) -> str:
    return rendered.split("## Item hierarchy")[1].split("## Type-command aliases")[0]


def _lifecycles_section(rendered: str) -> str:
    return rendered.split("## Type lifecycles")[1]


def test_hierarchy_flowchart_is_fenced_and_reflects_the_bundled_parent_chain() -> None:
    rendered = render("workflow.md.j2", spec=bundled_spec())
    section = _hierarchy_section(rendered)
    assert "```mermaid" in section
    assert "flowchart TD" in section
    assert section.count("```") == 2
    assert 'epic["epic"] --> feature["feature"]' in section
    assert 'feature["feature"] --> task["task"]' in section


def test_per_type_lifecycle_state_diagram_is_fenced_with_edges_and_terminal_markers() -> None:
    rendered = render("workflow.md.j2", spec=bundled_spec())
    section = _lifecycles_section(rendered)
    assert "```mermaid" in section
    assert "stateDiagram-v2" in section
    assert "`guide` lifecycle:" in section
    guide_block = section.split("`guide` lifecycle:")[1].split("```")[1]
    assert "[*] --> Draft" in guide_block
    assert "Draft --> Published" in guide_block
    assert "Published --> Deprecated" in guide_block
    assert "Deprecated --> [*]" in guide_block  # Deprecated is terminal
    assert "Draft --> [*]" not in guide_block  # Draft is not terminal


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
        }
    )


def test_a_renamed_type_appears_in_both_diagrams_and_the_bundled_name_does_not_leak() -> None:
    rendered = render("workflow.md.j2", spec=_renamed_task_spec())
    hierarchy = _hierarchy_section(rendered)
    lifecycles = _lifecycles_section(rendered)

    assert 'ticket["ticket"]' in hierarchy
    assert 'task["task"]' not in hierarchy

    assert "`ticket` lifecycle:" in lifecycles
    assert "`task` lifecycle:" not in lifecycles


def test_diagram_rendering_is_deterministic_across_repeated_calls() -> None:
    """Lifecycle.states is a frozenset (hash-seed-ordered) — the diagram must not depend on
    its iteration order to stay byte-stable across ``sq sync`` runs."""
    spec = bundled_spec()
    first = render("workflow.md.j2", spec=spec)
    second = render("workflow.md.j2", spec=spec)
    assert first == second


def test_a_custom_lifecycle_renders_every_transition_and_terminal_marker() -> None:
    """A small, hand-built machine (distinct from any bundled one) asserted edge-by-edge,
    independent of the real task/feature machine's larger transition set."""
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
        }
    )
    rendered = render("workflow.md.j2", spec=spec)
    block = _lifecycles_section(rendered).split("`incident` lifecycle:")[1].split("```")[1]
    assert "[*] --> Open" in block
    assert "Open --> Done" in block
    assert "Open --> WontFix" in block
    assert "WontFix --> Open" in block
    assert "Done --> [*]" in block  # Done is terminal
    assert "WontFix --> [*]" in block  # WontFix is terminal
    assert "Open --> [*]" not in block  # Open is not terminal
