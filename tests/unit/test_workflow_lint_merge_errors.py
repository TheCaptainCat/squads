"""``lint_workflow_spec`` collects EVERY merge/structural error in one pass instead of raising
on the first (the "sq workflow lint" verbose surface). Distinct from the transition-graph
*reachability* lint (tests/unit/test_workflow_lifecycle_reachability.py) — this is the
merge-time vocabulary-conflict family.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._workflow._loader import lint_workflow_spec


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def _stamped(content: str) -> str:
    """Prefix *content* with a current-version stamp — used only by the "is clean" roster-
    floor tests below, so the unrelated unstamped-and-shadowing finding (a shadowing override
    with no ``# squads:override-base`` stamp is its own error-level finding) never masks
    whether the floor itself is satisfied."""
    return f"# squads:override-base:{__version__}\n{content}"


def test_lint_with_no_override_reports_nothing(tmp_path: Path) -> None:
    assert lint_workflow_spec(tmp_path) == []


def test_lint_with_a_valid_override_reports_no_errors(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[statuses.Triage]
[statuses.Resolved]
role = "done"

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
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert errors == []


# --------------------------------------------------------------------------- the stamp
# obligation's lint-side half — shared with `sq check` via `workflow_stamp_finding` so the two
# surfaces can never disagree about the same file; each of the three levels driven directly
# through `lint_workflow_spec` (the surface `sq workflow lint` itself calls), never assumed
# from the shared helper's own unit coverage.


def test_lint_reports_an_error_for_a_shadowing_override_with_no_stamp(tmp_path: Path) -> None:
    _write_override(tmp_path, '[items.guide]\nfolder = "handbooks"\n')  # shadows a bundled key
    findings = lint_workflow_spec(tmp_path)
    errors = [f for f in findings if f[0] == "error"]
    assert len(errors) == 1
    assert "override-base" in errors[0][2]


def test_lint_reports_a_warning_for_a_shadowing_override_with_a_stamp_the_bundle_changed_since(
    tmp_path: Path,
) -> None:
    """Content-gated: the warning fires only when the bundled workflow.toml actually changed
    since the stamped version (v0.13.1 -> running is real recorded history with a change)."""
    _write_override(
        tmp_path, '# squads:override-base:0.13.1\n[items.guide]\nfolder = "handbooks"\n'
    )
    findings = lint_workflow_spec(tmp_path)
    warnings = [f for f in findings if f[0] == "warn"]
    assert len(warnings) == 1
    assert "stale" in warnings[0][2]
    assert not [f for f in findings if f[0] == "error"]


def test_lint_reports_nothing_for_a_shadowing_override_with_a_stamp_squads_carries_no_history_for(
    tmp_path: Path,
) -> None:
    """Unknown history is treated as unchanged, never a warning: v0.0.1 predates workflow.toml's
    own coverage floor, so a stale-looking stamp reports clean rather than "may be stale"."""
    _write_override(tmp_path, '# squads:override-base:0.0.1\n[items.guide]\nfolder = "handbooks"\n')
    findings = lint_workflow_spec(tmp_path)
    assert not [f for f in findings if f[0] in ("warn", "error")]


def test_lint_reports_nothing_for_an_add_only_override_with_no_stamp(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "work"\n',
    )
    assert lint_workflow_spec(tmp_path) == []


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(
            '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "work"\n',
            id="add-only-unstamped",
        ),
        pytest.param('[items.guide]\nfolder = "handbooks"\n', id="shadowing-unstamped"),
        pytest.param(
            '# squads:override-base:0.13.1\n[items.guide]\nfolder = "handbooks"\n',
            id="stamped-with-a-bundled-change",
        ),
        pytest.param(
            f'# squads:override-base:{__version__}\n[items.guide]\nfolder = "handbooks"\n',
            id="stamped-without-a-bundled-change",
        ),
        pytest.param(
            '# squads:override-base:0.0.1\n[items.guide]\nfolder = "handbooks"\n',
            id="unrecorded-base-version",
        ),
    ],
)
def test_lint_and_check_agree_on_the_workflow_stamp_finding(tmp_path: Path, content: str) -> None:
    """`sq workflow lint` (`lint_workflow_spec`) and `sq check` (`check_override_issues`) both
    read `workflow_stamp_finding` — one function, so they must report the exact same
    (level, message) for the exact same file across every case that distinguishes the three
    outcomes. A future fork of this obligation fails this test, not a docstring comparison."""
    from squads._overrides._service import check_override_issues

    _write_override(tmp_path, content)

    lint_findings = {(level, msg) for level, _loc, msg, _hint in lint_workflow_spec(tmp_path)}
    check_findings = {(level, msg) for level, _loc, msg in check_override_issues(tmp_path)}
    assert lint_findings == check_findings


def test_lint_reports_a_finding_shaped_tuple_for_a_structural_error(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        '[items.broken_type]\nprefix = "BRK"\nfolder = "brokens"\n'
        'lifecycle = "nonexistent_lifecycle"\n',
    )
    findings = lint_workflow_spec(tmp_path)
    errors = [f for f in findings if f[0] == "error"]
    assert len(errors) >= 1
    for level, location, message, fix_hint in findings:
        assert isinstance(level, str)
        assert isinstance(location, str)
        assert isinstance(message, str)
        assert isinstance(fix_hint, str)


def test_lint_collects_every_conflict_in_one_pass_not_just_the_first(tmp_path: Path) -> None:
    """Two independent structural violations in one override — two new types each naming an
    undeclared lifecycle — must surface as two separate findings, not just the first
    (``WorkflowSpec._validate``'s combined error message splits into one bullet per finding)."""
    _write_override(
        tmp_path,
        """
[items.widget]
prefix = "WDGT"
folder = "widgets"
lifecycle = "nonexistent_lifecycle_1"

[items.gizmo]
prefix = "GIZ"
folder = "gizmos"
lifecycle = "nonexistent_lifecycle_2"
""",
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert len(errors) >= 2
    messages = " ".join(f[2] for f in errors)
    assert "widget" in messages
    assert "gizmo" in messages


def test_lint_surfaces_a_prefix_shadowing_a_builtin_as_an_error(tmp_path: Path) -> None:
    """A custom type re-using a reserved prefix is exactly the reserved-vocab violation lint
    must catch — the direct-construction instance of this rule lives in
    test_workflow_reserved_vocab.py; this is lint's own surfacing of it."""
    _write_override(
        tmp_path,
        '[items.shadow-task]\nprefix = "TASK"\nfolder = "shadow-tasks"\nlifecycle = "work"\n',
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert errors


def test_lint_is_clean_for_a_valid_custom_type_that_adds_a_new_lifecycle(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
""",
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert not errors


# --------------------------------------------------------------------------- roster lifecycle floor
# The roster type-key lock refuses ANY type outside role/skill/operator from declaring
# category="roster" (that lock is covered separately below), so the only way to drive a
# roster-category lifecycle through the merge is to shadow ONE of those three built-ins'
# `lifecycle` field — an ordinary field-merge — pointing it at a brand-new custom lifecycle
# declared in the same override. `role`/`skill` are used here as the two available roster
# hosts; the type itself is untouched (still category="roster", still named `role`/`skill`).
#
# Every custom status here that names `role = "active"` resolves to the bundled `[roles.active]`
# role, which is `live = true` — the merge is additive over the bundled role catalog, so a
# shadowed roster lifecycle reusing the bundled role name gets the bundled live flag for free.


def test_lint_reports_a_roster_type_with_zero_live_statuses(tmp_path: Path) -> None:
    """R1: a category='roster' type's lifecycle must have at least one live status. Neither
    Spinning (role-less, falls back to 'pending', not live) nor Retired ('done', not
    live) carries it, so shadowing `role`'s lifecycle with this one has zero — refused,
    naming the type."""
    _write_override(
        tmp_path,
        """
[statuses.Spinning]
[statuses.Retired]
role = "done"

[lifecycles.gadget_lc]
initial = "Spinning"
[lifecycles.gadget_lc.transitions]
Spinning = ["Retired"]
Retired = []

[items.role]
lifecycle = "gadget_lc"
""",
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert any("role" in msg and "no live status" in msg and "R1" in msg for _, _, msg, _ in errors)


def test_lint_is_clean_for_a_roster_type_with_two_live_statuses_when_the_initial_is_live(
    tmp_path: Path,
) -> None:
    """R1 only requires AT LEAST ONE live status, and R1' only bites when the lifecycle's
    initial is itself non-live. Here Spinning (the initial) and AlsoSpinning both carry the
    live 'active' role — two live statuses, but since the initial is one of them there is
    no ambiguity for the create path to resolve, so this is legal (it was a violation under the
    old 'exactly one' rule)."""
    _write_override(
        tmp_path,
        _stamped(
            """
[statuses.Spinning]
role = "active"
[statuses.AlsoSpinning]
role = "active"
[statuses.Retired]
role = "done"

[lifecycles.gadget_lc]
initial = "Spinning"
[lifecycles.gadget_lc.transitions]
Spinning = ["AlsoSpinning", "Retired"]
AlsoSpinning = ["Retired"]
Retired = []

[items.role]
lifecycle = "gadget_lc"
"""
        ),
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert not errors


def test_lint_reports_a_roster_type_with_two_live_statuses_when_the_initial_is_nonlive(
    tmp_path: Path,
) -> None:
    """R1': when the lifecycle's initial is NOT live, exactly one status must be live —
    Booting (role-less, not live) is the initial here, and BOTH Spinning and AlsoSpinning
    are live, leaving the create path with no unambiguous target."""
    _write_override(
        tmp_path,
        """
[statuses.Booting]
[statuses.Spinning]
role = "active"
[statuses.AlsoSpinning]
role = "active"
[statuses.Retired]
role = "done"

[lifecycles.gadget_lc]
initial = "Booting"
[lifecycles.gadget_lc.transitions]
Booting = ["Spinning", "AlsoSpinning"]
Spinning = ["Retired"]
AlsoSpinning = ["Retired"]
Retired = []

[items.role]
lifecycle = "gadget_lc"
""",
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert any("role" in msg and "R1'" in msg and "found 2 live" in msg for _, _, msg, _ in errors)


def test_lint_reports_a_roster_type_whose_live_status_can_never_retire(tmp_path: Path) -> None:
    """R2: a settled, non-live status must be reachable from a live one — Shutdown IS
    reachable from initial (so the universal reachable-settled floor is satisfied) but NOT
    from the live Spinning status, which has no outgoing transition at all."""
    _write_override(
        tmp_path,
        """
[statuses.Bootstrapping]
[statuses.Spinning]
role = "active"
[statuses.Shutdown]
role = "done"

[lifecycles.gadget_lc]
initial = "Bootstrapping"
[lifecycles.gadget_lc.transitions]
Bootstrapping = ["Spinning", "Shutdown"]
Spinning = []
Shutdown = []

[items.role]
lifecycle = "gadget_lc"
""",
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert any(
        "role" in msg
        and "no settled, non-live status reachable from a live status" in msg
        and "R2" in msg
        for _, _, msg, _ in errors
    )


def test_lint_collects_both_roster_floor_violations_across_two_types_in_one_pass(
    tmp_path: Path,
) -> None:
    """Two independent roster-category types (`role` and `skill`, each shadowed onto its own
    custom lifecycle) each violating a different floor clause are both reported in one lint
    run — collected, not fail-fast-on-first."""
    _write_override(
        tmp_path,
        """
[statuses.Spinning]
[statuses.Retired]
role = "done"

[lifecycles.gadget_lc]
initial = "Spinning"
[lifecycles.gadget_lc.transitions]
Spinning = ["Retired"]
Retired = []

[items.role]
lifecycle = "gadget_lc"

[statuses.Booting]
[statuses.Widgeting]
role = "active"
[statuses.Retired2]
role = "done"

[lifecycles.widget_lc]
initial = "Booting"
[lifecycles.widget_lc.transitions]
Booting = ["Widgeting", "Retired2"]
Widgeting = []
Retired2 = []

[items.skill]
lifecycle = "widget_lc"
""",
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    messages = " ".join(f[2] for f in errors)
    assert "role" in messages and "no live status" in messages
    assert "skill" in messages and "no settled, non-live status reachable" in messages


def test_lint_is_clean_for_a_custom_roster_type_that_satisfies_the_floor(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        _stamped(
            """
[statuses.Spinning]
role = "active"
[statuses.Retired]
role = "done"

[lifecycles.gadget_lc]
initial = "Spinning"
[lifecycles.gadget_lc.transitions]
Spinning = ["Retired"]
Retired = ["Spinning"]

[items.role]
lifecycle = "gadget_lc"
"""
        ),
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert not errors
