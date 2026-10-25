"""`--help` as an option of a verb under an addressed group renders without an address that
resolves: in a squad with no such item, with a number of another type, and on a squad behind
the package's schema. `--help` as an option's value is not a help request, so the address is
resolved and a wrong-type number or a behind-schema squad is refused."""

import sys

import pytest

from _gate_layouts import squad
from _selection_table import write_override

pytestmark = pytest.mark.anyio

_FINDING_IMPACT = (
    '[subentity_kinds.finding]\nfields = [{ code = "impact", label = "Impact", '
    'collection = "severity", required = true, default = "medium" }]\n'
)

# (squad, command, exit code, text in the output)
_ROWS = [
    ("fresh", ["task", "1", "show", "--help"], 0, "sq task N show"),
    ("fresh", ["task", "999999", "show", "--help"], 0, "sq task N show"),
    ("fresh", ["task", "1", "comment", "--help"], 0, "sq task N comment"),
    ("fresh", ["skill", "999999", "show", "--help"], 0, "sq skill <slug|id|n> show"),
    ("fresh", ["operator", "999999", "show", "--help"], 0, "sq operator <slug|id|n> show"),
    ("fresh", ["role", "999999", "comment", "--help"], 0, "sq role <slug|id|n> comment"),
    ("fresh", ["task", "1", "show"], 1, "not a task"),
    ("fresh", ["task", "1", "comment", "-m", "--help"], 1, "not a task"),
    ("behind", ["task", "1", "comment", "--help"], 0, "sq task N comment"),
    ("behind", ["task", "1", "show"], 1, "sq migrate up"),
    (
        "declared",
        ["review", "999", "finding", "1", "update", "--impact", "--help"],
        1,
        "no item",
    ),
]


@pytest.mark.parametrize(
    ("kind", "args", "exit_code", "text"),
    [pytest.param(*row, id=" ".join(row[1])) for row in _ROWS],
)
async def test_help_never_needs_an_address_and_a_call_without_help_always_has_one(
    project, tmp_path, invoke, monkeypatch, kind, args, exit_code, text
) -> None:
    if kind == "behind":
        monkeypatch.chdir(squad(tmp_path, "behind", "none"))
    if kind == "declared":
        write_override(project.squad_dir, _FINDING_IMPACT)
    monkeypatch.setattr(sys, "argv", ["sq", *args])

    result = await invoke(args)

    assert isinstance(result.exception, (SystemExit, type(None))), result.exception
    assert result.exit_code == exit_code, result.output
    assert text in result.output
