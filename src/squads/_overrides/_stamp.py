"""Override-base stamp: read and write the ``<!-- squads:override-base:<version> -->`` marker, the
override file's provenance ("last reconciled against squads v<version>") following the managed-file
stamping convention. It is an HTML comment inert to rendering; the ``squads:`` prefix (not ``sq:``)
marks tooling metadata, not a section delimiter, so ``find_markers`` ignores it. A role TOML
override carries it as a first-line TOML comment, ``# squads:override-base:<squads_version>``.
"""

import re
from pathlib import Path

from squads._aio import atomic_replace_sync
from squads._specload import (
    ROLE_OVERRIDE_MESSAGES,
    TEMPLATE_OVERRIDE_MESSAGES,
    OverrideMessages,
    read_override_text,
)

# Both stamp writers rewrite a whole hand-authored override file, so a kill mid-write must not cost
# it. This module is sync end to end (as `_overrides/_service.py` is), so it uses
# `_aio.atomic_replace_sync` rather than the async `atomic_write_text`, which would force the chain
# async.

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
    text = read_override_text(path, TEMPLATE_OVERRIDE_MESSAGES)
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


def stamp_toml_file(
    path: Path, version: str, messages: OverrideMessages = ROLE_OVERRIDE_MESSAGES
) -> None:
    """Read *path*, update (or insert) the TOML stamp comment, and write it back atomically.
    A file that cannot be read is refused in *messages*' wording."""
    text = read_override_text(path, messages)
    updated = write_toml_stamp(text, version)
    atomic_replace_sync(path, updated)
