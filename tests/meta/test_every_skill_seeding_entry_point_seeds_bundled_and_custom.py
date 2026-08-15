"""Repo-hygiene gate: every entry point that writes managed skill bodies must call *both*
``seed_bundled_skills`` and ``seed_custom_skills`` — ``init``, ``adopt`` and ``sync`` alike.

The bug class, twice over. First ``init`` called only ``seed_bundled_skills``, so a squad with
a custom or renamed type sat with an unstamped, un-indexed skill body on disk until someone
happened to run ``sq sync``; ``adopt`` was worse and called neither, leaving an adopted
project's roster incomplete from the very first command. Then the mirror image surfaced on the
third entry point: ``sync`` called only ``seed_custom_skills``, and "custom" is defined by
exclusion from the *bundled* playbook — so a bundled-playbook type whose body file first
appeared after init was claimed by neither vocabulary and stayed bare forever, invisible to
``sq check`` and beyond ``sq repair``'s reach (repair rebuilds the index *from* frontmatter,
and the file has none).

The guard is per-entry-point because the failures were per-entry-point: each of the three
justified its own gap locally, in a docstring that had already gone stale. ``sync`` matters
most of the three going forward — it is what a future release adding a bundled type relies on,
instead of owing a hand-written migration to stamp the new skill.

An AST scan (not a runtime test) so this stays a structural guard independent of any one
override shape; the seeding behaviour itself is proven end to end in
``tests/integration/test_custom_type_skill_generation.py`` and
``tests/integration/test_a_skill_body_appearing_after_init_is_seeded_by_the_next_sync.py``.
"""

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
