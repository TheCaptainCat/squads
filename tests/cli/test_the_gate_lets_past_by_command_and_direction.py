"""On a squad whose schema differs from the package's, only the commands that declare a ground
get past the gate, each for the directions it declares: ``sq migrate up`` behind; ``sq migrate
help`` and ``sq migrate chlog`` behind and ahead. Everything else, ``repad``, ``rename-type`` and
``rename-status`` included, is refused with the message for the direction, and a refused command
changes no file. ``--help`` is let past only when given as an option of its own.
"""

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from _gate_layouts import (
    OUTSIDE,
    OVERRIDES,
    RESOLVING,
    digest,
    lay_out,
    squad,
)
from squads._cli import app

_BEHIND_MESSAGE = "Run sq migrate up to upgrade it"
_AHEAD_MESSAGE = "Upgrade the squads package"

_COMMANDS: dict[str, list[str]] = {
    "migrate-up": ["migrate", "up"],
    "migrate-help": ["migrate", "help"],
    "migrate-chlog": ["migrate", "chlog", "v0.14.0..v0.15.0"],
    "migrate-repad": ["migrate", "repad", "7"],
    "migrate-rename-type": ["migrate", "rename-type", "task", "guide"],
    "migrate-rename-status": ["migrate", "rename-status", "task", "InProgress", "InReview"],
    "list": ["list"],
    "repair": ["repair"],
    "check": ["check"],
}


def _grants() -> dict[str, tuple[bool, bool]]:
    from squads._cli._migrate import migrate_grants

    return {f"migrate-{name}": (g.behind, g.ahead) for name, g in migrate_grants().items()}


def _allowed(direction: str, command: str) -> bool:
    if direction == "equal":
        return True
    behind, ahead = _grants().get(command, (False, False))
    return behind if direction == "behind" else ahead


def _run(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sq", *args])
    result = CliRunner().invoke(app, args)
    return result.exit_code, result.output


@pytest.mark.parametrize("override", OVERRIDES)
@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize("direction", ["behind", "ahead", "equal"])
def test_a_command_gets_past_the_gate_only_by_the_grant_it_declares(
    direction: str, command: str, override: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, direction, override)
    before = digest(root)

    code, output = _run(_COMMANDS[command], root, monkeypatch)

    message = {"behind": _BEHIND_MESSAGE, "ahead": _AHEAD_MESSAGE}.get(direction, "\0")
    if _allowed(direction, command):
        assert _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output, output
    else:
        assert code == 1, output
        assert message in output
        assert digest(root) == before
    if direction == "ahead" and command == "migrate-up":
        assert "override" not in output and "workflow lint" not in output


@pytest.mark.parametrize("direction", ["behind", "ahead"])
@pytest.mark.parametrize("command", _COMMANDS)
def test_help_is_never_gated(
    direction: str, command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, direction, "none")

    code, output = _run([*_COMMANDS[command], "--help"], root, monkeypatch)

    assert code == 0, output
    assert _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output


@pytest.mark.parametrize(("layout", "target"), RESOLVING)
@pytest.mark.parametrize("command", ["migrate-repad", "list", "repair", "migrate-up"])
@pytest.mark.parametrize("direction", ["behind", "ahead", "equal"])
def test_the_gate_holds_when_c_names_a_folder_that_resolves_the_squad(
    layout: str,
    target: str,
    command: str,
    direction: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = squad(tmp_path, direction, "none")
    folder = lay_out(root, layout)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    before = digest(tmp_path)

    code, output = _run(
        ["-C", str(root if target == "project" else folder), *_COMMANDS[command]],
        elsewhere,
        monkeypatch,
    )

    if _allowed(direction, command):
        assert _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output, output
    else:
        assert code == 1, output
        assert (_BEHIND_MESSAGE if direction == "behind" else _AHEAD_MESSAGE) in output
        assert digest(tmp_path) == before


@pytest.mark.parametrize("layout", OUTSIDE)
@pytest.mark.parametrize("command", ["migrate-repad", "list", "repair", "migrate-up"])
@pytest.mark.parametrize("direction", ["behind", "ahead", "equal"])
def test_a_squad_folder_outside_its_project_is_not_a_squad_from_there_and_nothing_is_written(
    layout: str, command: str, direction: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, direction, "none")
    folder = lay_out(root, layout)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    before = digest(tmp_path)

    code, output = _run(["-C", str(folder), *_COMMANDS[command]], elsewhere, monkeypatch)

    assert code == 1, output
    assert "no .squads.toml found in" in " ".join(output.split())
    assert digest(tmp_path) == before


def test_a_folder_in_no_squad_is_never_given_a_squad_s_stamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lone = tmp_path / "lone"
    lone.mkdir()

    code, output = _run(["-C", str(lone), "repair"], tmp_path, monkeypatch)

    assert code == 1 and str(lone) in " ".join(output.split())
    assert _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output


#: Arguments that merely spell the help option: after ``--`` or as an option's value.
_LOOKS_LIKE_HELP = {
    "value-of-an-option": ["task", "3", "comment", "--as", "manager", "-m", "--help"],
    "short-h": ["task", "3", "comment", "--as", "manager", "-m", "-h"],
    "after-the-separator": ["create", "task", "--author", "manager", "--", "--help"],
}


@pytest.mark.parametrize("row", _LOOKS_LIKE_HELP)
@pytest.mark.parametrize("direction", ["behind", "ahead"])
def test_an_argument_that_only_spells_help_does_not_open_the_gate(
    row: str, direction: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, direction, "none")
    before = digest(root)

    code, output = _run(_LOOKS_LIKE_HELP[row], root, monkeypatch)

    assert code == 1, output
    assert (_BEHIND_MESSAGE if direction == "behind" else _AHEAD_MESSAGE) in output
    assert digest(root) == before


@pytest.mark.parametrize("command", ["migrate-up", "migrate-help", "migrate-chlog"])
def test_a_behind_squad_is_not_told_to_run_the_command_the_gate_refuses(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, "behind", "none")

    _, output = _run(_COMMANDS[command], root, monkeypatch)

    assert "sq sync" not in output.replace(
        "run `sq sync` to regenerate the agent files "
        "(pointers, skills, CLAUDE.md/AGENTS.md sections)",
        "",
    )


def test_outside_a_squad_the_migrate_commands_behave_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, output = _run(["migrate", "help"], tmp_path, monkeypatch)
    assert code == 0, output
    code, output = _run(["migrate", "repad", "7"], tmp_path, monkeypatch)
    assert code in (0, 1) and _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output


@pytest.mark.parametrize(
    "command", ["migrate-repad", "migrate-rename-type", "migrate-rename-status"]
)
def test_the_three_writing_verbs_still_do_their_work_on_a_current_squad(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, "equal", "none")
    before = digest(root)

    code, output = _run(_COMMANDS[command], root, monkeypatch)

    assert code == 0, output
    assert digest(root) != before


_HELP_SHAPES = [
    (["list", "--help"], True),
    (["task", "3", "comment", "-m", "--help"], False),
    (["task", "3", "comment", "-m", "-m", "--help"], True),
    (["task", "3", "comment", "--as", "x", "-m", "-m", "-m", "--help"], False),
    (["task", "3", "comment", "-m", "-h"], False),
    (["create", "task", "--", "--help"], False),
    (["migrate", "repad", "7", "--help"], True),
]


@pytest.mark.parametrize(("argv", "expected"), _HELP_SHAPES)
def test_help_is_recognised_only_where_the_parser_would_treat_it_as_help(
    argv: list[str], expected: bool
) -> None:
    from squads._cli._common import help_requested

    assert help_requested(argv) is expected
