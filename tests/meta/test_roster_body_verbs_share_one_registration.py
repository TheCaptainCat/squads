"""The role, skill and operator `body` verbs are one registration that drives `set_body`."""

import ast
from pathlib import Path

CLI = Path(__file__).parents[2] / "src" / "squads" / "_cli"


def _tree(name: str) -> ast.Module:
    return ast.parse((CLI / name).read_text(encoding="utf-8"))


def _calls(tree: ast.AST, name: str) -> int:
    return sum(
        1
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == name
    )


def test_each_roster_group_registers_the_shared_body_verb_and_none_defines_its_own() -> None:
    for module in ("_role.py", "_skill.py", "_operator.py"):
        tree = _tree(module)
        assert _calls(tree, "register_body_verb") == 1, module
        assert _calls(tree, "set_body") == 0, module
        assert not [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and getattr(n.func, "attr", None) == "command"
            and n.args
            and getattr(n.args[0], "value", None) == "body"
        ], module


def test_the_shared_helper_writes_through_set_body_only() -> None:
    helper = next(
        n
        for n in ast.walk(_tree("_common.py"))
        if isinstance(n, ast.FunctionDef) and n.name == "register_body_verb"
    )
    assert _calls(helper, "set_body") == 1
    assert _calls(helper, "roster_body_view_name") == 0
