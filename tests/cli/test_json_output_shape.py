"""Every ``--json`` read command has a pinned golden shape under tests/goldens/ — a shape
drift fails the build. Reuses the existing golden files read-only (the same reviewed
reference renders the old flat suite pins) rather than duplicating them, per the "one golden
per distinct rendering path" protocol.

Regenerating goldens: set ``UPDATE_GOLDENS=1`` and run this module with -v; commit the diff.
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from squads._cli import app

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"


@pytest.fixture
def golden_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any) -> CliRunner:
    """A deterministic, seeded squad (stable IDs — the global counter starts at 1 after init).

    ROLE-2  manager, FEAT-2  User authentication, TASK-3  Implement login (parent=FEAT-2),
    BUG-4, ADR-5, REV-6, GUIDE-7, SKIL-8, OP-9, plus a story/subtask/finding/ref/comment/
    status-change/override-scaffold — see the invocation list below for the exact sequence.
    The subtask (ST1) is assigned to `manager` and carries its own discussion comment (so is
    the story, US1), exercising the sub-entity-aware `mine`/`workload`/`inbox`/`show --json`
    surfaces from one fixture.
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup step {args!r} failed:\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
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
    )
    inv(["create", "task", "Implement login", "--author", "manager", "--parent", "FEAT-000002"])
    inv(["create", "bug", "Login crashes on empty password", "--author", "manager"])
    inv(["create", "decision", "Use JWT for session tokens", "--author", "manager"])
    inv(["create", "review", "Code review for login", "--author", "manager"])
    inv(["create", "guide", "Python coding guide", "--author", "manager"])
    inv(["skill", "add", "golden-skill", "--desc", "Test skill for golden snapshots"])
    inv(["operator", "add", "Alice Tester"])
    inv(["feature", "2", "add-story", "As a user I can log in"])
    inv(["task", "3", "add-subtask", "Write login handler", "--story", "US1"])
    inv(["review", "6", "add-finding", "Missing input validation", "--severity", "high"])
    inv(["task", "3", "ref", "add", "BUG-000004", "--kind", "depends-on"])
    # A sub-entity assignment + its own discussion — exercises the sub-entity-aware `mine`/
    # `workload`/`inbox` surfaces and the per-subentity `discussion` JSON key.
    inv(["task", "3", "subtask", "ST1", "update", "--assignee", "manager"])
    inv(
        [
            "task",
            "3",
            "subtask",
            "ST1",
            "comment",
            "--as",
            "manager",
            "-m",
            "@manager please double check this subtask",
        ]
    )
    inv(
        [
            "feature",
            "2",
            "story",
            "US1",
            "comment",
            "--as",
            "manager",
            "-m",
            "Scoped to password auth only for this release.",
        ]
    )
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
    # An item whose ONLY mention lives in its own frontmatter (`--desc`), added last so no
    # existing id shifts. Without it the alignment guard below never sees the one shape that can
    # produce a zero-line hit, and passed while `sq inbox` was emitting exactly that.
    inv(
        [
            "create",
            "task",
            "Rotate the signing keys",
            "--author",
            "manager",
            "--desc",
            "@manager owns the rotation window",
        ]
    )
    inv(["override", "scaffold", "items/task.md.j2"])

    return runner


def _check_golden(name: str, actual_data: Any) -> None:
    path = GOLDENS_DIR / f"{name}.json"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual_data, indent=2) + "\n", encoding="utf-8")
        return
    assert path.exists(), f"golden file missing: {path}"
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual_data == expected, f"golden mismatch for {name!r}"


def _run_json(runner: CliRunner, args: list[str], expected_exit: int = 0) -> Any:
    r = runner.invoke(app, args)
    assert r.exit_code == expected_exit, f"{args!r} exited {r.exit_code}:\n{r.output}"
    return json.loads(r.output)


@pytest.mark.parametrize(
    ("golden_name", "args"),
    [
        ("list", ["list", "--json"]),
        ("list_feature", ["list", "--type", "feature", "--json"]),
        ("tree", ["tree", "--json"]),
        ("tree_feat", ["tree", "FEAT-000002", "--json"]),
        ("inbox_manager", ["inbox", "manager", "--json"]),
        ("search_login", ["search", "login", "--json"]),
        ("blocked", ["blocked", "--json"]),
        ("workload", ["workload", "--json"]),
        ("mine_manager", ["mine", "manager", "--json"]),
        ("task_refs_out", ["task", "3", "refs", "--json"]),
        ("task_refs_all", ["task", "3", "refs", "--all", "--json"]),
        ("feature_stories", ["feature", "2", "stories", "--json"]),
        ("task_subtasks", ["task", "3", "subtasks", "--json"]),
        ("review_findings", ["review", "6", "findings", "--json"]),
        ("subtask_st1_show", ["task", "3", "subtask", "ST1", "show", "--json"]),
        ("role_catalog", ["role", "catalog", "--json"]),
        ("role_manager_show", ["role", "manager", "show", "--json"]),
        ("role_qa_show", ["role", "qa", "show", "--json"]),
        ("role_list", ["role", "list", "--json"]),
        ("skill_show", ["skill", "8", "show", "--json"]),
        ("operator_show", ["operator", "op-alice", "show", "--json"]),
        ("operator_list", ["operator", "list", "--json"]),
        ("comments", ["task", "3", "comments", "--json"]),
        ("override_list", ["override", "list", "--json"]),
        ("override_diff", ["override", "diff", "items/task.md.j2", "--json"]),
        ("workflow_types", ["workflow", "types", "--json"]),
        ("workflow_subentity_kinds", ["workflow", "subentity-kinds", "--json"]),
        ("workflow_collections", ["workflow", "collections", "--json"]),
        ("workflow_statuses", ["workflow", "statuses", "--json"]),
        ("workflow_roles", ["workflow", "roles", "--json"]),
        ("workflow_lifecycles", ["workflow", "lifecycles", "--json"]),
        ("workflow_ref_kinds", ["workflow", "ref-kinds", "--json"]),
        ("workflow_views", ["workflow", "views", "--json"]),
    ],
)
def test_command_json_output_matches_its_golden_shape(
    golden_squad: CliRunner, golden_name: str, args: list[str]
) -> None:
    _check_golden(golden_name, _run_json(golden_squad, args))


def test_check_json_output_matches_its_golden_shape_and_exits_0(golden_squad: CliRunner) -> None:
    """sq check --json: the seeded squad may carry warnings (no errors, so exit 0)."""
    _check_golden("check_squad", _run_json(golden_squad, ["check", "--json"], expected_exit=0))


def test_inbox_json_lines_and_regions_stay_index_aligned(golden_squad: CliRunner) -> None:
    """`lines` and `regions` are two parallel arrays built off one paired list (`InboxLine`) —
    nothing in the payload states the alignment invariant, so pin it directly: for every
    item, and especially the multi-hit one the fixture already produces (an item-level line
    and a sub-entity one on the same task), the two arrays are the same length."""
    data = _run_json(golden_squad, ["inbox", "manager", "--json"])
    assert data  # the fixture's mentioned task always matches; an empty run would prove nothing
    for hit in data:
        assert len(hit["lines"]) == len(hit["regions"]) > 0
    multi = next(hit for hit in data if len(hit["lines"]) > 1)
    assert any(r is not None for r in multi["regions"])
    assert any(r is None for r in multi["regions"])


@pytest.mark.parametrize(
    ("golden_name", "generic_args", "typed_args"),
    [
        ("feature_show", ["show", "FEAT-000002", "--json"], ["feature", "2", "show", "--json"]),
        ("task_show", ["show", "TASK-000003", "--json"], ["task", "3", "show", "--json"]),
    ],
)
def test_the_generic_show_and_the_typed_show_converge_on_one_identical_golden_shape(
    golden_squad: CliRunner,
    golden_name: str,
    generic_args: list[str],
    typed_args: list[str],
) -> None:
    """`sq show <id>` and `sq <type> <n> show` are two entry points to the same render —
    one golden proves both converge, rather than pinning two byte-identical files."""
    generic = _run_json(golden_squad, generic_args)
    typed = _run_json(golden_squad, typed_args)
    assert generic == typed
    _check_golden(golden_name, generic)
