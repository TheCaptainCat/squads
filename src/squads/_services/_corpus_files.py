"""One reading of an item file, shared by the index rebuild and the ``check`` scan.

Both walks open every file the same way. :func:`read_corpus_file` classifies what it finds once
and returns one tagged record per file, so each walk only decides what its own report does
with each tag.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from squads import _aio
from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._models._vocab import prefix_for
from squads._paths import number_for_id
from squads._workflow import ROSTER_SKILL
from squads._workflow._models import WorkflowSpec


def stem_digit_run(md: Path, item_type: str, spec: WorkflowSpec) -> str | None:
    """The zero-padded digit run from *md*'s filename stem alone (e.g. ``"000011"``), ``None`` when
    it does not parse: the fallback for a file whose frontmatter is unreadable, the same parse
    :meth:`MaintenanceMixin.repad` uses. A hyphenated prefix (``"RUN-BOOK"``) is stripped whole. It
    stays a string so callers can also read the padding width.
    """
    prefix = spec.items[item_type].prefix
    digits_slug = md.stem.removeprefix(f"{prefix}-")
    digit_run, _, _slug = digits_slug.partition("-")
    return digit_run if digit_run.isdigit() else None


def seq_from_frontmatter_id(fid: object) -> int | None:
    """The sequence number in a frontmatter ``id:`` value, or ``None`` when it is not a well-formed
    id (a non-string, or a non-integer trailing segment). Both are corrupt file data, and every
    caller is a per-file scan loop that must report the failure per file rather than abort.
    """
    if not isinstance(fid, str):
        return None
    try:
        return number_for_id(fid)
    except SquadsError:
        return None


def missing_dirent_message(md: Path, *, is_symlink: bool) -> str:
    """The one wording for a ``FileNotFoundError`` on a dirent the caller's own glob just saw,
    shared by ``check``, ``repair`` and ``repad``/``renumber``. A broken symlink is a present dirent
    with a missing target, so "No such file or directory" would mislead; only a dirent that vanished
    between scan and read is absent. It names the path once and never interpolates the errno.
    """
    if is_symlink:
        return f"{md} is a broken symlink (its target does not exist)"
    return f"{md} vanished between the directory scan and the read"


def malformed_id_message(fid: object) -> str:
    """The report for a frontmatter ``id:`` that :func:`seq_from_frontmatter_id` could not read. It
    describes the file and claims no repair outcome, because ``repair`` behaves differently across
    the shapes that reach here and ``renumber`` reuses the message and refuses; correcting the line
    is the only remedy it names.
    """
    return (
        f"frontmatter `id` {fid!r} is malformed -- an `id:` must read `<prefix>-<number>`, and "
        "the prefix half of the item's identity is read from this line, with nothing else in the "
        "file supplying it. Correct the `id:` line to match this file's `sequence_id` and its "
        "type's prefix; removing the line is reported too, so it is not a fix."
    )


def is_legacy_skill_body(md: Path, item_type: str, spec: WorkflowSpec) -> bool:
    """True for a slug-named skill body (e.g. ``squads.md``) that never carried a frontmatter
    ``id``, the one shape where a missing ``id`` is not an error. Shared by
    :meth:`CheckMixin._scan_for_check` and :meth:`MaintenanceMixin._rebuild_index_from_disk`. It
    matches any unprefixed skill file, as ``init``'s ``_skip_skill_seed`` yields the same shape, so
    :meth:`MaintenanceMixin.sync` reports bodies left unindexed after seeding.
    """
    if item_type != ROSTER_SKILL:
        return False
    skill_prefix = prefix_for(ROSTER_SKILL, spec) + "-"
    return not md.name.startswith(skill_prefix)


@dataclass(frozen=True)
class CorpusFile:
    """One item file as the corpus walks found it: which type folder and which path."""

    item_type: str
    md: Path


@dataclass(frozen=True)
class Vanished(CorpusFile):
    """Listed by the directory scan, gone by the time it was read."""


@dataclass(frozen=True)
class Unreadable(CorpusFile):
    """Present but its bytes cannot be read or decoded (a broken symlink included)."""

    message: str


@dataclass(frozen=True)
class Unparseable(CorpusFile):
    """Read, but its frontmatter does not parse. ``text`` is what was read."""

    text: str
    message: str


@dataclass(frozen=True)
class MissingId(CorpusFile):
    """Parsed, with no ``id`` in its frontmatter."""

    text: str
    data: dict[str, Any]


@dataclass(frozen=True)
class LegacySkillBody(CorpusFile):
    """A pre-stamping, slug-named skill body: it has never carried an ``id``."""

    text: str
    data: dict[str, Any]


@dataclass(frozen=True)
class Parsed(CorpusFile):
    """Parsed with an ``id``; whether it builds into an item is the caller's to find out."""

    text: str
    data: dict[str, Any]


type Found = Vanished | Unreadable | Unparseable | MissingId | LegacySkillBody | Parsed


async def _read(
    item_type: str, md: Path, read: Callable[[Path], Awaitable[str]]
) -> str | Vanished | Unreadable:
    try:
        return await read(md)
    except FileNotFoundError:
        if not await _aio.path_is_symlink(md):
            return Vanished(item_type, md)
        return Unreadable(item_type, md, missing_dirent_message(md, is_symlink=True))
    except SquadsError as exc:
        return Unreadable(item_type, md, str(exc))


def _tag_by_id(
    item_type: str, md: Path, text: str, data: dict[str, Any], spec: WorkflowSpec
) -> Parsed | LegacySkillBody | MissingId:
    if data.get("id"):
        return Parsed(item_type, md, text, data)
    if is_legacy_skill_body(md, item_type, spec):
        return LegacySkillBody(item_type, md, text, data)
    return MissingId(item_type, md, text, data)


async def read_corpus_file(
    item_type: str,
    md: Path,
    spec: WorkflowSpec,
    read: Callable[[Path], Awaitable[str]] = _aio.read_text,
) -> Found:
    """Open *md* and tag what was found. *read* is how the caller fetches the text."""
    text = await _read(item_type, md, read)
    if not isinstance(text, str):
        return text
    try:
        data = read_frontmatter(text=text, source=str(md))
    except SquadsError as exc:
        return Unparseable(item_type, md, text, str(exc))
    return _tag_by_id(item_type, md, text, data, spec)
