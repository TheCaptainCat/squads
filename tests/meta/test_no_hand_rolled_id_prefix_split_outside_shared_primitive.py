"""Repo-hygiene gate: an item id's (or a ``PREFIX-<digits>-<slug>`` filename's) prefix must
never be hand-parsed by splitting on a *fixed small hyphen count* — ``"...".split("-", 1)``
or ``.split("-", 2)`` — because the workflow spec's own grammar allows a hyphen inside a
declared ``prefix`` (a path segment is a TOML bare key, ``A-Za-z0-9_-``, so ``"RUN-BOOK"`` is a
legal prefix), and a fixed-count split then breaks inside the prefix itself instead of at its
boundary, corrupting the id/filename it was meant to parse.

The one correct, shared way to recover a prefix from a formatted id is
:func:`squads._models._item.prefix_from_id` (``rpartition`` on the LAST hyphen); recovering a
digit-run/slug from a filename stem whose prefix is already known should ``removeprefix`` that
known prefix and ``partition`` the remainder — never re-derive the prefix by counting hyphens
from the front. This is the same shape as the other ``tests/meta`` guards (the roster-status
literal scan, the mutable-state guard): a cheap, readable AST scan, not a new framework.
"""

import ast
from pathlib import Path
from typing import TypeIs

#: (path, lineno) hits allowlisted — each entry is a KNOWN, pre-existing, separately-tracked
#: instance of this same bug class, not something this gate is meant to silently bless going
#: forward at that location: a fix landing there should remove the entry, not widen it.
#:
#: Empty: ``_models/_item.py``'s ``_slug_from_path`` — the last front-hyphen-count split in the
#: tree — now derives the slug via ``prefix_from_id`` + ``removeprefix``/``partition``, the same
#: shape as every other fixed site, so the guard covers the whole tree with no exceptions.
_ALLOWED_HITS: frozenset[tuple[str, int]] = frozenset()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_hyphen_fixed_split(node: ast.AST) -> TypeIs[ast.Call]:
    """True for a call shaped exactly like ``EXPR.split("-", 1)`` or ``EXPR.split("-", 2)`` —
    the two argument counts every reintroduced instance of this bug has used to grab "the first
    segment" or "the first two segments" of a ``PREFIX-...`` string, assuming the prefix itself
    holds no hyphen."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "split"):
        return False
    if len(node.args) != 2 or node.keywords:
        return False
    sep, count = node.args
    return (
        isinstance(sep, ast.Constant)
        and sep.value == "-"
        and isinstance(count, ast.Constant)
        and count.value in (1, 2)
    )


def _scan(root: Path, allowed: frozenset[tuple[str, int]] = _ALLOWED_HITS) -> list[tuple[str, int]]:
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
            if _is_hyphen_fixed_split(node) and (rel, node.lineno) not in allowed
        )
    return hits


def test_no_hyphen_fixed_split_appears_outside_the_allowlist() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}:{lineno}" for path, lineno in hits)
    assert not hits, (
        'hand-rolled prefix/filename split("-", 1|2) found — a hyphenated prefix corrupts '
        f'this; use prefix_from_id, or removeprefix(known_prefix) + partition("-"):\n{detail}'
    )


def test_the_scan_would_catch_a_planted_split_on_a_fixed_hyphen_count(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('prefix = item_id.split("-", 1)[0]\n', encoding="utf-8")

    assert _scan(tmp_path, allowed=frozenset()) == [("src/squads/_example.py", 1)]


def test_the_scan_would_catch_a_planted_split_two_not_immediately_subscripted(
    tmp_path: Path,
) -> None:
    """The bug shape need not be an immediate ``[...]`` subscript on the same line — the real
    ``_slug_from_path`` instance assigns to a variable first, then subscripts it later."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        'parts = name.split("-", 2)\nslug = parts[2] if len(parts) == 3 else name\n',
        encoding="utf-8",
    )

    assert _scan(tmp_path, allowed=frozenset()) == [("src/squads/_example.py", 1)]


def test_the_scan_never_flags_a_different_split_count_or_separator(tmp_path: Path) -> None:
    """``split("-")`` (no count), ``split("-", 3)``, and ``split("_", 1)`` are not this bug
    shape — only the count-1/count-2, hyphen-separator combination is."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        'a = x.split("-")\nb = x.split("-", 3)\nc = x.split("_", 1)\n',
        encoding="utf-8",
    )

    assert _scan(tmp_path, allowed=frozenset()) == []


def test_every_allowlisted_hit_is_still_produced_by_the_scan_without_it() -> None:
    """A dead allowlist entry is worse than none — it would silently excuse whatever new code
    later lands on that exact (path, line). Removing each entry and re-scanning the real tree
    must reproduce exactly that hit, proving it is still live."""
    root = _repo_root()
    for entry in _ALLOWED_HITS:
        without_this_entry = _ALLOWED_HITS - {entry}
        assert entry in _scan(root, allowed=without_this_entry), (
            f"allowlist entry {entry!r} is dead — the scan no longer produces it; remove it"
        )
