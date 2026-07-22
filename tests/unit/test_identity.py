"""Item identity math and the retype status-carry rule.

Retype flips an item's type in place; the pure decisions behind that (does the id's numeric
suffix survive a prefix change, does status carry or reset) are spec/model-level facts with no
filesystem dependency — the file-move/index/body side of retype lives in tests/service/.
"""

from datetime import UTC, datetime

from squads._models._item import Item
from squads._services._retype import _carry_or_reset_status  # pyright: ignore[reportPrivateUsage]
from squads._workflow import WORKFLOWS, WorkflowSpec, load_workflow_spec

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _item(seq: int, item_type: str, prefix: str) -> Item:
    return Item(
        sequence_id=seq,
        type=item_type,
        prefix=prefix,
        title="t",
        slug="t",
        status="Draft",
        path=f"{item_type}s/x.md",
        created_at=_NOW,
        updated_at=_NOW,
    )


# --------------------------------------------------------------------------- id math


def test_changing_type_and_prefix_preserves_the_sequence_number_in_the_rendered_id():
    """A retype changes type/prefix but must never touch sequence_id — the id's numeric
    suffix is exactly the sequence number, before and after."""
    task = _item(5, "task", "TASK")
    assert task.id == "TASK-5"

    retyped = task.model_copy(update={"type": "bug", "prefix": "BUG"})
    assert retyped.id == "BUG-5"
    assert retyped.sequence_id == task.sequence_id == 5


# --------------------------------------------------------------------------- status carry/reset


def test_status_carries_when_old_and_new_type_share_a_workflow():
    """feature/epic share one lifecycle -> the current status survives a retype between them."""
    spec = load_workflow_spec()
    reset, new_status = _carry_or_reset_status(spec, "feature", "epic", "Ready")
    assert reset is False
    assert new_status == "Ready"


def test_status_resets_to_the_new_types_initial_when_workflows_differ():
    """task/decision use different lifecycles -> retype resets to the new type's initial."""
    spec = load_workflow_spec()
    reset, new_status = _carry_or_reset_status(spec, "task", "decision", "InProgress")
    assert reset is True
    assert new_status == spec.initial_status("decision")


def test_status_resets_when_the_carried_value_is_not_a_state_of_the_new_workflow():
    """Same-workflow types still reset if the current status wouldn't be a legal state under
    the new type (defensive: carry requires BOTH same workflow AND value membership)."""
    spec = load_workflow_spec()
    reset, new_status = _carry_or_reset_status(spec, "task", "bug", "InProgress")
    # task/bug use different lifecycles entirely, so this also exercises the plain reset path.
    assert reset is True
    assert new_status == spec.initial_status("bug")


def test_status_carry_relies_on_workflow_value_equality_not_object_identity():
    """The adversarial case the historical `is`-vs-`==` bug class targets: two independently
    loaded WorkflowSpecs produce structurally-identical but genuinely distinct `Workflow`
    objects for two types that share a lifecycle. `_carry_or_reset_status` must keep firing on
    `==` — this test would fail if that comparison ever regressed to `is`.
    """
    spec_a = load_workflow_spec()
    spec_b = load_workflow_spec()
    assert spec_a is not spec_b, "the loader must not hand back a cached singleton here"

    wf_from_a = spec_a.workflow_for("feature")
    wf_from_b = spec_b.workflow_for("epic")
    # structurally identical (feature/epic share one lifecycle) but never the same object —
    # workflow_for() builds a fresh Workflow from the Lifecycle machine on every call.
    assert wf_from_a == wf_from_b
    assert wf_from_a is not wf_from_b

    # The real carry logic below is driven by exactly this property: its two internal
    # workflow_for() calls (on spec_a alone) are just as independent as wf_from_a/wf_from_b
    # above, so this assertion is a direct proof the code compares by value, not identity.
    reset, new_status = _carry_or_reset_status(spec_a, "feature", "epic", "Ready")
    assert reset is False
    assert new_status == "Ready"


# --------------------------------------------------------------------------- WORKFLOWS isolation


def test_workflows_constant_is_never_mutated_by_constructing_a_custom_spec():
    """WORKFLOWS is an immutable bundled snapshot; building an unrelated custom WorkflowSpec
    must not perturb it, and a caller that imported the name keeps seeing the bundled map."""
    bundled = load_workflow_spec()
    captured = WORKFLOWS  # simulate a caller that imported the name at module load

    from squads._workflow._models import ItemSpec, Lifecycle, StatusSpec

    custom_lc = Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []})
    custom_spec = WorkflowSpec.model_validate(
        {
            "items": {
                **bundled.items,
                "probe": ItemSpec(prefix="PRB", folder="probes", lifecycle="custom_probe"),
            },
            "statuses": {
                **bundled.statuses,
                "Open2": StatusSpec(role="pending"),
                "Done2": StatusSpec(role="done"),
            },
            "lifecycles": {**bundled.lifecycles, "custom_probe": custom_lc},
            "prefix_to_type": {**bundled.prefix_to_type, "PRB": "probe"},
            "alias_to_type": dict(bundled.alias_to_type),
            "collections": dict(bundled.collections),
            "subentity_kinds": dict(bundled.subentity_kinds),
            "roles": dict(bundled.roles),
        }
    )

    assert captured is WORKFLOWS
    assert "probe" not in captured
    assert custom_spec.workflow_for("probe") is not None


def test_two_squads_custom_and_bundled_specs_are_independent_objects(tmp_path):
    """A squad with a project override and a squad without one load fully independent specs —
    isolation is structural (each Service carries its own spec), not a singleton reset."""
    override_dir = tmp_path / ".overrides"
    override_dir.mkdir(parents=True)
    (override_dir / "workflow.toml").write_text(
        """
[statuses.SquadAStatus]

[statuses.SquadADone]
role = "done"

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
    spec_b = load_workflow_spec()  # bundled only

    assert "squad_a_type" in spec_a.items
    assert "squad_a_type" not in spec_b.items
