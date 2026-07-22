"""The bundled spec is a tested artifact (P2): no parent-cycle in the type-parent graph, the
module-level ``WORKFLOWS`` snapshot is immutable and never mutated by constructing a custom
spec, and every squad's (possibly overridden) spec is independent of every other squad's.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._workflow import WORKFLOWS, WorkflowSpec, bundled_spec, load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, StatusSpec


def _extra_lifecycle() -> Lifecycle:
    return Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []})


# --------------------------------------------------------------------------- parent cycles


@pytest.mark.parametrize(
    "parent_map",
    [
        {"a": ["b"], "b": ["a"]},
        {"a": ["c"], "b": ["a"], "c": ["b"]},
    ],
    ids=["direct-cycle", "three-node-cycle"],
)
def test_a_cycle_in_the_type_parent_graph_raises(parent_map: dict[str, list[str]]) -> None:
    bundled = bundled_spec()
    new_items = dict(bundled.items)
    new_prefix_to_type = dict(bundled.prefix_to_type)
    for name, parents in parent_map.items():
        new_items[name] = ItemSpec(
            prefix=name.upper() * 3, folder=f"{name}s", lifecycle="work", parents=parents
        )
        new_prefix_to_type[name.upper() * 3] = name
    with pytest.raises(SquadsError, match="cycle"):
        WorkflowSpec.model_validate(
            {
                "items": new_items,
                "statuses": dict(bundled.statuses),
                "lifecycles": dict(bundled.lifecycles),
                "prefix_to_type": new_prefix_to_type,
                "alias_to_type": dict(bundled.alias_to_type),
                "collections": dict(bundled.collections),
                "subentity_kinds": dict(bundled.subentity_kinds),
            }
        )


def test_the_bundled_spec_itself_has_no_parent_cycle() -> None:
    assert load_workflow_spec() is not None  # would have raised above if cyclic


# --------------------------------------------------------------------------- immutable snapshot


def test_workflows_dict_is_a_stable_immutable_bundled_snapshot() -> None:
    """Constructing a custom ``WorkflowSpec`` never mutates the module-level ``WORKFLOWS`` a
    caller imported earlier — each spec carries its own workflow map via ``workflow_for()``."""
    bundled = load_workflow_spec()
    captured = WORKFLOWS

    custom_spec = WorkflowSpec.model_validate(
        {
            "items": {
                **bundled.items,
                "probe": ItemSpec(prefix="PRB", folder="probes", lifecycle="custom_probe"),
            },
            "statuses": {
                **bundled.statuses,
                "Open2": StatusSpec(terminal=False),
                "Done2": StatusSpec(terminal=True),
            },
            "lifecycles": {**bundled.lifecycles, "custom_probe": _extra_lifecycle()},
            "prefix_to_type": {**bundled.prefix_to_type, "PRB": "probe"},
            "alias_to_type": dict(bundled.alias_to_type),
            "collections": dict(bundled.collections),
            "subentity_kinds": dict(bundled.subentity_kinds),
        }
    )

    assert captured is WORKFLOWS
    assert "probe" not in WORKFLOWS
    assert custom_spec.workflow_for("probe") is not None
    assert bundled_spec() is bundled_spec()  # always the same cached singleton


def test_two_squads_overridden_specs_are_independent(tmp_path: Path) -> None:
    override_dir = tmp_path / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        """
[statuses.SquadAStatus]
terminal = false
[statuses.SquadADone]
terminal = true

[lifecycles.squad_a_lc]
initial = "SquadAStatus"
[lifecycles.squad_a_lc.transitions]
SquadAStatus = ["SquadADone"]
SquadADone = []

[items.squad_a_type]
prefix = "SQA"
folder = "squad_a_types"
lifecycle = "squad_a_lc"
""",
        encoding="utf-8",
    )
    spec_a = load_workflow_spec(squad_dir=tmp_path)
    spec_b = load_workflow_spec()  # a different squad, no override

    assert "squad_a_type" in spec_a.items
    assert "squad_a_type" not in spec_b.items
    assert "squad_a_type" not in WORKFLOWS


def test_load_workflow_spec_with_no_squad_dir_matches_the_bundled_singleton() -> None:
    spec_a = load_workflow_spec()
    spec_b = load_workflow_spec(squad_dir=None)
    assert set(spec_a.items) == set(spec_b.items)
    assert set(spec_a.statuses) == set(spec_b.statuses)
    assert spec_a.terminal_set() == spec_b.terminal_set()


# --------------------------------------------------------------------------- alias-table defense
# A spec-artifact regression floor, not a custom-type concern — a built-in work type declared
# with no alias would silently vanish from the alias cheatsheet with no other signal.


def test_every_builtin_work_type_declares_at_least_one_alias() -> None:
    spec = bundled_spec()
    alias_less = [t for t in spec.non_roster_types() if not spec.items[t].aliases]
    assert not alias_less
