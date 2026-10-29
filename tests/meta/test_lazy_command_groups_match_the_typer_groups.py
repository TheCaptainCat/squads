"""Repo-hygiene gate: the root builds each command group when it is looked up, from a table that
names its module and Typer. The table must list exactly the public group Typers the `_cli` modules
define, and building every row must give the group the root lists under that name."""

import ast
from pathlib import Path

import typer.main
from typer._click import Context  # underscore is upstream's own private module path, not ours
from typer.testing import CliRunner

from squads._cli import LAZY_GROUPS, app


def _is_typer_call(node: ast.expr) -> bool:
    """Whether *node* calls ``Typer`` as ``typer.Typer(...)`` or a bare ``Typer(...)``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Attribute) and func.attr == "Typer") or (
        isinstance(func, ast.Name) and func.id == "Typer"
    )


def _group_typers() -> frozenset[tuple[str, str]]:
    """Each public module-level ``name = typer.Typer(...)`` in ``squads._cli``: (module, name)."""
    cli = Path(__file__).resolve().parents[2] / "src" / "squads" / "_cli"
    found: set[tuple[str, str]] = set()
    for path in sorted(cli.glob("_*.py")):
        if path.name == "__init__.py":
            continue
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            if not _is_typer_call(value):
                continue
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    found.add((f"squads._cli.{path.stem}", target.id))
    return frozenset(found)


def test_the_lazy_table_names_every_group_typer_the_cli_modules_define() -> None:
    assert {(g.module, g.attr) for g in LAZY_GROUPS} == _group_typers()


def test_each_lazy_group_builds_under_its_name_with_its_summary() -> None:
    root = typer.main.get_command(app)
    for group in LAZY_GROUPS:
        built = root.commands[group.name]  # type: ignore[attr-defined]
        assert built.name == group.name
        assert built.help == group.help


def test_the_root_lists_the_lazy_groups_in_table_order() -> None:
    root = typer.main.get_command(app)
    names = root.list_commands(Context(root))  # type: ignore[attr-defined]
    listed = [n for n in names if n in {g.name for g in LAZY_GROUPS}]
    assert listed == [g.name for g in LAZY_GROUPS]


def test_the_root_help_lists_every_lazy_group() -> None:
    help_text = CliRunner().invoke(app, ["--help"]).output
    assert [g.name for g in LAZY_GROUPS if f"│ {g.name} " not in help_text] == []
