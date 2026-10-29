"""The role, skill and operator `body` verbs are one registration, and their operations write
through one `set_body` call."""

import ast
from pathlib import Path

SRC = Path(__file__).parents[2] / "src" / "squads"
CLI = SRC / "_cli"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _calls(tree: ast.AST, name: str) -> int:
    return sum(
        1
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == name
    )


def _body_commands(tree: ast.AST) -> list[ast.Call]:
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and getattr(n.func, "attr", None) == "command"
        and n.args
        and getattr(n.args[0], "value", None) == "body"
    ]


def test_each_roster_group_registers_the_shared_body_verb_and_none_defines_its_own() -> None:
    for module in ("_role.py", "_skill.py", "_operator.py"):
        tree = _tree(CLI / module)
        assert _calls(tree, "register_write_verbs") == 1, module
        assert _calls(tree, "set_body") == 0, module
        assert not _body_commands(tree), module


def test_the_shared_registration_mounts_the_body_verb() -> None:
    helper = next(
        n
        for n in ast.walk(_tree(CLI / "_roster.py"))
        if isinstance(n, ast.FunctionDef) and n.name == "register_write_verbs"
    )
    assert len(_body_commands(helper)) == 1


def test_the_roster_operations_write_a_body_through_set_body_once() -> None:
    assert _calls(_tree(SRC / "_services" / "_roster_ops.py"), "set_body") == 1


def test_no_cli_module_asks_the_view_classification() -> None:
    for path in sorted(CLI.rglob("*.py")):
        assert _calls(ast.parse(path.read_text(encoding="utf-8")), "roster_body_view_name") == 0, (
            path.name
        )
