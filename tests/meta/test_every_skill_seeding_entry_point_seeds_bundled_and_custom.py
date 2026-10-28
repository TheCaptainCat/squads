"""Repo-hygiene gate: every entry point that writes managed skill bodies must call *both*
``seed_bundled_skills`` and ``seed_custom_skills`` — ``init``, ``adopt`` and ``sync`` alike."""

import ast
from pathlib import Path

_SEED_CALLS = ("seed_bundled_skills", "seed_custom_skills")

#: Entry point -> the module under ``src/squads`` that defines it. Each of these writes (or
#: drives a backend that writes) managed skill bodies, so each owes the same seeding.
_ENTRY_POINTS = {
    "init": Path("_services") / "_service.py",
    "adopt": Path("_services") / "_service.py",
    "sync": Path("_services") / "_maintenance.py",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _called_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {
        node.func.attr
        for node in ast.walk(func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found — has the module been restructured?")


def test_every_entry_point_seeds_both_bundled_and_custom_skills() -> None:
    for fn_name, rel in _ENTRY_POINTS.items():
        path = _repo_root() / "src" / "squads" / rel
        tree = ast.parse(path.read_text(encoding="utf-8"))
        called = _called_names(_find_function(tree, fn_name))
        missing = [name for name in _SEED_CALLS if name not in called]
        assert not missing, (
            f"{rel}::{fn_name}() doesn't call {missing} — a skill body it writes would sit "
            "unindexed, and neither a repeated sync nor `sq repair` would heal it"
        )
