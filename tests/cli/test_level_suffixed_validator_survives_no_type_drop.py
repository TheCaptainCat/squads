"""A level-suffixed validator entry naming a dropped type does not stop the squad loading."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads import __version__
from squads._cli import app

_OVERRIDE = """\
[selected]
items = ["epic", "feature", "task", "bug", "decision", "milestone", "review", "guide",
  "skill", "role", "operator"]

[items.feature]
validators = ["ref_rule_target_present:contract@warn"]
"""


def _run(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr("sys.argv", ["sq", *args])
    return CliRunner().invoke(app, args)


def test_a_level_suffixed_entry_for_a_dropped_type_leaves_the_squad_usable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    done = _run(
        ["init", "--default-names", "--backend", "none", "--roles", "minimal"],
        tmp_path,
        monkeypatch,
    )
    assert done.exit_code == 0, done.output
    overrides = tmp_path / "squads" / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{_OVERRIDE}", encoding="utf-8"
    )

    listed = _run(["list"], tmp_path, monkeypatch)
    lint = _run(["workflow", "lint"], tmp_path, monkeypatch)

    assert listed.exit_code == 0, listed.output
    assert lint.exit_code == 0, lint.output
    assert "ref_rule_target_present" not in lint.output
