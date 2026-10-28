"""Repo-hygiene gate closing the same class of correspondence
``test_validator_context_requirements_match_what_each_member_reads.py`` closes for declared
context — applied here to the level/floor declaration table (``DEFAULT_VALIDATOR_LEVEL``,
``VALIDATOR_LEVEL_FLOOR``) each catalog member's default and floor live in."""

import ast
from pathlib import Path
from typing import Any, cast

from squads._services._validators import CATALOG
from squads._workflow._validator_names import VALIDATOR_LEVELS

_SOURCE = ("src", "squads", "_services", "_validators.py")


def _module_ast() -> ast.Module:
    path = Path(__file__).resolve().parents[2].joinpath(*_SOURCE)
    return ast.parse(path.read_text(encoding="utf-8"))


def _member_function_names() -> dict[str, str]:
    """Catalog name -> the name of the function registered under it (mirrors the context-scan
    test's own helper — ``Validator`` is a call-only Protocol, so a function's own ``__name__``
    is not part of the declared interface)."""
    return {name: cast(Any, fn).__name__ for name, fn in CATALOG.items()}


def _level_literal(call: ast.Call) -> str | None:
    """The literal string a ``CheckIssue(...)`` call passes as its ``level`` — positionally
    (arg 0) or by keyword — or ``None`` when that argument is not a string constant at all
    (a name, an attribute access, a call result: exactly what a resolved value looks like)."""
    node: ast.expr | None = call.args[0] if call.args else None
    if node is None:
        node = next((kw.value for kw in call.keywords if kw.arg == "level"), None)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _hardcoded_levels_by_function(tree: ast.Module) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        hits = [
            literal
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "CheckIssue"
            for literal in (_level_literal(call),)
            if literal is not None
        ]
        if hits:
            out[node.name] = hits
    return out


def test_no_catalog_member_passes_a_literal_level_string_to_checkissue() -> None:
    functions = _member_function_names()
    assert len(functions) == len(CATALOG) > 1, "the catalog resolved to too few members to scan"

    hardcoded = _hardcoded_levels_by_function(_module_ast())
    offenders = {
        fn_name: hardcoded[fn_name] for fn_name in functions.values() if fn_name in hardcoded
    }
    assert not offenders, (
        f"catalog member(s) pass a literal level string to CheckIssue instead of a value "
        f"resolved from DEFAULT_VALIDATOR_LEVEL/a type's own override: {offenders}. Read the "
        "member's effective level (see _resolved_level) and pass that, not a literal."
    )


def test_default_validator_level_values_are_all_declared_levels() -> None:
    from squads._workflow._validator_names import DEFAULT_VALIDATOR_LEVEL

    assert set(DEFAULT_VALIDATOR_LEVEL.values()) <= VALIDATOR_LEVELS


def test_validator_level_floor_values_are_all_declared_levels() -> None:
    from squads._workflow._validator_names import VALIDATOR_LEVEL_FLOOR

    assert set(VALIDATOR_LEVEL_FLOOR.values()) <= VALIDATOR_LEVELS
