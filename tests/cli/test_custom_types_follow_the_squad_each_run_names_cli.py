"""Custom types, their aliases and their verbs resolve from the spec of the squad `-C` names, run
after run in one process: another squad's alias or verb is not served from an earlier run."""

import re
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads import __version__
from squads._cli import app

_OVERRIDE = """\
# squads:override-base:{version}
[items.widget]
prefix = "WID"
folder = "{folder}"
lifecycle = "work"
aliases = ["{alias}"]
{extra}"""


def _run(args: list[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "argv", ["sq", *args])
    return CliRunner().invoke(app, args)


@pytest.fixture
def squads_ab(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Two squads declaring `widget` with different aliases and folders, one widget in each;
    only the first gives it sub-tasks."""
    roots: dict[str, Path] = {}
    for name, alias in (("a", "wa"), ("b", "wb")):
        root = tmp_path / name
        root.mkdir()
        init = _run(
            ["-C", str(root), "init", "--default-names", "--backend", "none", "--roles", "minimal"],
            monkeypatch,
        )
        assert init.exit_code == 0, init.output
        overrides = root / "squads" / ".overrides"
        overrides.mkdir()
        (overrides / "workflow.toml").write_text(
            _OVERRIDE.format(
                version=__version__,
                folder=f"widgets-{name}",
                alias=alias,
                extra='subentity_kind = "subtask"\n' if name == "a" else "",
            ),
            encoding="utf-8",
        )
        roots[name] = root
    return roots


def _widget(root: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    created = _run(
        ["-C", str(root), "create", "widget", f"widget {root.name}", "--author", "manager"],
        monkeypatch,
    )
    assert created.exit_code == 0, created.output
    match = re.search(r"WID-0*(\d+)", created.output)
    assert match, created.output
    return match.group(1)


@pytest.mark.parametrize(
    ("first", "second", "exit_code"),
    [
        (("a", "wa"), ("b", "wb"), 0),
        (("a", "wa"), ("b", "wa"), 2),
    ],
)
def test_a_later_run_resolves_the_alias_of_its_own_squad(
    squads_ab, monkeypatch, first, second, exit_code
) -> None:
    numbers = {name: _widget(root, monkeypatch) for name, root in squads_ab.items()}

    for name, alias in (first, second):
        result = _run(["-C", str(squads_ab[name]), alias, numbers[name], "show"], monkeypatch)

    assert result.exit_code == exit_code, result.output
    if exit_code == 0:
        assert f"widget {second[0]}" in result.output


@pytest.mark.parametrize(("second", "exit_code"), [("b", 2), ("a", 0)])
def test_a_later_run_builds_the_verbs_its_own_squad_declares(
    squads_ab, monkeypatch, second, exit_code
) -> None:
    numbers = {name: _widget(root, monkeypatch) for name, root in squads_ab.items()}
    alias = {"a": "wa", "b": "wb"}

    _run(["-C", str(squads_ab["a"]), "wa", numbers["a"], "subtasks"], monkeypatch)
    result = _run(
        ["-C", str(squads_ab[second]), alias[second], numbers[second], "subtasks"], monkeypatch
    )

    assert result.exit_code == exit_code, result.output
