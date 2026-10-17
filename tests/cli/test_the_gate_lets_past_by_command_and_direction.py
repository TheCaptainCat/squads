"""On a squad whose schema differs from the package's, only the commands that declare a ground
get past the gate, each for the directions it declares: ``sq migrate up`` behind; ``sq migrate
help`` and ``sq migrate chlog`` behind and ahead. Everything else, ``repad``, ``rename-type`` and
``rename-status`` included, is refused with the message for the direction, and a refused command
changes no file. ``--help`` is let past only when given as an option of its own.
"""

import hashlib
import shutil
import sys
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads import __version__
from squads._cli import app
from squads._models._schema import SCHEMA_VERSION

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
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

#: What each direction lets past, written once here and compared with the declared grants in
#: ``tests/meta``; the table below reads the expectation from the grants, not from this.
_OVERRIDES = ["none", "valid", "conflicting", "does-not-load"]


def _stamp(root: Path, schema: str) -> None:
    text = (root / ".squads.toml").read_text(encoding="utf-8")
    current = tomllib.loads(text)["schema_version"]
    (root / ".squads.toml").write_text(
        text.replace(f'schema_version = "{current}"', f'schema_version = "{schema}"'),
        encoding="utf-8",
    )


def _override(root: Path, kind: str) -> None:
    if kind == "none":
        return
    folder = root / ".overrides"
    folder.mkdir()
    header = f"# squads:override-base:{__version__}\n"
    body = {
        "valid": '[ref_kinds.mirrors]\nlabel = "Mirrors"\nhint = "mirror"\n',
        "conflicting": "[selected]\nitems = ['task', 'bug', 'feature', 'epic']\n",
        "does-not-load": "[items.broken\nnot toml ===",
    }[kind]
    (folder / "workflow.toml").write_text(header + body, encoding="utf-8")


def _squad(tmp_path: Path, direction: str, override: str) -> Path:
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS_DIR / ("v0_14" if direction != "equal" else "v0_15"), root)
    if direction == "ahead":
        _stamp(root, "0.99")
    elif direction == "equal":
        _stamp(root, SCHEMA_VERSION)
    _override(root, override)
    return root


def _digest(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != ".reflog.jsonl"
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


@pytest.mark.parametrize("override", _OVERRIDES)
@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize("direction", ["behind", "ahead", "equal"])
def test_a_command_gets_past_the_gate_only_by_the_grant_it_declares(
    direction: str, command: str, override: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _squad(tmp_path, direction, override)
    before = _digest(root)

    code, output = _run(_COMMANDS[command], root, monkeypatch)

    message = {"behind": _BEHIND_MESSAGE, "ahead": _AHEAD_MESSAGE}.get(direction, "\0")
    if _allowed(direction, command):
        assert _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output, output
    else:
        assert code == 1, output
        assert message in output
        assert _digest(root) == before
    if direction == "ahead" and command == "migrate-up":
        assert "override" not in output and "workflow lint" not in output


@pytest.mark.parametrize("direction", ["behind", "ahead"])
@pytest.mark.parametrize("command", _COMMANDS)
def test_help_is_never_gated(
    direction: str, command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _squad(tmp_path, direction, "none")

    code, output = _run([*_COMMANDS[command], "--help"], root, monkeypatch)

    assert code == 0, output
    assert _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output


def _move_into(root: Path, sub: str) -> Path:
    folder = root / sub
    folder.mkdir(parents=True, exist_ok=True)
    top = sub.split("/")[0]
    for child in [c for c in root.iterdir() if c.name not in (".squads.toml", top)]:
        shutil.move(child, folder / child.name)
    return folder


def _set_squad_dir(root: Path, value: str) -> None:
    text = (root / ".squads.toml").read_text(encoding="utf-8")
    (root / ".squads.toml").write_text(text.replace('squad_dir = "."', f'squad_dir = "{value}"'))


def _lay_out(root: Path, layout: str) -> Path:  # noqa: PLR0911 - one return per layout
    """Arrange the squad at *root* as *layout* says; return the folder ``--dir`` is given."""
    if layout == "root":
        return root
    if layout == "dot-slash":
        _set_squad_dir(root, "./")
        return root
    if layout in ("outside-relative", "outside-absolute"):
        shared = root.parent / "shared"
        shared.mkdir()
        for child in [c for c in root.iterdir() if c.name != ".squads.toml"]:
            shutil.move(child, shared / child.name)
        _set_squad_dir(root, "../shared" if layout == "outside-relative" else str(shared))
        return shared
    if layout == "symlinked":
        real = _move_into(root, "real")
        (root / "link").symlink_to(real, target_is_directory=True)
        _set_squad_dir(root, "link")
        return root / "link"
    sub = {"nested": "squads", "multi-level": "work/squad", "renamed": "team"}.get(layout, "squads")
    folder = _move_into(root, sub)
    _set_squad_dir(root, sub)
    if layout == "at-the-project-root":
        return root
    if layout == "at-a-sibling-folder":
        (root / "docs").mkdir()
        return root / "docs"
    return folder


_LAYOUTS = ["nested", "root", "dot-slash", "multi-level", "renamed", "symlinked"]
_NOT_THE_SQUAD = [
    "at-the-project-root",
    "at-a-sibling-folder",
    "outside-relative",
    "outside-absolute",
]


@pytest.mark.parametrize("layout", _LAYOUTS)
@pytest.mark.parametrize("command", ["migrate-repad", "list", "repair", "migrate-up"])
@pytest.mark.parametrize("direction", ["behind", "ahead", "equal"])
def test_the_gate_holds_when_the_squad_is_named_with_dir_from_outside_it(
    layout: str, command: str, direction: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _squad(tmp_path, direction, "none")
    folder = _lay_out(root, layout)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    before = _digest(root)

    code, output = _run(["--dir", str(folder), *_COMMANDS[command]], elsewhere, monkeypatch)

    if _allowed(direction, command):
        assert _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output, output
    else:
        assert code == 1, output
        assert (_BEHIND_MESSAGE if direction == "behind" else _AHEAD_MESSAGE) in output
        assert _digest(root) == before


@pytest.mark.parametrize("layout", _NOT_THE_SQUAD)
@pytest.mark.parametrize("command", ["migrate-repad", "list", "repair", "migrate-up"])
@pytest.mark.parametrize("direction", ["behind", "ahead", "equal"])
def test_a_folder_that_is_not_the_squads_own_is_refused_and_nothing_is_written(
    layout: str, command: str, direction: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _squad(tmp_path, direction, "none")
    folder = _lay_out(root, layout)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    before = _digest(tmp_path)

    code, output = _run(["--dir", str(folder), *_COMMANDS[command]], elsewhere, monkeypatch)

    assert code == 1, output
    said = " ".join(output.split())
    assert "is not the squad folder" in said or "holds squad data" in said
    assert _digest(tmp_path) == before


def test_a_folder_in_no_squad_is_never_given_a_squad_s_stamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lone = tmp_path / "lone"
    lone.mkdir()

    code, output = _run(["--dir", str(lone), "repair"], tmp_path, monkeypatch)

    assert code in (0, 1) and _BEHIND_MESSAGE not in output and _AHEAD_MESSAGE not in output


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
    root = _squad(tmp_path, direction, "none")
    before = _digest(root)

    code, output = _run(_LOOKS_LIKE_HELP[row], root, monkeypatch)

    assert code == 1, output
    assert (_BEHIND_MESSAGE if direction == "behind" else _AHEAD_MESSAGE) in output
    assert _digest(root) == before


@pytest.mark.parametrize("command", ["migrate-up", "migrate-help", "migrate-chlog"])
def test_a_behind_squad_is_not_told_to_run_the_command_the_gate_refuses(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _squad(tmp_path, "behind", "none")

    _, output = _run(_COMMANDS[command], root, monkeypatch)

    assert "sq sync" not in output.replace("run `sq sync` to refresh managed files", "")


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
    root = _squad(tmp_path, "equal", "none")
    before = _digest(root)

    code, output = _run(_COMMANDS[command], root, monkeypatch)

    assert code == 0, output
    assert _digest(root) != before


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
