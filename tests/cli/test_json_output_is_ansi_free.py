"""``--json`` output stays ANSI-free even when FORCE_COLOR is re-injected inside the test —
a regression class where every --json path used console.print_json(), which honours
FORCE_COLOR/CLICOLOR_FORCE/PY_COLORS and injects escape codes even into piped output.

Deliberately defeats the conftest-wide FORCE_COLOR suppression so this exercises the real
production code path, not just the harness's ambient suppression — a test that merely relied
on the autouse strip would not catch this regression.
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
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup step {args!r} failed:\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "task", "Test task", "--author", "manager"])

    monkeypatch.setenv("FORCE_COLOR", "3")  # re-inject after setup, before the assertion below
    return runner


def test_json_output_has_no_ansi_escapes_under_forced_color(
    force_color_squad: CliRunner,
) -> None:
    result = force_color_squad.invoke(app, ["list", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)  # must parse cleanly — no stray escape codes
    assert "\x1b" not in result.output

    assert isinstance(data, list)
    assert len(data) >= 1
