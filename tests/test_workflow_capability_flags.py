"""TASK-000233 — Parts B & C: unit tests for new TypeSpec/StatusSpec capability flags
and the fail-closed hardening (extra=forbid / model_validate).

These test NEW surface only — they do not duplicate the existing golden-lock test.
The golden-lock (test_workflow_spec.py) is the behavioral regression gate; this file
is the forward-looking surface test for the capability flags introduced in TASK-000233.
"""

import math

import pytest

from squads._errors import SquadsError
from squads._workflow._loader import (
    _build_spec,  # pyright: ignore[reportPrivateUsage]
    load_workflow_spec,
)
from squads._workflow._models import ItemSpec, Lifecycle, RefRule, StatusSpec, WorkflowSpec

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def spec() -> WorkflowSpec:
    return load_workflow_spec()


# ---------------------------------------------------------------------------
# is_meta flag
# ---------------------------------------------------------------------------


def test_meta_types_have_is_meta_true(spec: WorkflowSpec) -> None:
    """role/skill/operator all have is_meta=True; all work types have is_meta=False."""
    for t in ("role", "skill", "operator"):
        assert spec.items[t].is_meta is True, f"{t} should have is_meta=True"
    for t in (
        "epic",
        "feature",
        "task",
        "bug",
        "decision",
        "review",
        "guide",
    ):
        assert spec.items[t].is_meta is False, f"{t} should have is_meta=False"


# ---------------------------------------------------------------------------
# subentity_kind flag
# ---------------------------------------------------------------------------


def test_subentity_kind_values(spec: WorkflowSpec) -> None:
    """subentity_kind encodes the correct kind for each type."""
    assert spec.items["feature"].subentity_kind == "story"
    assert spec.items["task"].subentity_kind == "subtask"
    assert spec.items["review"].subentity_kind == "finding"
    # All other types should have no subentity_kind.
    for t in (
        "epic",
        "bug",
        "decision",
        "guide",
        "role",
        "skill",
        "operator",
    ):
        assert spec.items[t].subentity_kind is None, f"{t} should have subentity_kind=None"


def test_item_subentity_kind_returns_none_for_unknown_type(spec: WorkflowSpec) -> None:
    """item_subentity_kind degrades gracefully (None) for a type not declared in the spec.

    A dropped/renamed type must cleanly lose its sub-entity check rather than raise
    KeyError — not triggerable via today's additive-only overrides, but the eventual
    type drop/rename support must not crash the sq-check helpers that call this.
    """
    assert spec.item_subentity_kind("not-a-real-type") is None


# ---------------------------------------------------------------------------
# parent_required flag
# ---------------------------------------------------------------------------


def test_parent_required_only_on_task(spec: WorkflowSpec) -> None:
    """parent_required="feature" on task; all other types have it None."""
    assert spec.items["task"].parent_required == "feature"
    for t in (
        "epic",
        "feature",
        "bug",
        "decision",
        "review",
        "guide",
        "role",
        "skill",
        "operator",
    ):
        assert spec.items[t].parent_required is None, f"{t} should have parent_required=None"


# ---------------------------------------------------------------------------
# ref_rules flag
# ---------------------------------------------------------------------------


def test_task_ref_rules_contain_fixes_and_addresses(spec: WorkflowSpec) -> None:
    """task.ref_rules contains exactly fixes and addresses rules."""
    kinds = {r.kind for r in spec.items["task"].ref_rules}
    assert "fixes" in kinds
    assert "addresses" in kinds


def test_decision_ref_rules_contain_supersedes(spec: WorkflowSpec) -> None:
    """decision.ref_rules contains a supersedes rule."""
    kinds = {r.kind for r in spec.items["decision"].ref_rules}
    assert "supersedes" in kinds


def test_other_types_have_empty_ref_rules(spec: WorkflowSpec) -> None:
    """Types with no special ref rules have an empty ref_rules list."""
    for t in (
        "epic",
        "feature",
        "bug",
        "review",
        "guide",
        "role",
        "skill",
        "operator",
    ):
        assert spec.items[t].ref_rules == [], f"{t} should have empty ref_rules"


def test_ref_rule_model_fields(spec: WorkflowSpec) -> None:
    """Each RefRule carries a kind and (optionally) a hint."""
    for rule in spec.items["task"].ref_rules:
        assert isinstance(rule.kind, str) and rule.kind
        assert isinstance(rule.hint, str)  # may be empty but must be a str


def test_parent_hint_uses_declared_hint_not_literal_kind_detection() -> None:
    """parent_hint appends the RefRule's own declared hint text, not a re-detected
    'fixes'/'addresses' literal + bundled 'bug or review' prose — proven on a renamed
    type/parent with a custom ref rule and hint."""
    custom = WorkflowSpec.model_validate(
        {
            "items": {
                "role": ItemSpec(prefix="ROLE", folder="roles", lifecycle="agent", is_meta=True),
                "skill": ItemSpec(prefix="SKILL", folder="skills", lifecycle="agent", is_meta=True),
                "operator": ItemSpec(
                    prefix="OP", folder="operators", lifecycle="agent", is_meta=True
                ),
                "feat": ItemSpec(prefix="FEAT", folder="feats", lifecycle="work"),
                "chore": ItemSpec(
                    prefix="CHORE",
                    folder="chores",
                    lifecycle="work",
                    parents=["feat"],
                    ref_rules=[RefRule(kind="mends", hint="see `sq ref add <chore> <id>`")],
                ),
            },
            "statuses": {
                "Draft": StatusSpec(terminal=False),
                "Active": StatusSpec(terminal=False),
                "Archived": StatusSpec(terminal=True),
                "Done": StatusSpec(terminal=True),
            },
            "lifecycles": {
                "agent": Lifecycle(
                    initial="Draft", transitions={"Draft": ["Active"], "Active": ["Archived"]}
                ),
                "work": Lifecycle(initial="Draft", transitions={"Draft": ["Done"]}),
            },
            "prefix_to_type": {},
            "alias_to_type": {},
        }
    )
    hint = custom.parent_hint("chore")
    assert hint == "a chore's parent must be of type feat; see `sq ref add <chore> <id>`"


# ---------------------------------------------------------------------------
# ItemSpec.extra_fields flag
# ---------------------------------------------------------------------------


def test_bundled_guide_and_review_declare_extra_fields(spec: WorkflowSpec) -> None:
    """The bundled spec anchors tags/target_ref on guide/review via extra_fields, not a
    hardcoded type-name lookup elsewhere."""
    assert spec.item_extra_fields("guide") == ["tags"]
    assert spec.item_extra_fields("review") == ["target_ref"]


def test_item_extra_fields_empty_for_type_with_none_declared(spec: WorkflowSpec) -> None:
    """A type declaring no extra_fields (e.g. task) resolves to an empty list, not an error."""
    assert spec.item_extra_fields("task") == []


# ---------------------------------------------------------------------------
# StatusSpec.role flag
# ---------------------------------------------------------------------------


def test_superseded_has_role_superseded(spec: WorkflowSpec) -> None:
    """The Superseded status has role='superseded'."""
    assert spec.statuses["Superseded"].role == "superseded"


def test_no_other_status_has_a_role(spec: WorkflowSpec) -> None:
    """No other status has a non-None role value in the default spec."""
    for s, ss in spec.statuses.items():
        if s != "Superseded":
            assert ss.role is None, f"{s} should have role=None, got {ss.role!r}"


# ---------------------------------------------------------------------------
# extra="forbid" on workflow spec models (Part C hardening)
# ---------------------------------------------------------------------------


def test_lifecycle_rejects_unknown_key() -> None:
    """Lifecycle with an unknown key raises ValidationError (extra=forbid)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Lifecycle.model_validate(
            {
                "initial": "Draft",
                "transitions": {},
                "unexpected_key": "boom",
            }
        )


def test_item_spec_rejects_unknown_key() -> None:
    """ItemSpec with an unknown key raises ValidationError (extra=forbid)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ItemSpec.model_validate(
            {
                "prefix": "TST",
                "folder": "tests",
                "lifecycle": "work",
                "unknown_field": "oops",
            }
        )


def test_status_spec_rejects_unknown_key() -> None:
    """StatusSpec with an unknown key raises ValidationError (extra=forbid)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        StatusSpec.model_validate({"terminal": False, "rogue_key": True})


def test_ref_rule_rejects_unknown_key() -> None:
    """RefRule with an unknown key raises ValidationError (extra=forbid)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RefRule.model_validate({"kind": "fixes", "hint": "", "bogus": "data"})


def test_workflow_spec_rejects_unknown_top_level_key() -> None:
    """WorkflowSpec constructed with an unknown top-level key raises (extra=forbid)."""
    from pydantic import ValidationError

    spec = load_workflow_spec()
    # Try to construct a WorkflowSpec with an extra key — should raise.
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        WorkflowSpec.model_validate(
            {
                "items": dict(spec.items),
                "statuses": dict(spec.statuses),
                "lifecycles": dict(spec.lifecycles),
                "prefix_to_type": dict(spec.prefix_to_type),
                "alias_to_type": dict(spec.alias_to_type),
                "totally_bogus": "should_fail",
            }
        )


def test_loader_unknown_toml_key_in_item_raises_squads_error() -> None:
    """An unknown key in an items.* section in TOML causes SquadsError via _build_spec."""
    import tomllib

    # Minimal valid TOML with one item that carries an unknown key.
    toml_text = """
[lifecycles.work]
initial = "Draft"
[lifecycles.work.transitions]
Draft = ["Done"]
Done = []

[lifecycles.agent]
initial = "Draft"
[lifecycles.agent.transitions]
Draft = ["Active"]
Active = ["Archived"]
Archived = ["Active"]

[lifecycles.subtask]
initial = "Todo"
[lifecycles.subtask.transitions]
Todo = ["Done"]
Done = []

[lifecycles.story]
initial = "Todo"
[lifecycles.story.transitions]
Todo = ["Done"]
Done = []

[lifecycles.finding]
initial = "Open"
[lifecycles.finding.transitions]
Open = ["Fixed"]
Fixed = []

[lifecycles.adr]
initial = "Proposed"
[lifecycles.adr.transitions]
Proposed = ["Accepted"]
Accepted = []

[lifecycles.review]
initial = "Requested"
[lifecycles.review.transitions]
Requested = ["Approved"]
Approved = []

[lifecycles.bug]
initial = "Open"
[lifecycles.bug.transitions]
Open = ["Fixed"]
Fixed = []

[lifecycles.guide]
initial = "Draft"
[lifecycles.guide.transitions]
Draft = ["Published"]
Published = []

[statuses.Draft]
terminal = false
[statuses.Done]
terminal = true
[statuses.Active]
terminal = false
[statuses.Archived]
terminal = true
[statuses.Todo]
terminal = false
[statuses.InProgress]
terminal = false
[statuses.Blocked]
terminal = false
[statuses.Cancelled]
terminal = true
[statuses.Ready]
terminal = false
[statuses.InReview]
terminal = false
[statuses.Open]
terminal = false
[statuses.Fixed]
terminal = false
[statuses.Proposed]
terminal = false
[statuses.Accepted]
terminal = true
[statuses.Superseded]
terminal = true
[statuses.Rejected]
terminal = true
[statuses.Deprecated]
terminal = true
[statuses.Requested]
terminal = false
[statuses.ChangesRequested]
terminal = false
[statuses.Approved]
terminal = true
[statuses.Published]
terminal = true
[statuses.WontFix]
terminal = true
[statuses.Verified]
terminal = true

[items.task]
prefix   = "TASK"
folder   = "tasks"
lifecycle = "work"
parents  = ["feature"]
aliases  = ["t"]
UNKNOWN_BOGUS_KEY = "this should fail"

[items.feature]
prefix   = "FEAT"
folder   = "features"
lifecycle = "work"
parents  = ["epic"]
aliases  = ["feat", "f"]

[items.epic]
prefix   = "EPIC"
folder   = "epics"
lifecycle = "work"

[items.bug]
prefix   = "BUG"
folder   = "bugs"
lifecycle = "bug"
aliases  = ["b"]

[items.decision]
prefix   = "ADR"
folder   = "adrs"
lifecycle = "adr"
aliases  = ["dec", "d"]

[items.review]
prefix   = "REV"
folder   = "reviews"
lifecycle = "review"
aliases  = ["rev", "r"]

[items.guide]
prefix   = "GUIDE"
folder   = "guides"
lifecycle = "guide"
aliases  = ["g"]

[items.role]
prefix   = "ROLE"
folder   = "agents/roles"
lifecycle = "agent"

[items.skill]
prefix   = "SKILL"
folder   = "agents/skills"
lifecycle = "agent"

[items.operator]
prefix   = "OP"
folder   = "operators"
lifecycle = "agent"
"""
    raw = tomllib.loads(toml_text)
    with pytest.raises(SquadsError):
        _build_spec(raw)


# ---------------------------------------------------------------------------
# Bundled spec still loads cleanly (regression: new flags don't break the load)
# ---------------------------------------------------------------------------


def test_bundled_spec_loads_with_new_flags() -> None:
    """The bundled default_workflow.toml with the new capability flags still loads cleanly."""
    spec = load_workflow_spec()
    assert spec is not None
    # Spot-check a few flags that must be set.
    assert spec.items["task"].parent_required == "feature"
    assert spec.items["role"].is_meta is True


# ---------------------------------------------------------------------------
# ItemSpec.order — explicit CLI registration/display order, float, +inf default
# ---------------------------------------------------------------------------


def test_order_is_float_with_gapped_values_and_logical_sequence() -> None:
    """Bundled work types carry ascending float `order` values in today's logical sequence."""
    spec = load_workflow_spec()
    sequence = ["epic", "feature", "task", "bug", "decision", "review", "guide"]
    orders = [spec.items[t].order for t in sequence]
    assert orders == sorted(orders), f"{sequence} orders not ascending: {orders}"
    assert all(isinstance(o, float) for o in orders)
    # Gapped (spaced by 10), not consecutive integers — room to insert between any two.
    assert orders == [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]


def test_order_omitted_defaults_to_positive_infinity() -> None:
    """A type that omits `order` defaults to +inf — sorts after every explicit value."""
    assert ItemSpec(prefix="INC", folder="incidents", lifecycle="work").order == math.inf


def test_fractional_custom_order_sorts_between_two_bundled_types() -> None:
    """A custom type with a fractional order (e.g. 35.5) lands between task (30) and bug (40).

    Exercises the exact sort key the CLI's static registration loop uses
    (``key=lambda t: (spec.items[t].order, t)``) so insertion-without-renumbering is proven
    at the data level, independent of the CLI's lazy dynamic-dispatch path for
    project-declared custom types (which is unaffected by `order` and always sorts
    alphabetically after every statically-registered type).
    """
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
        }
    )
    ordered = sorted(spec.work_types(), key=lambda t: (spec.items[t].order, t))
    task_idx = ordered.index("task")
    bug_idx = ordered.index("bug")
    incident_idx = ordered.index("incident")
    assert task_idx < incident_idx < bug_idx, (
        f"expected incident (order=35.5) between task (30) and bug (40); got {ordered}"
    )
    assert spec.statuses["Superseded"].role == "superseded"
