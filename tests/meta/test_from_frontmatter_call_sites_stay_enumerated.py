"""``Item.from_frontmatter`` takes the active spec's resolved default ref kind as a
**required** keyword (``default_kind``) — the one seam every ``refs`` value passes the fold
through on its way into an ``Item``, so a wrongly-encoded item is never constructed (see the
function's own docstring, and :func:`squads._models._item.fold_legacy_kinds`). That property
holds only because the call site count stays small and known: three, in ``src/squads/`` —
``_itemfile.py`` (the disk side of the frontmatter/index skew guard), and two in
``_services/_maintenance.py`` (``sq repair``'s corpus rebuild, and ``sq check``'s scan).

A **required** keyword makes an omission a ``pyright`` error, not a silent regression — but
that only protects a call site that already exists. Nothing stops a *new* call site from being
added with the keyword correctly supplied, quietly growing the set of places the fold's input
must be reasoned about. This is the anti-drift half: a cheap, readable AST scan (the same shape
as the other ``tests/meta`` guards — the roster-status literal scan, the hyphen-split scan)
that fails the suite the moment a fourth site appears, known or not.
"""

import ast
from pathlib import Path
from typing import TypeIs

#: The three known call sites, transcribed from the code itself — not derived from a live
#: scan, so a call site quietly moving off this list (added elsewhere, removed here) is
#: exactly what this guard exists to catch.
_KNOWN_CALL_SITES: frozenset[tuple[str, str]] = frozenset(
    {
        ("src/squads/_itemfile.py", "frontmatter_skew"),
        ("src/squads/_services/_maintenance.py", "_rebuild_index_from_disk"),
        ("src/squads/_services/_maintenance.py", "_scan_for_check"),
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_item_from_frontmatter_call(node: ast.AST) -> TypeIs[ast.Call]:
    """True only for ``Item.from_frontmatter(...)`` — not ``cls.from_frontmatter`` (the
    definition itself), and not an unrelated model's ``.from_frontmatter`` (``MemoryEntry``,
    ``BoardNotice``), which name the same method on a different class entirely."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "from_frontmatter"
        and isinstance(func.value, ast.Name)
        and func.value.id == "Item"
    )


class _CallSiteVisitor(ast.NodeVisitor):
    """Records ``(function name or "<module>", node)`` for every ``Item.from_frontmatter``
    call, keeping a live stack of enclosing ``def``/``async def`` names so a nested function
    reports its own (innermost) name — never the module or an outer function's."""

    def __init__(self) -> None:
        self._stack: list[str] = []
        self.hits: list[str] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        if _is_item_from_frontmatter_call(node):
            self.hits.append(self._stack[-1] if self._stack else "<module>")
        self.generic_visit(node)


def _scan(root: Path) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    base = root / "src" / "squads"
    if not base.is_dir():
        return hits
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        rel = path.relative_to(root).as_posix()
        visitor = _CallSiteVisitor()
        visitor.visit(tree)
        hits.extend((rel, fn) for fn in visitor.hits)
    return hits


def test_item_from_frontmatter_has_exactly_the_three_known_call_sites() -> None:
    hits = set(_scan(_repo_root()))
    extra = hits - _KNOWN_CALL_SITES
    missing = _KNOWN_CALL_SITES - hits
    assert not extra, f"a NEW Item.from_frontmatter call site appeared, unaccounted for: {extra}"
    assert not missing, f"a known Item.from_frontmatter call site vanished: {missing}"


def test_the_scan_would_catch_a_planted_fourth_call_site(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "from squads._models._item import Item\n\n"
        "def _sneaky(data, path, default_kind):\n"
        "    return Item.from_frontmatter(data, path=path, default_kind=default_kind)\n",
        encoding="utf-8",
    )

    hits = set(_scan(tmp_path))
    assert ("src/squads/_example.py", "_sneaky") in hits


def test_the_scan_never_flags_the_classmethod_definition_or_a_different_models_method(
    tmp_path: Path,
) -> None:
    """``cls.from_frontmatter`` (the definition body) and ``MemoryEntry.from_frontmatter``/
    ``BoardNotice.from_frontmatter`` (a different class, same method name) are not this call
    shape — only a literal ``Item.from_frontmatter(...)`` is."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "class Item:\n"
        "    @classmethod\n"
        "    def from_frontmatter(cls, data, *, path, default_kind):\n"
        "        return cls.model_validate(data)\n\n"
        "def _other(entry_data, slug, body):\n"
        "    return MemoryEntry.from_frontmatter(slug, entry_data, body)\n",
        encoding="utf-8",
    )

    assert _scan(tmp_path) == []
