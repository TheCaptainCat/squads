"""A flag several commands share is declared once, in ``_cli/_common.py``: no other CLI module
builds a ``typer.Option`` for one of these names, so its wording cannot drift per command.
"""

import ast
from pathlib import Path

import squads

CLI_DIR = Path(squads.__file__).parent / "_cli"

#: Flag names whose every use goes through a shared declaration.
SHARED_FLAGS = frozenset(
    {
        "--file",
        "-m",
        "--message",
        "--append",
        "--raw",
        "--desc",
        "--author",
        "--as",
        "--yes",
        "--tech",
        "--depth",
        "--assignee",
    }
)


def _option_calls(source: str) -> list[tuple[int, set[str]]]:
    calls: list[tuple[int, set[str]]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "Option":
                continue
            names = {
                a.value
                for a in node.args
                if isinstance(a, ast.Constant) and isinstance(a.value, str)
            }
            calls.append((node.lineno, names & SHARED_FLAGS))
    return calls


def test_the_scan_finds_a_literal_shared_flag_option() -> None:
    assert _option_calls('typer.Option(None, "--file", help="x")') == [(1, {"--file"})]
    assert _option_calls('typer.Option(None, "--title", help="x")') == [(1, set())]


def test_no_cli_module_outside_common_declares_a_shared_flag_itself() -> None:
    found = [
        f"{path.name}:{line} declares {sorted(names)}"
        for path in sorted(CLI_DIR.glob("*.py"))
        if path.name != "_common.py"
        for line, names in _option_calls(path.read_text(encoding="utf-8"))
        if names
    ]
    assert not found, "\n".join(found)
