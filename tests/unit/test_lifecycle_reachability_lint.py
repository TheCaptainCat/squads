"""The lifecycle-graph reachability lint (distinct from the override-MERGE-error lint family
in tests/unit/test_workflow_lint_merge_errors.py — same command, different failure family):
a transition target off the declared status vocabulary fails closed and names the offending
lifecycle; a lifecycle with no reachable terminal fails closed and reports the reachable set;
a terminal reachable only via a side branch is correctly accepted; the bundled spec lints
clean; and a custom sub-entity kind's completion status off its own vocabulary is caught the
same way.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import load_workflow_spec
from squads._workflow._loader import lint_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, StatusSpec, WorkflowSpec

_FLOOR_STATUSES: dict[str, StatusSpec] = {
    "Draft": StatusSpec(terminal=False),
    "Active": StatusSpec(terminal=False),
    "Archived": StatusSpec(terminal=True),
    "Todo": StatusSpec(terminal=False),
    "InProgress": StatusSpec(terminal=False),
    "Blocked": StatusSpec(terminal=False),
    "Done": StatusSpec(terminal=True),
    "Cancelled": StatusSpec(terminal=True),
    "Open": StatusSpec(terminal=False),
    "Fixed": StatusSpec(terminal=True),
    "Verified": StatusSpec(terminal=True),
    "WontFix": StatusSpec(terminal=True),
}
_AGENT_LIFECYCLE = Lifecycle(
    initial="Draft",
    transitions={"Draft": ["Active"], "Active": ["Archived"], "Archived": ["Active"]},
)


def _build_spec(
    *, extra_statuses: dict[str, StatusSpec], work_lifecycle: Lifecycle
) -> WorkflowSpec:
    """A minimal-but-complete spec (floor: the three meta-types + one work type) so only the
    behaviour under test (transition-target vocab / reachable-terminal) can fail."""
    statuses = {**_FLOOR_STATUSES, **extra_statuses}
    items_map = {
        "task": ItemSpec(prefix="TASK", folder="tasks", lifecycle="work", category="work"),
        "role": ItemSpec(
            prefix="ROLE", folder="agents/roles", lifecycle="agent", category="roster"
        ),
        "skill": ItemSpec(
            prefix="SKILL", folder="agents/skills", lifecycle="agent", category="roster"
        ),
        "operator": ItemSpec(prefix="OP", folder="operators", lifecycle="agent", category="roster"),
    }
    return WorkflowSpec.model_validate(
        {
            "items": items_map,
            "statuses": statuses,
            "lifecycles": {"work": work_lifecycle, "agent": _AGENT_LIFECYCLE},
            "prefix_to_type": {ts.prefix: name for name, ts in items_map.items()},
            "alias_to_type": {},
        }
    )


def test_a_transition_target_off_vocabulary_fails_closed_naming_lifecycle_and_status() -> None:
    bad = Lifecycle(initial="Draft", transitions={"Draft": ["Ghost"]})
    with pytest.raises(SquadsError, match=r"lifecycle 'work'") as exc_info:
        _build_spec(extra_statuses={}, work_lifecycle=bad)
    assert "'Ghost' not in status set" in str(exc_info.value)


def test_no_reachable_terminal_fails_closed_and_reports_the_reachable_set() -> None:
    stuck = Lifecycle(
        initial="Draft",
        transitions={
            "Draft": ["InProgress", "Blocked"],
            "InProgress": ["Draft"],
            "Blocked": ["InProgress"],
        },
    )
    with pytest.raises(SquadsError) as exc_info:
        _build_spec(extra_statuses={}, work_lifecycle=stuck)
    msg = str(exc_info.value)
    assert "no terminal status reachable from initial 'Draft'" in msg
    assert "reachable:" in msg
    assert "'Draft'" in msg and "'InProgress'" in msg and "'Blocked'" in msg


def test_a_terminal_reachable_only_via_a_side_branch_is_accepted_not_a_false_positive() -> None:
    """Draft <-> InProgress cycles forever on the naive first-edge walk, but InProgress also
    branches to the terminal Done — the machine CAN close via that side branch."""
    branching = Lifecycle(
        initial="Draft",
        transitions={
            "Draft": ["InProgress"],
            "InProgress": ["Draft", "Done"],
            "Done": ["InProgress"],
        },
    )
    spec = _build_spec(extra_statuses={}, work_lifecycle=branching)
    assert spec.statuses["Done"].terminal is True


def test_the_bundled_default_spec_lints_clean() -> None:
    spec = load_workflow_spec()
    for name, machine in spec.lifecycles.items():
        reachable = {machine.initial}
        queue = [machine.initial]
        while queue:
            cur = queue.pop()
            for nxt in machine.transitions.get(cur, []):
                if nxt not in reachable:
                    reachable.add(nxt)
                    queue.append(nxt)
        assert any(spec.statuses[s].terminal for s in reachable), (
            f"lifecycle {name!r} has no reachable terminal in the bundled spec"
        )


def _write_override(squad_dir, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def test_lint_reports_an_off_vocabulary_transition_target_with_location_and_fix_hint(
    tmp_path,
) -> None:
    _write_override(
        tmp_path,
        """
[statuses.Triage]
terminal = false

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["GhostStatus"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    findings = lint_workflow_spec(tmp_path)
    errors = [f for f in findings if f[0] == "error"]
    assert any("GhostStatus" in msg for _, _, msg, _ in errors)
    for level, location, message, fix_hint in findings:
        assert level == "error" and location and message and fix_hint


def test_lint_reports_a_lifecycle_with_no_reachable_terminal(tmp_path) -> None:
    _write_override(
        tmp_path,
        """
[statuses.Triage]
terminal = false
[statuses.Mitigating]
terminal = false

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Mitigating"]
Mitigating = ["Triage"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert any(
        "incident_lc" in msg and "no terminal status reachable" in msg for _, _, msg, _ in errors
    )


def test_lint_is_clean_for_a_valid_custom_lifecycle_and_for_no_override_at_all(tmp_path) -> None:
    _write_override(
        tmp_path,
        """
[statuses.Triage]
terminal = false
[statuses.Resolved]
terminal = true

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Resolved"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    assert [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"] == []
    assert lint_workflow_spec(tmp_path.parent / "no-such-override-dir") == []


_SUBENTITY_COMPLETION_OFF_VOCAB_OVERRIDE = """
[lifecycles.action]
initial = "Open"
[lifecycles.action.transitions]
Open = ["InProgress", "Done"]
InProgress = ["Done"]
Done = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "action"
subentity_kind = "action"

[subentity_kinds.action]
lifecycle = "action"
completion = "Verified"
plural = "actions"
local_prefix = "AC"
"""


def test_lint_reports_a_custom_subentity_kinds_completion_status_off_its_own_vocabulary(
    tmp_path,
) -> None:
    """ "Verified" is a real global status (finding's), just not reachable on the custom kind's
    own machine — the per-kind completion check catches this regardless."""
    _write_override(tmp_path, _SUBENTITY_COMPLETION_OFF_VOCAB_OVERRIDE)
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert any(
        "action" in msg and "Verified" in msg and "not a reachable" in msg
        for _, _, msg, _ in errors
    )
