"""``-C`` reaches everything that decides what "here" means: the custom-type lookups that run
before the root callback, the context each in-process invocation binds, and every relative path
argument (``--file`` bodies and comments, the ``sq import`` event file).
"""

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app

_WIDGET_OVERRIDE = """\
[lifecycles.flow]
initial = "Open"
[lifecycles.flow.transitions]
Open = ["Done"]
Done = []

[items.widget]
prefix = "WID"
folder = "widgets"
lifecycle = "flow"
aliases = ["wid"]
"""

_MARKER = "NOTES-MARKER"


def _run(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch, **kw):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sq", *args])
    return CliRunner().invoke(app, args, **kw)


def _make_squad(root: Path, monkeypatch: pytest.MonkeyPatch, *, widget: bool) -> Path:
    root.mkdir(parents=True)
    done = _run(
        ["init", "--default-names", "--backend", "none", "--roles", "minimal"], root, monkeypatch
    )
    assert done.exit_code == 0, done.output
    if widget:
        overrides = root / "squads" / ".overrides"
        overrides.mkdir()
        (overrides / "workflow.toml").write_text(_WIDGET_OVERRIDE, encoding="utf-8")
        made = _run(["create", "widget", "First", "--author", "manager"], root, monkeypatch)
        assert made.exit_code == 0, made.output
    return root


@pytest.fixture
def here(tmp_path: Path) -> Path:
    folder = tmp_path / "here"
    folder.mkdir()
    return folder


_WIDGET_SHOW = ["widget", "1", "show"]


def test_a_custom_type_declared_only_in_the_c_squad_resolves_from_outside_it(
    tmp_path: Path, here: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    squad = _make_squad(tmp_path / "with-widget", monkeypatch, widget=True)
    number = "2"  # the first item created after the minimal roster

    shown = _run(["-C", str(squad), "widget", number, "show"], here, monkeypatch)
    create_help = _run(["-C", str(squad), "create", "widget", "--help"], here, monkeypatch)
    root_help = _run(["-C", str(squad), "--help"], here, monkeypatch)

    assert shown.exit_code == 0, shown.output
    assert create_help.exit_code == 0, create_help.output
    assert "widget" in root_help.output
    assert root_help.exit_code == 0


def test_a_broken_override_in_the_c_squad_is_reported_not_called_an_unknown_command(
    tmp_path: Path, here: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    squad = _make_squad(tmp_path / "broken", monkeypatch, widget=False)
    overrides = squad / "squads" / ".overrides"
    overrides.mkdir()
    (overrides / "workflow.toml").write_text("[items.widget\nnot toml ===", encoding="utf-8")

    _run(["list"], here, monkeypatch)  # leaves the previous invocation bound to `here`
    result = _run(["-C", str(squad), "widget", "2", "show"], here, monkeypatch)

    assert result.exit_code == 1, result.output
    assert "No such command" not in result.output
    assert "workflow.toml" in " ".join(result.output.split())


#: (squad A declares widget, squad B declares widget): the second run must see only its own.
_PAIRS = {
    "only the second declares it": (False, True),
    "only the first declares it": (True, False),
    "both declare it": (True, True),
    "neither declares it": (False, False),
}


@pytest.mark.parametrize("pair", _PAIRS)
def test_two_invocations_in_one_process_each_see_only_their_own_squad_s_types(
    pair: str, tmp_path: Path, here: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_declares, second_declares = _PAIRS[pair]
    first = _make_squad(tmp_path / "a", monkeypatch, widget=first_declares)
    second = _make_squad(tmp_path / "b", monkeypatch, widget=second_declares)

    ran_first = _run(["-C", str(first), "widget", "2", "show"], here, monkeypatch)
    ran_second = _run(["-C", str(second), "widget", "2", "show"], here, monkeypatch)

    assert (ran_first.exit_code == 0) == first_declares, ran_first.output
    assert (ran_second.exit_code == 0) == second_declares, ran_second.output


def test_a_bare_invocation_after_a_c_invocation_resolves_from_its_own_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _make_squad(tmp_path / "a", monkeypatch, widget=False)
    second = _make_squad(tmp_path / "b", monkeypatch, widget=False)
    for root, title in ((first, "Only in A"), (second, "Only in B")):
        made = _run(["create", "task", title, "--author", "manager"], root, monkeypatch)
        assert made.exit_code == 0, made.output

    via_c = _run(["-C", str(first), "list"], second, monkeypatch)
    bare = _run(["list"], second, monkeypatch)

    assert "Only in A" in via_c.output and "Only in B" not in via_c.output
    assert "Only in B" in bare.output and "Only in A" not in bare.output


# --- relative path arguments follow -C ---------------------------------------------------------

#: source -> (argv with a ``{file}`` slot, argv that reads back what it stored). The notes file
#: holds the marker text, or for ``import`` an event that creates a task titled with it.
_SOURCES = {
    "body": (["task", "2", "body", "--file", "{file}"], ["task", "2", "show", "--full"]),
    "comment": (
        ["task", "2", "comment", "--as", "manager", "--file", "{file}"],
        ["task", "2", "show", "--comments"],
    ),
    "create": (
        ["create", "task", "From file", "--author", "manager", "--file", "{file}"],
        ["task", "3", "show", "--full"],
    ),
    "board": (["board", "post", "--as", "manager", "--file", "{file}"], ["board", "list"]),
    "import": (["import", "{file}", "--as", "manager"], ["list"]),
}


def _notes_text(source: str) -> str:
    if source == "import":
        return f'{{"op":"create","type":"task","title":"{_MARKER}"}}\n'
    return f"{_MARKER}\n"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = _make_squad(tmp_path / "project", monkeypatch, widget=False)
    made = _run(["create", "task", "Host", "--author", "manager"], root, monkeypatch)
    assert made.exit_code == 0, made.output
    return root


@pytest.mark.parametrize("source", _SOURCES)
def test_a_relative_file_is_found_from_the_c_directory(
    source: str, project: Path, here: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write, read = _SOURCES[source]
    (project / "notes.md").write_text(_notes_text(source), encoding="utf-8")

    done = _run(
        ["-C", str(project), *[a.format(file="notes.md") for a in write]], here, monkeypatch
    )
    back = _run(["-C", str(project), *read], here, monkeypatch)

    assert done.exit_code == 0, done.output
    assert _MARKER in back.output


@pytest.mark.parametrize("source", _SOURCES)
def test_a_relative_file_is_not_found_without_c_when_it_is_not_in_the_working_directory(
    source: str, project: Path, here: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write, _ = _SOURCES[source]
    (project / "notes.md").write_text(_notes_text(source), encoding="utf-8")

    done = _run([a.format(file="notes.md") for a in write], project.parent / "here", monkeypatch)

    assert done.exit_code != 0


@pytest.mark.parametrize("source", _SOURCES)
def test_an_absolute_file_works_wherever_c_points(
    source: str, project: Path, here: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write, read = _SOURCES[source]
    absolute = tmp_path / "abs-notes.md"
    absolute.write_text(_notes_text(source), encoding="utf-8")

    done = _run(
        ["-C", str(project), *[a.format(file=str(absolute)) for a in write]], here, monkeypatch
    )
    back = _run(["-C", str(project), *read], here, monkeypatch)

    assert done.exit_code == 0, done.output
    assert _MARKER in back.output


@pytest.mark.parametrize("source", _SOURCES)
def test_a_dash_still_reads_standard_input(
    source: str, project: Path, here: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write, read = _SOURCES[source]

    done = _run(
        ["-C", str(project), *[a.format(file="-") for a in write]],
        here,
        monkeypatch,
        input=_notes_text(source),
    )
    back = _run(["-C", str(project), *read], here, monkeypatch)

    assert done.exit_code == 0, done.output
    assert _MARKER in back.output
