"""Golden-file tests: freeze every --json shape so a shape drift fails the build (TASK-000084).

Every command that emits ``--json`` output has a companion golden file under
``tests/goldens/<name>.json``.  The test runs the command against a deterministic seeded
squad (frozen time + fixed item sequence) and compares the parsed JSON to the stored golden.

Regenerating goldens
--------------------
Set ``UPDATE_GOLDENS=1`` in the environment and run the suite normally::

    UPDATE_GOLDENS=1 uv run pytest tests/test_golden_json.py -v

The suite will *write* (not read) the golden files, updating them to match the current output.
Commit the diff — any shape change then appears in the PR as a deliberate golden update.

Coverage
--------
This module pins the following ``--json`` commands (read surface):

  - ``list --json`` (all items)
  - ``list --type feature --json`` (filtered list)
  - ``tree --json`` (full tree)
  - ``tree FEAT-000002 --json`` (rooted subtree)
  - ``inbox manager --json``
  - ``search login --json``
  - ``blocked --json``
  - ``workload --json``
  - ``mine manager --json``
  - ``show FEAT-000002 --json`` (root show)
  - ``show TASK-000003 --json`` (root show)
  - ``check --json`` (seeded squad; exit 0, no error-level issues)
  - ``feature 2 show --json`` (typed show)
  - ``task 3 show --json`` (typed show)
  - ``task 3 refs --json`` (forward refs only)
  - ``task 3 refs --all --json`` (both directions)
  - ``feature 2 stories --json`` (sub-entity list)
  - ``task 3 subtasks --json`` (sub-entity list)
  - ``review 6 findings --json`` (sub-entity list)
  - ``role catalog --json``
  - ``role manager show --json`` (activated role)
  - ``role qa show --json`` (bundled-only role)
  - ``skill 8 show --json`` (SKIL-000008, added via ``skill add``)
  - ``operator op-alice show --json``
  - ``override list --json`` (one scaffolded template override; state=current)
  - ``override diff items/task.md.j2 --json`` (Δ-mine shows stamp prepended; Δ-upgrade empty)

Notes
-----
- ``role catalog`` is purely static (bundled catalog, no project state) — its golden pins
  the full catalog shape and is safe across re-runs.
- ``skill <addr> show --json`` requires an activated skill item; the seeded squad creates one
  via ``skill add``.
- Write-side commands (``create --json``, ``add-story --json``, etc.) are mutation commands,
  not read commands.  They are tested for shape in ``test_cli.py``; goldens here focus on
  the read surface.
- The ``print_block`` output (``add-story/add-subtask/add-finding --json``) emits ``file``
  (not ``path``) by design: it points to the *write target* for the agent, while the read-side
  ``skill/operator show --json`` emits ``path`` for the *item location*.  This asymmetry is
  intentional and documented here so it is not inadvertently "fixed".
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from squads._cli import app

# Golden files live here.  The directory is created automatically when UPDATE_GOLDENS is set.
GOLDENS_DIR = Path(__file__).parent / "goldens"

# Set UPDATE_GOLDENS=1 to write/update golden files instead of comparing.
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"


# ---------------------------------------------------------------------------
# Deterministic squad fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def golden_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any) -> CliRunner:
    """A deterministic, seeded squad in a temp dir; returns a configured CliRunner.

    Squad contents (stable IDs — global counter starts at 1 after init):
      ROLE-000001  manager          (from ``init --roles minimal``)
      FEAT-000002  User authentication
      TASK-000003  Implement login        parent=FEAT-000002
      BUG-000004   Login crashes on empty password
      ADR-000005   Use JWT for session tokens
      REV-000006   Code review for login
      GUIDE-000007 Python coding guide
      SKIL-000008  golden-skill           (for ``skill show --json``)
      OP-000009    Alice Tester
      FEAT-000002 / US1  As a user I can log in
      TASK-000003 / ST1  Write login handler  (story=US1)
      REV-000006  / F1   Missing input validation  (severity=high)
      TASK-000003 refs: BUG-000004 (depends-on)
      TASK-000003 comment: ``@manager please review the login handler``
      TASK-000003 status → InProgress
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup step {args!r} failed (exit {r.exit_code}):\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])  # ROLE-000001
    inv(
        [
            "create",
            "feature",
            "User authentication",
            "--author",
            "manager",
            "--desc",
            "Login and logout flows",
        ]
    )  # FEAT-000002
    inv(
        ["create", "task", "Implement login", "--author", "manager", "--parent", "FEAT-000002"]
    )  # TASK-000003
    inv(["create", "bug", "Login crashes on empty password", "--author", "manager"])  # BUG-000004
    inv(["create", "decision", "Use JWT for session tokens", "--author", "manager"])  # ADR-000005
    inv(["create", "review", "Code review for login", "--author", "manager"])  # REV-000006
    inv(["create", "guide", "Python coding guide", "--author", "manager"])  # GUIDE-000007
    inv(
        ["skill", "add", "golden-skill", "--desc", "Test skill for golden snapshots"]
    )  # SKIL-000008
    inv(["operator", "add", "Alice Tester"])  # OP-000009
    inv(["feature", "2", "add-story", "As a user I can log in"])  # US1
    inv(["task", "3", "add-subtask", "Write login handler", "--story", "US1"])  # ST1
    inv(["review", "6", "add-finding", "Missing input validation", "--severity", "high"])  # F1
    inv(["task", "3", "ref", "add", "BUG-000004", "--kind", "depends-on"])
    inv(
        [
            "task",
            "3",
            "comment",
            "--as",
            "manager",
            "-m",
            "@manager please review the login handler",
        ]
    )
    inv(["task", "3", "status", "InProgress"])
    inv(["override", "scaffold", "items/task.md.j2"])  # scaffolded override for override goldens

    return runner


# ---------------------------------------------------------------------------
# Golden-comparison helper
# ---------------------------------------------------------------------------


def _check_golden(name: str, actual_data: Any) -> None:
    """Compare ``actual_data`` (already parsed JSON) to the stored golden, or write it."""
    path = GOLDENS_DIR / f"{name}.json"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual_data, indent=2) + "\n", encoding="utf-8")
        return
    assert path.exists(), (
        f"Golden file missing: {path}\n"
        f"Run UPDATE_GOLDENS=1 uv run pytest tests/test_golden_json.py to generate it."
    )
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual_data == expected, (
        f"Golden mismatch for {name!r}.\n"
        f"If this change is intentional, regenerate with:\n"
        f"  UPDATE_GOLDENS=1 uv run pytest tests/test_golden_json.py -v\n"
        f"and commit the updated golden file in the same PR."
    )


def _run_json(runner: CliRunner, args: list[str], expected_exit: int = 0) -> Any:
    """Run a CLI command, assert the exit code, parse and return the JSON output."""
    r = runner.invoke(app, args)
    assert r.exit_code == expected_exit, (
        f"Command {args!r} exited {r.exit_code}, expected {expected_exit}.\nOutput:\n{r.output}"
    )
    return json.loads(r.output)


# ---------------------------------------------------------------------------
# Golden tests — one test function per command
# ---------------------------------------------------------------------------


def test_golden_list(golden_squad: CliRunner) -> None:
    """sq list --json: full item list (all open items)."""
    data = _run_json(golden_squad, ["list", "--json"])
    _check_golden("list", data)


def test_golden_list_type_feature(golden_squad: CliRunner) -> None:
    """sq list --type feature --json: filtered to features only."""
    data = _run_json(golden_squad, ["list", "--type", "feature", "--json"])
    _check_golden("list_feature", data)


def test_golden_tree(golden_squad: CliRunner) -> None:
    """sq tree --json: full tree of all open items."""
    data = _run_json(golden_squad, ["tree", "--json"])
    _check_golden("tree", data)


def test_golden_tree_rooted(golden_squad: CliRunner) -> None:
    """sq tree FEAT-000002 --json: subtree rooted at a feature."""
    data = _run_json(golden_squad, ["tree", "FEAT-000002", "--json"])
    _check_golden("tree_feat", data)


def test_golden_inbox(golden_squad: CliRunner) -> None:
    """sq inbox manager --json: items mentioning @manager."""
    data = _run_json(golden_squad, ["inbox", "manager", "--json"])
    _check_golden("inbox_manager", data)


def test_golden_search(golden_squad: CliRunner) -> None:
    """sq search login --json: items matching 'login'."""
    data = _run_json(golden_squad, ["search", "login", "--json"])
    _check_golden("search_login", data)


def test_golden_blocked(golden_squad: CliRunner) -> None:
    """sq blocked --json: items blocked by an open blocker."""
    data = _run_json(golden_squad, ["blocked", "--json"])
    _check_golden("blocked", data)


def test_golden_workload(golden_squad: CliRunner) -> None:
    """sq workload --json: per-assignee open/closed/total counts."""
    data = _run_json(golden_squad, ["workload", "--json"])
    _check_golden("workload", data)


def test_golden_mine(golden_squad: CliRunner) -> None:
    """sq mine manager --json: items assigned to manager (empty in seeded squad)."""
    data = _run_json(golden_squad, ["mine", "manager", "--json"])
    _check_golden("mine_manager", data)


def test_golden_show_any_feature(golden_squad: CliRunner) -> None:
    """sq show FEAT-000002 --json: root show command on a feature."""
    data = _run_json(golden_squad, ["show", "FEAT-000002", "--json"])
    _check_golden("show_feat", data)


def test_golden_show_any_task(golden_squad: CliRunner) -> None:
    """sq show TASK-000003 --json: root show command on a task."""
    data = _run_json(golden_squad, ["show", "TASK-000003", "--json"])
    _check_golden("show_task", data)


def test_golden_check(golden_squad: CliRunner) -> None:
    """sq check --json: seeded squad (may have warnings; exit 0 when no errors).

    The golden pins the shape ``[{level, item, message}, ...]``; the seeded squad may emit
    warnings (e.g. the ``golden-skill`` item self-authors, which ``sq check`` flags).
    Errors are absent (exit 0).
    """
    data = _run_json(golden_squad, ["check", "--json"], expected_exit=0)
    _check_golden("check_squad", data)


def test_golden_feature_show(golden_squad: CliRunner) -> None:
    """sq feature 2 show --json: typed show on the feature item."""
    data = _run_json(golden_squad, ["feature", "2", "show", "--json"])
    _check_golden("feature_show", data)


def test_golden_task_show(golden_squad: CliRunner) -> None:
    """sq task 3 show --json: typed show on the task item."""
    data = _run_json(golden_squad, ["task", "3", "show", "--json"])
    _check_golden("task_show", data)


def test_golden_refs_out(golden_squad: CliRunner) -> None:
    """sq task 3 refs --json: forward refs only (default)."""
    data = _run_json(golden_squad, ["task", "3", "refs", "--json"])
    _check_golden("task_refs_out", data)


def test_golden_refs_all(golden_squad: CliRunner) -> None:
    """sq task 3 refs --all --json: both forward and back refs."""
    data = _run_json(golden_squad, ["task", "3", "refs", "--all", "--json"])
    _check_golden("task_refs_all", data)


def test_golden_stories(golden_squad: CliRunner) -> None:
    """sq feature 2 stories --json: sub-entity list for stories."""
    data = _run_json(golden_squad, ["feature", "2", "stories", "--json"])
    _check_golden("feature_stories", data)


def test_golden_subtasks(golden_squad: CliRunner) -> None:
    """sq task 3 subtasks --json: sub-entity list for subtasks."""
    data = _run_json(golden_squad, ["task", "3", "subtasks", "--json"])
    _check_golden("task_subtasks", data)


def test_golden_findings(golden_squad: CliRunner) -> None:
    """sq review 6 findings --json: sub-entity list for findings."""
    data = _run_json(golden_squad, ["review", "6", "findings", "--json"])
    _check_golden("review_findings", data)


def test_golden_role_catalog(golden_squad: CliRunner) -> None:
    """sq role catalog --json: bundled role catalog (static, no project state)."""
    data = _run_json(golden_squad, ["role", "catalog", "--json"])
    _check_golden("role_catalog", data)


def test_golden_role_show_activated(golden_squad: CliRunner) -> None:
    """sq role manager show --json: activated role metadata."""
    data = _run_json(golden_squad, ["role", "manager", "show", "--json"])
    _check_golden("role_manager_show", data)


def test_golden_role_show_bundled(golden_squad: CliRunner) -> None:
    """sq role qa show --json: bundled-only (not activated) role metadata."""
    data = _run_json(golden_squad, ["role", "qa", "show", "--json"])
    _check_golden("role_qa_show", data)


def test_golden_skill_show(golden_squad: CliRunner) -> None:
    """sq skill 8 show --json: skill item metadata (SKIL-000008, seeded via skill add)."""
    data = _run_json(golden_squad, ["skill", "8", "show", "--json"])
    _check_golden("skill_show", data)


def test_golden_operator_show(golden_squad: CliRunner) -> None:
    """sq operator op-alice show --json: operator metadata."""
    data = _run_json(golden_squad, ["operator", "op-alice", "show", "--json"])
    _check_golden("operator_show", data)


def test_golden_override_list(golden_squad: CliRunner) -> None:
    """sq override list --json: one scaffolded template override (state=current)."""
    data = _run_json(golden_squad, ["override", "list", "--json"])
    _check_golden("override_list", data)


def test_golden_override_diff(golden_squad: CliRunner) -> None:
    """sq override diff items/task.md.j2 --json: two-delta view for a freshly-scaffolded override.

    Δ-mine shows the stamp line prepended; Δ-upgrade is empty (base == current version).
    """
    data = _run_json(golden_squad, ["override", "diff", "items/task.md.j2", "--json"])
    _check_golden("override_diff", data)


# ---------------------------------------------------------------------------
# Smoke: UPDATE_GOLDENS path is wired
# ---------------------------------------------------------------------------


def test_update_goldens_flag_is_documented() -> None:
    """Confirm the UPDATE_GOLDENS mechanism is in place (non-functional smoke)."""
    # This test always passes — it just ensures the constant is defined so
    # developers can discover the update path via `pytest --collect-only`.
    assert isinstance(_UPDATE, bool)
