"""Repo-hygiene gate: the dedicated ``priority`` kwarg on item create/update must never reach
the model as a raw, unchecked passthrough — it has to go through the same declared-field gate
as the generic ``--set priority=<code>`` door (:meth:`ServiceCore._check_priority`, itself built
from :meth:`ServiceCore._badge_field`/:meth:`ServiceCore._parse_badge_code`).

The bug this guards against had exactly two shapes, both a bare, unvalidated ``priority`` local
reaching the model unchanged:

- ``Item(..., priority=priority, ...)`` — the model constructor called with the raw kwarg,
  in :meth:`ServiceCore._create_model`.
- ``item.priority = priority`` — a direct attribute assignment, in
  :meth:`~squads._services._items.ItemsMixin._update_model`.

A type declaring no ``priority`` field (``fields = []``) still had its value written and
rendered as though the type declared it, because the field-eligibility gate only ran on the
sibling ``--set`` door. This is the same shape as the other ``tests/meta`` guards: a cheap,
readable AST scan, not a new framework. It does not forbid the *thin passthrough* between
``create``/``update`` and their `_core`/`_model` halves (``priority=priority`` as a kwarg to
those helper calls is fine and expected) — only the two shapes above, where the value lands
directly on the model with no gate in between.
"""

import ast
from pathlib import Path
from typing import TypeIs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_raw_priority_kwarg_to_item_ctor(node: ast.AST) -> TypeIs[ast.Call]:
    """``Item(..., priority=priority, ...)`` — the model constructor invoked with the bare,
    same-named local, meaning nothing validated it first."""
    if not (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Item"
    ):
        return False
    return any(
        kw.arg == "priority" and isinstance(kw.value, ast.Name) and kw.value.id == "priority"
        for kw in node.keywords
    )


def _is_raw_priority_attr_assign(node: ast.AST) -> TypeIs[ast.Assign]:
    """``item.priority = priority`` (or any object's ``.priority`` attribute) — a direct
    assignment of the bare, same-named local, bypassing the gate entirely."""
    if not isinstance(node, ast.Assign):
        return False
    if not (isinstance(node.value, ast.Name) and node.value.id == "priority"):
        return False
    return any(isinstance(t, ast.Attribute) and t.attr == "priority" for t in node.targets)


def _scan(root: Path) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    base = root / "src" / "squads"
    if not base.is_dir():
        return hits
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        rel = path.relative_to(root).as_posix()
        hits.extend(
            (rel, node.lineno)
            for node in ast.walk(tree)
            if _is_raw_priority_kwarg_to_item_ctor(node) or _is_raw_priority_attr_assign(node)
        )
    return hits


def test_no_raw_priority_passthrough_reaches_the_model() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}:{lineno}" for path, lineno in hits)
    assert not hits, (
        "a raw `priority` kwarg/attribute assignment bypasses the declared-field gate — route it "
        f"through ServiceCore._check_priority instead:\n{detail}"
    )


def test_the_scan_would_catch_a_planted_item_ctor_passthrough(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text("item = Item(priority=priority)\n", encoding="utf-8")

    assert _scan(tmp_path) == [("src/squads/_example.py", 1)]


def test_the_scan_would_catch_a_planted_attribute_assign_passthrough(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text("item.priority = priority\n", encoding="utf-8")

    assert _scan(tmp_path) == [("src/squads/_example.py", 1)]


def test_the_scan_never_flags_a_gated_assignment_or_a_passthrough_kwarg(tmp_path: Path) -> None:
    """A validated value under a different name (``checked_priority``), and a kwarg-name
    passthrough between wrapper and core (not into ``Item(...)`` itself), are both fine."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "item.priority = checked_priority\n"
        "item2 = Item(priority=checked_priority)\n"
        "await self._create_core(db, priority=priority)\n",
        encoding="utf-8",
    )

    assert _scan(tmp_path) == []
