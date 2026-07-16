"""`sq show <id> --raw` is a deterministic, markdown-preview-clean dossier — zero Rich chrome
(no box-drawing header panel, no space-aligned summary table, no ``=== … ===`` separators):
an ``#`` title, a bullet list of metadata, the body verbatim, and (``--full``/``--comments``)
one section per sub-entity and a Discussion section. Pinned against a golden text file so a
future change to the structure is a deliberate, reviewed diff — the ``--json`` analogue of this
same rendering path is golden-pinned in ``tests/cli/test_json_output_shape.py``.

Regenerating the golden: set ``UPDATE_GOLDENS=1`` and run this module; commit the diff.
"""

import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from squads._cli import app

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"


@pytest.fixture
def raw_dossier_squad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any
) -> CliRunner:
    """A task with every raw-dossier metadata field populated, a sub-entity, and a comment.

    Builds a parent feature with a story, the task under test (given a parent, priority,
    assignee, label, a ``depends-on`` ref, a subtask mapped to the story, a body, and a
    comment), and a second item as the ref target.
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup step {args!r} failed:\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "feature", "Parent feature", "--author", "manager"])
    inv(["create", "task", "Ship it", "--author", "manager", "--parent", "FEAT-000002"])
    inv(["create", "bug", "Something broke", "--author", "manager"])
    inv(["feature", "2", "add-story", "As a user I can log in"])
    inv(
        [
            "task",
            "3",
            "update",
            "--priority",
            "high",
            "--assignee",
            "manager",
            "--add-label",
            "backend",
        ]
    )
    inv(["task", "3", "ref", "add", "BUG-000004", "--kind", "depends-on"])
    inv(["task", "3", "add-subtask", "Write handler", "--story", "US1"])
    inv(["task", "3", "subtask", "1", "body", "-m", "Implement the handler function."])
    inv(
        [
            "task",
            "3",
            "body",
            "-m",
            "## Overview\n\nSome **bold** text and a list:\n\n- one\n- two",
        ]
    )
    inv(["task", "3", "comment", "--as", "manager", "-m", "Please review the login handler."])

    return runner


def _check_golden(name: str, actual: str) -> None:
    path = GOLDENS_DIR / f"{name}.txt"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    assert path.exists(), f"golden file missing: {path}"
    assert actual == path.read_text(encoding="utf-8"), f"golden mismatch for {name!r}"


def test_show_raw_full_comments_matches_the_clean_markdown_golden(
    raw_dossier_squad: CliRunner,
) -> None:
    r = raw_dossier_squad.invoke(app, ["task", "3", "show", "--raw", "--full", "--comments"])
    assert r.exit_code == 0, r.output
    _check_golden("item_show_raw", r.output)


def test_show_raw_has_zero_rich_chrome(raw_dossier_squad: CliRunner) -> None:
    """No box-drawing header panel, no space-aligned summary table, no ``=== … ===`` panes."""
    r = raw_dossier_squad.invoke(app, ["task", "3", "show", "--raw", "--full", "--comments"])
    assert r.exit_code == 0, r.output
    for box_char in "╭╮╰╯│─":
        assert box_char not in r.output
    assert "===" not in r.output
    assert r.output.startswith("# TASK-3 — Ship it\n")


def test_show_raw_without_full_or_comments_omits_those_sections(
    raw_dossier_squad: CliRunner,
) -> None:
    r = raw_dossier_squad.invoke(app, ["task", "3", "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert "## Subtask" not in r.output
    assert "## Discussion" not in r.output


def test_show_raw_comments_empty_discussion_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    r = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["create", "task", "No comments yet", "--author", "manager"])
    assert r.exit_code == 0, r.output

    shown = runner.invoke(app, ["task", "2", "show", "--raw", "--comments"])
    assert shown.exit_code == 0, shown.output
    assert "## Discussion" in shown.output
    assert "_(no discussion)_" in shown.output
