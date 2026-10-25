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
    """The zero-padded digit run recovered from *md*'s **filename** stem alone (e.g.
    ``"000011"``), ``None`` when even that does not parse.

    The fallback source for a file whose frontmatter cannot be read at all — the same
    prefix-stripped digit-run parse :meth:`MaintenanceMixin.repad` already relies on for the
    identical reason (a filename is a weaker source of truth than frontmatter, but it is the
    only one left once frontmatter is unreadable). A hyphenated prefix (e.g. ``"RUN-BOOK"``) is
    stripped whole rather than split on the stem's first hyphen. Kept as the raw digit-run
    *string* (not just the parsed int) so a caller that also needs the filename's padding
    width — :meth:`MaintenanceMixin._rebuild_index_from_disk`'s counter/padding floor — never
    has to re-parse the stem a second time to get it.
    """
    prefix = spec.items[item_type].prefix
    digits_slug = md.stem.removeprefix(f"{prefix}-")
    digit_run, _, _slug = digits_slug.partition("-")
    return digit_run if digit_run.isdigit() else None


def seq_from_frontmatter_id(fid: object) -> int | None:
    """The sequence number carried by a frontmatter ``id:`` value, or ``None`` when that value
    is not a well-formed id at all.

    Two shapes give ``None``: a non-string (``id: 5``, ``id: [a, b]`` — where ``number_for_id``
    raises ``AttributeError``) and a trailing segment that is not an integer (``id: TASK-abc``
    — where it raises ``InvalidIdError``). Both are corrupt *file data*, and every call site is
    inside a per-file scan loop that must never abort the whole scan for one bad file, so the
    parse is funnelled through here and the failure reported per file like any other defect.
    """
    if not isinstance(fid, str):
        return None
    try:
        return number_for_id(fid)
    except SquadsError:
        return None


def missing_dirent_message(md: Path, *, is_symlink: bool) -> str:
    """The one wording for a ``FileNotFoundError`` raised on a dirent the caller's own glob just
    saw — shared by every command that can hit one (``check``, ``repair``, ``repad``/``renumber``)
    so the same dirent cannot be given two different diagnoses depending on which command found
    it.

    The distinction is the whole point of the ``is_symlink`` test each caller performs: a broken
    symlink is a **present** dirent whose *target* is missing, so "No such file or directory" —
    what the raw ``OSError`` says —
    sends an operator looking for a file that is sitting right there. Only a dirent that genuinely
    vanished between the scan and the read is absent.

    Names the path exactly once and never interpolates the errno: the raw ``str(exc)`` repeats the
    path a second time inside its own text, which is how the two-paths-in-one-message shape got in.
    """
    if is_symlink:
        return f"{md} is a broken symlink (its target does not exist)"
    return f"{md} vanished between the directory scan and the read"


def malformed_id_message(fid: object) -> str:
    """The report for a frontmatter ``id:`` that :func:`seq_from_frontmatter_id` could not read.

    Describes the **file**, and deliberately says nothing about what another command will then do
    with it. Two reasons, both load-bearing.

    *No repair outcome is claimed.* ``repair``'s behaviour is not one behaviour across the shapes
    that reach here, all driven: ``id: TASK-abc`` rebuilds the entry cleanly (prefix from the id's
    own prefix segment, number from ``sequence_id``); a non-string ``id: 5`` is refused by the load
    boundary, so ``repair`` reports the file and leaves the previous index entry in place; and a
    hyphen-less ``id: TASK`` rebuilds an entry whose id degrades to the ``UNRESOLVED`` sentinel.
    No single sentence is true of all three — and this same message is reused verbatim by
    ``renumber``, which refuses outright, where any repair claim is doubly wrong. So each command
    reports its own outcome and this states only what is wrong with the line.

    *The remedy is the one that works.* The wording this replaced also offered "or delete it".
    Driven: a file with no ``id:`` at all is reported by ``check`` ("file has no `id` in
    frontmatter") and third-stated by ``repair``, so deleting the line swaps one error for
    another. Correcting the line is the only action that clears it, and the message says so
    rather than letting an operator discover it the slow way.
    """
    return (
        f"frontmatter `id` {fid!r} is malformed -- an `id:` must read `<PREFIX>-<number>`, and "
        "the prefix half of the item's identity is read from this line, with nothing else in the "
        "file supplying it. Correct the `id:` line to match this file's `sequence_id` and its "
        "type's prefix; removing the line is reported too, so it is not a fix."
    )


def is_legacy_skill_body(md: Path, item_type: str, spec: WorkflowSpec) -> bool:
    """True for a pre-stamping, slug-named skill body file (e.g. ``squads.md``) that has
    legitimately never carried a frontmatter ``id`` — the one shape where a missing ``id`` is
    not an error, since these files pre-date the id-stamping migration entirely (see
    :meth:`ServiceCore._iter_item_files`). An ID-prefixed skill file (``SKILL-*.md``)
    missing its ``id`` is a real error, same as any other type — only the legacy, unstamped
    shape is exempt. Shared by both :meth:`CheckMixin._scan_for_check` and
    :meth:`MaintenanceMixin._rebuild_index_from_disk`'s "no id" branch so the exemption can
    never drift between the two.

    **This is wider than "pre-migration", and deliberately stays that way.** It matches any
    skill file whose name lacks the type prefix, whenever it was written — including an
    unstamped body produced *today* by a seeding gap, which is a real defect (a generated,
    pointer-referenced file no ``SKILL`` item indexes) wearing the same shape. Narrowing it
    was tried and is not available: the two states are indistinguishable on disk *and* in the
    index, because ``init``'s internal ``_skip_skill_seed`` hook manufactures exactly the
    defect shape on purpose — bodies written, ids deliberately not stamped, to hold the global
    counter still. Every discriminator that reports the defect also reports that hook's output.

    So the report for an unindexed skill body lives where the file is *produced* rather than
    where it is later found: :meth:`MaintenanceMixin.sync` seeds every managed skill slug and
    then reports, by name, any slug-named body still left unindexed
    (:meth:`MaintenanceMixin._unindexed_skill_bodies`). That covers the variant this exemption
    cannot — a body whose slug no seeding vocabulary claims — at the one surface that knows it
    just wrote the file, and leaves check free to keep tolerating a corpus that has genuinely
    never been stamped.
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
