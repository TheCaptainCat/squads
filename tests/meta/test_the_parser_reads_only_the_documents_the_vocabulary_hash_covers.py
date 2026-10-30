"""Repo-hygiene gate: parsing a command reads only the workflow override from the override folder,
so the vocabulary hash covers every document the parser reads."""

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._api._vocabulary import OVERRIDE_DOCUMENT
from squads._cli import _common as common
from squads._cli import app
from squads._paths import SquadPaths

#: Documents of the override folder the parser must never open.
OTHERS = (
    "playbook.toml",
    "roles.toml",
    "roles/probe.toml",
    "templates/items/task.md.j2",
    "views/probe.toml",
)


class _Opens:
    """Records the files opened under a folder while it is switched on."""

    def __init__(self, folder: Path) -> None:
        self.folder = str(folder)
        self.on = False
        self.seen: set[str] = set()

    def __call__(self, event: str, args: tuple[object, ...]) -> None:
        if self.on and event == "open" and isinstance(args[0], str | Path):
            name = str(args[0])
            if name.startswith(self.folder):
                self.seen.add(name[len(self.folder) :].lstrip("/\\").replace("\\", "/"))


def test_parsing_a_command_opens_no_override_document_the_hash_leaves_out(
    project: SquadPaths,
) -> None:
    overrides = project.squad_dir / ".overrides"
    for name in OTHERS:
        path = overrides / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# a document the parser has no business reading\n", encoding="utf-8")
    opens = _Opens(overrides)
    sys.addaudithook(opens)
    opens.on = True
    try:
        common.bind_active_spec(project.root)
        runner = CliRunner()
        for args in (["--help"], ["task", "--help"], ["task", "1", "show", "--help"]):
            runner.invoke(app, args)
    finally:
        opens.on = False
    assert opens.seen <= {OVERRIDE_DOCUMENT.removeprefix(".overrides/")}, sorted(opens.seen)


@pytest.mark.parametrize("name", OTHERS)
def test_the_scan_sees_a_document_that_is_opened(project: SquadPaths, name: str) -> None:
    """A read of any one of the documents shows up in the record, so the guard can fail."""
    overrides = project.squad_dir / ".overrides"
    path = overrides / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n", encoding="utf-8")
    opens = _Opens(overrides)
    sys.addaudithook(opens)
    opens.on = True
    try:
        path.read_text(encoding="utf-8")
    finally:
        opens.on = False
    assert opens.seen == {name}
