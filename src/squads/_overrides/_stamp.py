"""Override-base stamp: read and write the ``<!-- squads:override-base:<version> -->`` marker.

The stamp follows the existing managed-file stamping convention (see the ``squads:start``/
``squads:end`` managed-region markers in CLAUDE.md/AGENTS.md).  It is a plain HTML comment,
inert to rendering.  The stamp is the override file's provenance marker: "last reconciled
against squads v<version>".

Stamp format::

    <!-- squads:override-base:<squads_version> -->

The ``squads:`` prefix (not ``sq:``) is intentional: this marker is tooling metadata, not
a document-section delimiter.  ``find_markers`` (strict ``sq:``-only regex) correctly ignores it.

Role TOML overrides also carry a stamp, embedded as a TOML comment on the first line::

    # squads:override-base:0.3.0
"""

import re
from pathlib import Path

from squads._aio import atomic_replace_sync

# Both stamp writers below rewrite a *whole* override file the adopter hand-authored — a
# template or a role TOML — so a kill mid-write must not cost that content. This module is sync
# end to end (called from `_overrides/_service.py`, itself sync), so it reaches for
# `_aio.atomic_replace_sync` directly rather than the async `atomic_write_text` wrapper, which
# would force this whole call chain async for no benefit.

# ─── Template-file stamp (HTML comment) ────────────────────────────────────────

_TEMPLATE_STAMP_RE = re.compile(r"<!--\s*squads:override-base:([A-Za-z0-9._-]+)\s*-->")
_TEMPLATE_STAMP_TPL = "<!-- squads:override-base:{version} -->"


def read_template_stamp(text: str) -> str | None:
    """Return the version string from the ``<!-- squads:override-base:… -->`` comment, or None."""
    m = _TEMPLATE_STAMP_RE.search(text)
    return m.group(1) if m else None


def write_template_stamp(text: str, version: str) -> str:
    """Insert or replace the stamp in *text*, returning the updated content.

    Inserts the stamp as the **first line** of the file when absent; replaces an
    existing stamp in-place when present so the file's line structure stays intact.
    """
    new_stamp = _TEMPLATE_STAMP_TPL.format(version=version)
    if _TEMPLATE_STAMP_RE.search(text):
        return _TEMPLATE_STAMP_RE.sub(new_stamp, text, count=1)
    # No existing stamp — prepend as the first line.
    return new_stamp + "\n" + text


def stamp_template_file(path: Path, version: str) -> None:
    """Read *path*, update (or insert) the override-base stamp, and write it back atomically."""
    text = path.read_text(encoding="utf-8")
    updated = write_template_stamp(text, version)
    atomic_replace_sync(path, updated)


# ─── Role TOML stamp (TOML comment) ────────────────────────────────────────────

_TOML_STAMP_RE = re.compile(r"^#\s*squads:override-base:([A-Za-z0-9._-]+)\s*$", re.MULTILINE)
_TOML_STAMP_TPL = "# squads:override-base:{version}"


def read_toml_stamp(text: str) -> str | None:
    """Return the version from the ``# squads:override-base:…`` TOML comment, or None."""
    m = _TOML_STAMP_RE.search(text)
    return m.group(1) if m else None


def write_toml_stamp(text: str, version: str) -> str:
    """Insert or replace the TOML stamp comment, returning the updated content."""
    new_stamp = _TOML_STAMP_TPL.format(version=version)
    if _TOML_STAMP_RE.search(text):
        return _TOML_STAMP_RE.sub(new_stamp, text, count=1)
    return new_stamp + "\n" + text


def stamp_toml_file(path: Path, version: str) -> None:
    """Read *path*, update (or insert) the TOML stamp comment, and write it back atomically."""
    text = path.read_text(encoding="utf-8")
    updated = write_toml_stamp(text, version)
    atomic_replace_sync(path, updated)
