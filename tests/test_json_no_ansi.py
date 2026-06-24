"""Regression test for BUG-000183: --json output must be ANSI-free even when FORCE_COLOR is set.

The root cause was that all --json paths used ``console.print_json()``, which honours
FORCE_COLOR / CLICOLOR_FORCE / PY_COLORS and injects ANSI escape codes into stdout even when
output is piped.  The fix routes every --json path through ``print_json_clean()``, which uses
plain ``print()`` and is unconditionally color-free.

This test re-introduces the forced-color environment within a single test (bypassing the
suite-wide suppression in conftest.py) to confirm that --json output is clean regardless.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from squads._cli import app


@pytest.fixture
def force_color_squad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any
) -> CliRunner:
    """A minimal squad in a temp dir with FORCE_COLOR=3 active, returns a CliRunner.

    Sets up the squad while color-forcing vars are stripped (via the autouse fixture),
    then re-injects FORCE_COLOR=3 so the test runner exercises the forced-color path.
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup step {args!r} failed (exit {r.exit_code}):\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "task", "Test task", "--author", "manager"])

    # Re-inject forced-color after setup so only the test assertions run under it.
    monkeypatch.setenv("FORCE_COLOR", "3")

    return runner


def test_json_output_is_ansi_free_under_force_color(
    force_color_squad: CliRunner,
) -> None:
    """--json output parses cleanly and contains no ANSI escape codes when FORCE_COLOR is set.

    Simulates the Claude Code agent harness environment (FORCE_COLOR=3) and confirms that
    ``sq list --json`` emits valid, ANSI-free JSON regardless.  This is a regression test
    for BUG-000183.
    """
    result = force_color_squad.invoke(app, ["list", "--json"])

    assert result.exit_code == 0, (
        f"sq list --json exited {result.exit_code} under FORCE_COLOR=3:\n{result.output}"
    )

    # (a) The output must parse as valid JSON — no JSONDecodeError.
    data = json.loads(result.output)

    # (b) The raw output must contain no ANSI escape sequences.
    assert "\x1b" not in result.output, (
        "sq list --json emitted ANSI escape codes under FORCE_COLOR=3 — "
        "JSON output must be unconditionally color-free (BUG-000183)."
    )

    # Sanity-check the shape: should be a non-empty list containing the created task.
    assert isinstance(data, list)
    assert len(data) >= 1
