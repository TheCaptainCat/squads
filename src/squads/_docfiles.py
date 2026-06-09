"""Locate and read the bundled project docs for the ``sq docs`` command.

Docs are authored at the repo-root ``docs/`` and shipped into the wheel as ``squads/_docs/``
(hatch ``force-include`` — see ``pyproject.toml``). At runtime we prefer that packaged copy and
fall back to the repo-root ``docs/`` for editable/dev installs, where force-include does not apply.
This is a leaf module: it depends only on ``_errors`` to keep the import graph acyclic.
"""

from pathlib import Path

from squads._errors import SquadsError

_HERE = Path(__file__).resolve()


def _docs_root() -> Path:
    """The directory holding the doc markdown, packaged or (in dev) at the repo root."""
    packaged = _HERE.parent / "_docs"  # squads/_docs in an installed wheel
    if packaged.is_dir():
        return packaged
    return _HERE.parents[2] / "docs"  # editable: src/squads/_docfiles.py → repo root /docs


def _title(md: Path) -> str:
    """The doc's first ``# `` heading, or its stem if it has none."""
    for line in md.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return md.stem


def available() -> list[tuple[str, str]]:
    """``(stem, title)`` for every bundled doc, sorted by stem."""
    return [(md.stem, _title(md)) for md in sorted(_docs_root().glob("*.md"))]


def read(name: str) -> str:
    """Return a doc's markdown by stem (case-insensitive, optional ``.md``).

    Raises ``SquadsError`` listing the available names when ``name`` matches nothing.
    """
    target = name.strip().removesuffix(".md").lower()
    for md in sorted(_docs_root().glob("*.md")):
        if md.stem.lower() == target:
            return md.read_text(encoding="utf-8")
    names = ", ".join(stem for stem, _ in available())
    raise SquadsError(f"unknown doc {name!r} (one of: {names})")
