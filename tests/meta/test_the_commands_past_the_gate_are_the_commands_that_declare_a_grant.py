"""The set of commands that get past the schema gate on a mismatched squad is, for each
direction, exactly the set whose declared grant covers that direction. Every top-level command
and group of the app and every verb of ``sq migrate`` and ``sq override`` is invoked on a squad
stamped behind and on one stamped ahead, and the ones the gate does not refuse are collected. The
two literal sets below are the only place the expectation is written, so adding a grant is a
visible change here.
"""

import shutil
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._cli._common import GATED_GROUPS, grants_by_command
from squads._cli._migrate import migrate_app
from squads._cli._override import override_app

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
_GATE_MESSAGES = ("Run sq migrate up to upgrade it", "Upgrade the squads package")

_PAST_WHEN_BEHIND = {
    "migrate up",
    "migrate help",
    "migrate chlog",
    "override list",
    "override diff",
    "override update",
}
_PAST_WHEN_AHEAD = {"migrate help", "migrate chlog"}


_GATED_APPS = {"migrate": migrate_app, "override": override_app}


def _name(info_name: str | None, callback_name: str | None) -> str:
    return info_name or (callback_name or "").replace("_", "-")


def _every_command() -> list[tuple[str, ...]]:
    top = [
        (_name(info.name, getattr(info.callback, "__name__", None)),)
        for info in app.registered_commands
    ]
    groups = [(str(g.name),) for g in app.registered_groups if g.name not in GATED_GROUPS]
    verbs = [
        (group, _name(info.name, getattr(info.callback, "__name__", None)))
        for group, group_app in _GATED_APPS.items()
        for info in group_app.registered_commands
    ]
    return [*top, *groups, *verbs]


def _declared(direction: str) -> set[str]:
    return {
        f"{group} {name}"
        for group, group_app in _GATED_APPS.items()
        for name, grant in grants_by_command(group_app).items()
        if (grant.behind if direction == "behind" else grant.ahead)
    }


def _observed(direction: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> set[str]:
    past: set[str] = set()
    for index, path in enumerate(_every_command()):
        root = tmp_path / f"squad{index}"
        shutil.copytree(_CORPUS_DIR / "v0_14", root)
        if direction == "ahead":
            toml = (root / ".squads.toml").read_text(encoding="utf-8")
            (root / ".squads.toml").write_text(
                toml.replace('schema_version = "0.14"', 'schema_version = "0.99"'),
                encoding="utf-8",
            )
        monkeypatch.chdir(root)
        monkeypatch.setattr(sys, "argv", ["sq", *path])
        output = CliRunner().invoke(app, list(path)).output
        if not any(message in output for message in _GATE_MESSAGES):
            past.add(" ".join(path))
    return past


def test_the_walk_sees_the_whole_command_tree() -> None:
    names = {" ".join(p) for p in _every_command()}
    assert {"list", "repair", "check", "migrate up", "migrate repad", "role"} <= names
    assert len(names) > 20


@pytest.mark.parametrize(
    ("direction", "literal"), [("behind", _PAST_WHEN_BEHIND), ("ahead", _PAST_WHEN_AHEAD)]
)
def test_the_commands_past_the_gate_are_the_ones_that_declare_it(
    direction: str, literal: set[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed = _observed(direction, tmp_path, monkeypatch)

    assert observed == _declared(direction)
    assert observed == literal
