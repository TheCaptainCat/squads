"""``lint_workflow_spec`` collects EVERY additive-merge/structural error in one pass instead of
raising on the first (the "sq workflow lint" verbose surface). Distinct from the transition-
graph *reachability* lint (tests/unit/test_workflow_lifecycle_reachability.py, out of this
chunk's range) — this is the merge-time vocabulary-conflict family.
"""

from pathlib import Path

from squads._workflow._loader import lint_workflow_spec


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def test_lint_with_no_override_reports_nothing(tmp_path: Path) -> None:
    assert lint_workflow_spec(tmp_path) == []


def test_lint_with_a_valid_override_reports_no_errors(tmp_path: Path) -> None:
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
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert errors == []


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
    """Redefining TWO built-in types in one override must surface two separate findings."""
    _write_override(
        tmp_path,
        """
[items.task]
prefix = "TSK2"
folder = "tasks2"
lifecycle = "work"

[items.bug]
prefix = "BUG2"
folder = "bugs2"
lifecycle = "work"
""",
    )
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert len(errors) >= 2
    messages = " ".join(f[2] for f in errors)
    assert "task" in messages
    assert "bug" in messages


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
