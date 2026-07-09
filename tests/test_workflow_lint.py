"""TASK-000277 (FEAT-000211 AC#5): `sq workflow lint` hardening.

Covers the two spec defects an author can introduce in `.overrides/workflow.toml`:

1. A transition target status not in the declared status vocabulary.
   Already enforced by `_check_lifecycle_statuses` (`_workflow/_models.py`) — these
   tests CONFIRM it reports clearly and surfaces through `lint_workflow_spec`.
2. A lifecycle (machine) with no reachable terminal state — the NEW check added
   here (`_check_reachable_terminal`), a BFS from `initial` over the transition
   graph that fails closed if no reachable state is `terminal`.

Both checks live in `WorkflowSpec._validate` (fail-closed for `open_service` too),
so an invalid override surfaces as a `SquadsError` that `lint_workflow_spec`
captures as a single finding (phase 2) rather than raising.

Uses constructed/parametrized `WorkflowSpec` models (unit level) plus real
`.overrides/workflow.toml` files run through `lint_workflow_spec` and the
`sq workflow lint` CLI (integration level). The bundled default spec is never
weakened — only confirmed clean.
"""

import re
from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._paths import SquadPaths
from squads._workflow import load_workflow_spec
from squads._workflow._loader import lint_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, StatusSpec, WorkflowSpec

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Shared minimal-spec builder
# ---------------------------------------------------------------------------

# Floor statuses every WorkflowSpec must declare (ADR-000232 §5-6b) — see
# test_workflow_spec.py::test_non_reserved_status_omission_is_allowed for provenance.
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
_SUBENTITY_LIFECYCLE = Lifecycle(
    initial="Todo",
    transitions={
        "Todo": ["InProgress", "Blocked", "Cancelled"],
        "InProgress": ["Done", "Blocked", "Cancelled"],
        "Blocked": ["InProgress", "Cancelled"],
        "Done": ["InProgress"],
        "Cancelled": ["Todo"],
    },
)
_FINDING_LIFECYCLE = Lifecycle(
    initial="Open",
    transitions={
        "Open": ["Fixed", "WontFix"],
        "Fixed": ["Verified", "Open"],
        "Verified": [],
        "WontFix": ["Open"],
    },
)


def _build_spec(
    *,
    extra_statuses: dict[str, StatusSpec],
    work_lifecycle: Lifecycle,
) -> WorkflowSpec:
    """Construct a minimal-but-complete WorkflowSpec for lint-check unit tests.

    Declares the three meta-types (on the agent lifecycle — ADR-322 §2's floor) plus one
    work type ('task', on ``work_lifecycle``), satisfying the floor so only the behaviour
    under test (transition-target vocab / reachable-terminal) can fail.
    """
    statuses = {**_FLOOR_STATUSES, **extra_statuses}
    items_map = {
        "task": ItemSpec(prefix="TASK", folder="tasks", lifecycle="work", is_meta=False),
        "role": ItemSpec(prefix="ROLE", folder="agents/roles", lifecycle="agent", is_meta=True),
        "skill": ItemSpec(prefix="SKILL", folder="agents/skills", lifecycle="agent", is_meta=True),
        "operator": ItemSpec(prefix="OP", folder="operators", lifecycle="agent", is_meta=True),
    }
    return WorkflowSpec.model_validate(
        {
            "items": items_map,
            "statuses": statuses,
            "lifecycles": {
                "work": work_lifecycle,
                "agent": _AGENT_LIFECYCLE,
                "subtask": _SUBENTITY_LIFECYCLE,
                "story": _SUBENTITY_LIFECYCLE,
                "finding": _FINDING_LIFECYCLE,
            },
            "prefix_to_type": {ts.prefix: name for name, ts in items_map.items()},
            "alias_to_type": {},
        }
    )


# ---------------------------------------------------------------------------
# Unit level: WorkflowSpec._validate (_check_lifecycle_statuses / _check_reachable_terminal)
# ---------------------------------------------------------------------------


def test_transition_target_off_vocabulary_fails_closed() -> None:
    """A transition target not in the status vocabulary raises SquadsError.

    Confirms `_check_lifecycle_statuses` (pre-existing) names the lifecycle and the
    offending status so an author can locate the fix.
    """
    bad_lifecycle = Lifecycle(
        initial="Draft",
        transitions={"Draft": ["Nonexistent"]},
    )
    with pytest.raises(SquadsError, match=r"transition target 'Nonexistent' not in status set"):
        _build_spec(extra_statuses={}, work_lifecycle=bad_lifecycle)


def test_transition_target_off_vocabulary_names_lifecycle() -> None:
    """The off-vocab error names the specific lifecycle, not just the status."""
    bad_lifecycle = Lifecycle(
        initial="Draft",
        transitions={"Draft": ["Ghost"]},
    )
    with pytest.raises(SquadsError, match=r"lifecycle 'work'"):
        _build_spec(extra_statuses={}, work_lifecycle=bad_lifecycle)


def test_no_reachable_terminal_fails_closed() -> None:
    """A machine whose entire reachable graph is non-terminal raises SquadsError.

    Draft <-> InProgress cycle forever, with no transition ever reaching a
    terminal status: items on this lifecycle could never close.
    """
    stuck_lifecycle = Lifecycle(
        initial="Draft",
        transitions={
            "Draft": ["InProgress"],
            "InProgress": ["Draft"],
        },
    )
    with pytest.raises(
        SquadsError, match=r"lifecycle 'work': no terminal status reachable from initial 'Draft'"
    ):
        _build_spec(extra_statuses={}, work_lifecycle=stuck_lifecycle)


def test_no_reachable_terminal_reports_reachable_set() -> None:
    """The reachable-terminal error's message includes the reachable-state set (fix hint)."""
    stuck_lifecycle = Lifecycle(
        initial="Draft",
        transitions={
            "Draft": ["InProgress", "Blocked"],
            "InProgress": ["Draft"],
            "Blocked": ["InProgress"],
        },
    )
    with pytest.raises(SquadsError) as exc_info:
        _build_spec(extra_statuses={}, work_lifecycle=stuck_lifecycle)
    msg = str(exc_info.value)
    assert "reachable:" in msg
    assert "'Blocked'" in msg
    assert "'Draft'" in msg
    assert "'InProgress'" in msg


def test_terminal_reachable_only_via_side_branch_is_accepted() -> None:
    """A terminal reachable through a non-spine branch (not just the greedy path) passes.

    Draft -> InProgress -> Draft (cycle) but InProgress also branches to Done
    (terminal) — the machine CAN close even though the naive "first edge" walk
    would stay in the cycle forever.
    """
    branching_lifecycle = Lifecycle(
        initial="Draft",
        transitions={
            "Draft": ["InProgress"],
            "InProgress": ["Draft", "Done"],
            "Done": ["InProgress"],
        },
    )
    spec = _build_spec(extra_statuses={}, work_lifecycle=branching_lifecycle)
    assert spec.statuses["Done"].terminal is True


def test_green_case_reachable_terminal_and_valid_targets() -> None:
    """A well-formed custom lifecycle (valid targets + reachable terminal) lints clean."""
    good_lifecycle = Lifecycle(
        initial="Draft",
        transitions={
            "Draft": ["InProgress", "Cancelled"],
            "InProgress": ["Done", "Cancelled"],
            "Done": [],
            "Cancelled": [],
        },
    )
    spec = _build_spec(extra_statuses={}, work_lifecycle=good_lifecycle)
    assert spec.machine_for("task").initial == "Draft"


def test_bundled_default_spec_lints_clean() -> None:
    """The bundled default spec (no override) passes both new/confirmed checks.

    Regression guard: hardening the lint must never touch `default_workflow.toml`
    semantics (byte-identical invariant, EPIC-000206).
    """
    spec = load_workflow_spec()
    assert isinstance(spec, WorkflowSpec)
    # Every lifecycle in the bundled spec must have at least one reachable terminal.
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
            f"lifecycle {name!r} has no reachable terminal in the bundled spec — regression"
        )


# ---------------------------------------------------------------------------
# Integration level: lint_workflow_spec over a real .overrides/workflow.toml
# ---------------------------------------------------------------------------


def _write_override(squad_dir: Path, content: str) -> Path:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    path = override_dir / "workflow.toml"
    path.write_text(content, encoding="utf-8")
    return path


_BOX_DRAWING_RE = re.compile(r"[─-╿]")


def _flatten(output: str) -> str:
    """Collapse a Rich table's hard word-wrapping back into single-spaced text.

    ``sq workflow lint`` renders findings in a fixed-width Rich ``Table``, which
    hard-wraps long messages across multiple lines/cells AND interleaves box-drawing
    border characters (``│``, ``┃``, …) between the wrapped fragments of a single
    cell. A naive whitespace collapse still leaves those border glyphs sitting
    between words, breaking a multi-word substring check at terminal-width-dependent
    points. Strip box-drawing characters first, then collapse all whitespace.
    """
    return re.sub(r"\s+", " ", _BOX_DRAWING_RE.sub(" ", output))


def test_lint_reports_off_vocab_transition_target(tmp_path: Path) -> None:
    """sq workflow lint (via lint_workflow_spec) reports an off-vocab transition target."""
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
Triage = ["GhostStatus"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    findings = lint_workflow_spec(tmp_path)
    errors = [f for f in findings if f[0] == "error"]
    assert errors, "Expected at least one error finding for an off-vocab transition target"
    assert any("GhostStatus" in msg for _, _, msg, _ in errors), (
        f"Expected 'GhostStatus' named in an error message: {errors}"
    )
    # Location + fix hint present (lint UX contract).
    for level, location, message, fix_hint in findings:
        assert level == "error"
        assert location
        assert message
        assert fix_hint


def test_lint_reports_terminal_unreachable_lifecycle(tmp_path: Path) -> None:
    """sq workflow lint reports a custom lifecycle with no reachable terminal state."""
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
    findings = lint_workflow_spec(tmp_path)
    errors = [f for f in findings if f[0] == "error"]
    assert errors, "Expected at least one error finding for a terminal-unreachable lifecycle"
    assert any(
        "incident_lc" in msg and "no terminal status reachable" in msg for _, _, msg, _ in errors
    ), f"Expected 'incident_lc' + 'no terminal status reachable' in an error message: {errors}"
    for level, location, message, fix_hint in findings:
        assert level == "error"
        assert location
        assert message
        assert fix_hint


def test_lint_green_case_valid_custom_lifecycle(tmp_path: Path) -> None:
    """sq workflow lint reports no errors: valid targets, terminal reachable."""
    _write_override(
        tmp_path,
        """
[statuses.Triage]
terminal = false

[statuses.Mitigating]
terminal = false

[statuses.Resolved]
terminal = true

[lifecycles.incident_lc]
initial = "Triage"

[lifecycles.incident_lc.transitions]
Triage = ["Mitigating"]
Mitigating = ["Resolved", "Triage"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    findings = lint_workflow_spec(tmp_path)
    errors = [f for f in findings if f[0] == "error"]
    assert errors == [], f"Expected no errors for a valid custom override, got: {errors}"


def test_lint_no_override_bundled_spec_stays_clean(tmp_path: Path) -> None:
    """No override present -> lint reports nothing (bundled spec always lints clean)."""
    findings = lint_workflow_spec(tmp_path)
    assert findings == []


# ---------------------------------------------------------------------------
# CLI level: sq workflow lint exit codes (AC#5 acceptance #1/#2/#3)
# ---------------------------------------------------------------------------


async def test_cli_workflow_lint_exits_1_on_off_vocab_target(project: SquadPaths, invoke) -> None:
    """sq workflow lint exits 1 when a transition targets an undeclared status."""
    _write_override(
        project.squad_dir,
        """
[statuses.Triage]
terminal = false

[lifecycles.incident_lc]
initial = "Triage"

[lifecycles.incident_lc.transitions]
Triage = ["Nowhere"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 1, f"Expected exit 1, got {result.exit_code}\n{result.output}"
    assert "Nowhere" in _flatten(result.output)


async def test_cli_workflow_lint_exits_1_on_terminal_unreachable(
    project: SquadPaths, invoke
) -> None:
    """sq workflow lint exits 1 when a custom lifecycle can never reach a terminal state."""
    _write_override(
        project.squad_dir,
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
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 1, f"Expected exit 1, got {result.exit_code}\n{result.output}"
    flat = _flatten(result.output)
    assert "incident_lc" in flat
    assert "1 error" in flat


async def test_cli_workflow_lint_exits_0_on_valid_custom_override(
    project: SquadPaths, invoke
) -> None:
    """sq workflow lint exits 0 on a valid custom override (targets ok, terminal reachable)."""
    _write_override(
        project.squad_dir,
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
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}\n{result.output}"


async def test_cli_workflow_lint_exits_0_on_bundled_spec(project: SquadPaths, invoke) -> None:
    """sq workflow lint exits 0 when no override is present (bundled spec is always clean)."""
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}\n{result.output}"
