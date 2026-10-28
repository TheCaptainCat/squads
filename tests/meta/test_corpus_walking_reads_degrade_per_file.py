"""Repo-hygiene gate: a command that walks the whole item corpus must not reach for an item's file
inline — neither the read nor the path resolution that feeds it. Both go to a helper that guards
and reports per file."""

import ast
import inspect
from pathlib import Path

import pytest

from squads._services._collab import CollabMixin


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _calls(fn: ast.AST, name: str) -> bool:
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        attr = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if attr == name:
            return True
    return False


#: Calls that reach for an item's file and can fail on a per-item basis. ``item_file``/
#: ``abspath`` resolve the stored path (and raise for one escaping the squad folder);
#: ``read_text`` reads it. A corpus walk must delegate all of them, not just the read.
_PER_ITEM_FILE_CALLS: frozenset[str] = frozenset({"read_text", "item_file", "abspath"})

#: ``(module, function)`` walks exempt from the rule, each with the reason failing loudly is the
#: right answer there rather than degrading. Function-granular, never module-granular, and the
#: liveness test below fails on a dead entry.
_ALLOWED: dict[tuple[str, str], str] = {}


def _scan(root: Path, allowed: frozenset[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
    """Every ``(path, function name)`` that enumerates the item corpus *and* reaches for an
    item's file directly — the shape whose failure mode is losing the whole answer to one bad
    item."""
    allowed = frozenset(_ALLOWED) if allowed is None else allowed
    hits: list[tuple[str, str]] = []
    base = root / "src" / "squads"
    if not base.is_dir():
        return hits
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        hits.extend(
            (rel, fn.name)
            for fn in ast.walk(tree)
            if isinstance(fn, ast.AsyncFunctionDef | ast.FunctionDef)
            and _calls(fn, "list_items")
            and any(_calls(fn, name) for name in sorted(_PER_ITEM_FILE_CALLS))
            and (rel, fn.name) not in allowed
        )
    return hits


def test_no_corpus_walk_reaches_for_an_item_file_inline() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}: {fn}" for path, fn in hits)
    assert not hits, (
        "a corpus walk resolves or reads an item file inline — one bad item would discard "
        "every result the walk had already accumulated. Delegate the whole operation, path "
        f"resolution included, to a helper that reports the skipped item:\n{detail}"
    )


def test_every_exempt_walk_is_still_produced_by_the_scan_without_it() -> None:
    """A dead exemption silently blesses whatever later takes that name."""
    root = _repo_root()
    for entry in _ALLOWED:
        without = frozenset(_ALLOWED) - {entry}
        assert entry in _scan(root, allowed=without), (
            f"exemption {entry!r} is dead — the scan no longer produces it; remove it"
        )


def test_the_scan_would_catch_a_planted_inline_corpus_read(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "async def walk(self):\n"
        "    out = []\n"
        "    for item in await self.list_items():\n"
        "        out.append(await _aio.read_text(item.path))\n"
        "    return out\n",
        encoding="utf-8",
    )
    assert _scan(tmp_path, allowed=frozenset()) == [("src/squads/_example.py", "walk")]


def test_the_scan_would_catch_a_guarded_read_fed_by_an_inline_path_resolution(
    tmp_path: Path,
) -> None:
    """The shape that defeated the first version of this gate: the read *is* delegated."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "async def walk(self):\n"
        "    out, skipped = [], []\n"
        "    for item in await self.list_items():\n"
        "        text = await _read_or_report(item_file(self.paths, item), skipped)\n"
        "        if text is not None:\n"
        "            out.append(text)\n"
        "    return out, skipped\n",
        encoding="utf-8",
    )
    assert _scan(tmp_path, allowed=frozenset()) == [("src/squads/_example.py", "walk")]


def test_the_scan_accepts_a_corpus_walk_that_delegates_the_read(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "async def walk(self):\n"
        "    out, skipped = [], []\n"
        "    for item in await self.list_items():\n"
        "        text = await _read_or_report(self.paths, item, skipped)\n"
        "        if text is not None:\n"
        "            out.append(text)\n"
        "    return out, skipped\n",
        encoding="utf-8",
    )
    assert _scan(tmp_path, allowed=frozenset()) == []


def test_the_scan_ignores_a_read_with_no_corpus_walk(tmp_path: Path) -> None:
    """A single-file read has no accumulated answer to lose."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text("async def one(path):\n    return await _aio.read_text(path)\n", "utf-8")
    assert _scan(tmp_path, allowed=frozenset()) == []


@pytest.mark.parametrize("name", ["search", "inbox"])
def test_each_corpus_walking_command_returns_a_skipped_file_channel(name: str) -> None:
    """The behavioural half: a guard that catches and says nothing is no better than no guard."""
    annotation = str(inspect.signature(getattr(CollabMixin, name)).return_annotation)
    assert "UnreadableItems" in annotation, f"{name} returns {annotation!r}"
