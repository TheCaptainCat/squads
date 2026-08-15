"""Repo-hygiene gate: ``squads._clock`` is the only module under ``src/squads`` that reads
wall-clock time.

Everything else asks it, so a forged ``--at`` run and a frozen-time test both see the instant
they set. A second, unhooked source of "now" is invisible rather than wrong-looking: it returns
a perfectly plausible timestamp, so nothing fails loudly — the override is simply ignored at
whichever seam still reads it.

The instance that motivated this guard was worse than a wrong timestamp. A frontmatter
timestamp the file did not carry defaulted to a direct ``datetime.now(UTC)``, so every load of
that file produced a *different* value. The skew check round-trips both of its inputs through
that same loader, so the on-disk side could never equal the index side, and the item was
refused for good — with a "run ``sq repair``" pointer repair cannot honour, because it rebuilds
the index from markdown and never rewrites markdown. Non-determinism at a load boundary is the
sharp edge here, not the offset.

The scan is deliberately blunt: any direct wall-clock call under ``src/squads``, whatever it is
for. The clock module itself is the one exempt implementation.
"""

import ast
from pathlib import Path
from typing import TypeIs

from squads import _clock as clock

#: The module that is allowed to read wall-clock time, relative to the repo root.
_CLOCK_MODULE = "src/squads/_clock.py"

#: Attribute call shapes that read wall-clock time: ``(object, attribute)``. Matched on the
#: trailing attribute access, so both ``datetime.now(...)`` and ``dt.datetime.now(...)`` hit.
_WALL_CLOCK_CALLS: frozenset[tuple[str, str]] = frozenset(
    {
        ("datetime", "now"),
        ("datetime", "utcnow"),
        ("datetime", "today"),
        ("date", "today"),
        ("time", "time"),
        ("time", "time_ns"),
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_wall_clock_call(node: ast.AST) -> TypeIs[ast.Call]:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    owner = func.value
    name = owner.attr if isinstance(owner, ast.Attribute) else getattr(owner, "id", None)
    return (name, func.attr) in _WALL_CLOCK_CALLS


def _scan(
    root: Path, allowed: frozenset[str] = frozenset({_CLOCK_MODULE})
) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    base = root / "src" / "squads"
    if not base.is_dir():
        return hits
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if rel in allowed:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        hits.extend((rel, node.lineno) for node in ast.walk(tree) if _is_wall_clock_call(node))
    return hits


def test_no_module_reads_wall_clock_time_outside_the_clock_module() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}:{lineno}" for path, lineno in hits)
    assert not hits, (
        "wall-clock read outside squads._clock — use clock.now() so a forged --at run and a "
        f"frozen-time test both see the instant they set:\n{detail}"
    )


def test_the_scan_would_catch_every_planted_wall_clock_shape(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "a = datetime.now(UTC)\nb = dt.datetime.utcnow()\nc = date.today()\nd = time.time()\n",
        encoding="utf-8",
    )
    assert [line for _, line in _scan(tmp_path, allowed=frozenset())] == [1, 2, 3, 4]


def test_the_scan_never_flags_the_sanctioned_seam_or_a_lookalike(tmp_path: Path) -> None:
    """``clock.now()``, a parse of a *stored* timestamp, and an unrelated ``.now`` attribute
    are all fine — only a direct wall-clock read is the bug shape."""
    planted = tmp_path / "src" / "façade.py"
    planted.parent.mkdir(parents=True)
    (tmp_path / "src" / "squads").mkdir()
    example = tmp_path / "src" / "squads" / "_example.py"
    example.write_text(
        "a = clock.now()\n"
        "b = datetime.fromisoformat(raw)\n"
        "c = clock.parse_iso(raw)\n"
        "d = self.now()\n",
        encoding="utf-8",
    )
    assert _scan(tmp_path, allowed=frozenset()) == []


def test_the_sanctioned_seam_actually_honours_an_override() -> None:
    """A scan alone would pass on a clock that ignores its own override, which would make every
    call site it forced traffic through equally unhooked."""
    from datetime import UTC, datetime

    forged = datetime(2011, 11, 11, 11, 11, 11, tzinfo=UTC)
    clock.set_now(forged)
    assert clock.now() == forged
