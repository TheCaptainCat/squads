"""One definition of which item file carries which id and slug, and the detector built on it,
shared by ``check``, ``repair``, the write guard and the managed-skill restamp."""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from squads import _aio
from squads import _sections as sections
from squads._errors import SquadsError
from squads._itemfile import write_text
from squads._models._item import DISPLAY_ID_PADDING, format_item_id, prefix_from_id
from squads._paths import number_for_id

#: What a report line says to do about a duplicated id; no verb can choose between the copies.
DUPLICATE_ID_REMEDY = (
    "merge the content you want into one file, delete the other by hand, then run `sq repair`"
)


def duplicate_id_remedy(then: str) -> str:
    """:data:`DUPLICATE_ID_REMEDY` ending with the command *then* (``sq adopt`` where there is no
    configuration for ``sq repair`` to read)."""
    return DUPLICATE_ID_REMEDY.removesuffix("`sq repair`") + f"`{then}`"


def normalized_id(fid: object) -> str | None:
    """*fid* spelled one way whatever its padding, or ``None`` when it is not a well-formed id."""
    if not isinstance(fid, str):
        return None
    try:
        return format_item_id(prefix_from_id(fid), number_for_id(fid), DISPLAY_ID_PADDING)
    except SquadsError:
        return None


def file_slug(md: Path, fm: dict[str, Any], prefix: str) -> str:
    """A file's slug: the frontmatter ``slug`` (or, in a file not yet migrated, the one under
    its ``extra`` block), else the slug segment of its name. The only definition; every caller
    asks here."""
    extra = fm.get("extra")
    for candidate in (
        fm.get("slug"),
        cast("dict[str, Any]", extra).get("slug") if isinstance(extra, dict) else None,
    ):
        if isinstance(candidate, str) and candidate:
            return candidate
    return md.stem.removeprefix(f"{prefix}-").partition("-")[2]


def duplicate_groups(pairs: Iterable[tuple[object, Path]]) -> dict[str, list[Path]]:
    """Every id carried by more than one file, mapped to those files in path order."""
    groups: dict[str, list[Path]] = {}
    for fid, md in pairs:
        key = normalized_id(fid)
        if key is not None:
            groups.setdefault(key, []).append(md)
    return {key: sorted(files) for key, files in groups.items() if len(files) > 1}


#: What a report line says to do about one number carried by two different ids.
SHARED_NUMBER_REMEDY = "run `sq repair --renumber` to give one of them a new number"


def shared_number_groups(pairs: Iterable[tuple[object, Path]]) -> dict[int, list[Path]]:
    """Every sequence number carried under more than one distinct id (a task and a bug both
    numbered 21), mapped to those files in path order. A repeated identical id is the business
    of :func:`duplicate_groups`."""
    ids_by_number: dict[int, set[str]] = {}
    files_by_number: dict[int, list[Path]] = {}
    for fid, md in pairs:
        key = normalized_id(fid)
        if key is not None:
            number = number_for_id(key)
            ids_by_number.setdefault(number, set()).add(key)
            files_by_number.setdefault(number, []).append(md)
    return {
        number: sorted(files)
        for number, files in files_by_number.items()
        if len(ids_by_number[number]) > 1
    }


_NAME_NUMBER = re.compile(r"^.+?-(\d+)(?:-|\.md$)")


def name_number(name: str) -> int | None:
    """The sequence number a file name carries (``<PREFIX>-000022-alpha.md`` -> 22), whatever its
    prefix, or ``None`` when the name carries none."""
    m = _NAME_NUMBER.match(name)
    return int(m[1]) if m else None


async def read_id(md: Path) -> str | None:
    """The normalized id in *md*'s frontmatter, or ``None`` when it has none or is unreadable."""
    try:
        fid = sections.split_frontmatter(await _aio.read_text(md))[0].get("id")
    except (OSError, SquadsError):  # fmt: skip
        return None
    return normalized_id(fid)


async def groups_among(files: Iterable[Path]) -> dict[str, list[Path]]:
    """The duplicate groups among *files*, reading every one of them."""
    return duplicate_groups(await _read_pairs(files))


async def _read_pairs(files: Iterable[Path]) -> list[tuple[object, Path]]:
    """``(normalized id, file)`` for each of *files* that still reads and carries an id."""
    pairs: list[tuple[object, Path]] = []
    for md in sorted(files):
        fid = await read_id(md)
        if fid is not None:
            pairs.append((fid, md))
    return pairs


def _candidates(files: Iterable[Path], number: int, listing: Iterable[Path]) -> set[Path]:
    """*files* plus every listed file whose name carries *number*: a copy renamed since the scan
    is found again by its number, without reading the rest of the corpus."""
    return set(files) | {md for md in listing if name_number(md.name) == number}


async def confirmed_groups(
    groups: dict[str, list[Path]], listing: Iterable[Path]
) -> dict[str, list[Path]]:
    """The duplicate groups that still hold when read again against a fresh *listing*: a file
    renamed or removed since the scan drops out, and a renamed copy is found under its new
    name, so one file seen under two names is not reported as two."""
    listing = list(listing)
    confirmed: dict[str, list[Path]] = {}
    for key, files in groups.items():
        again = duplicate_groups(await _read_pairs(_candidates(files, number_for_id(key), listing)))
        if key in again:
            confirmed[key] = again[key]
    return confirmed


async def confirmed_shared_numbers(
    groups: dict[int, list[Path]], listing: Iterable[Path]
) -> dict[int, list[Path]]:
    """The shared-number groups that still hold when read again against a fresh *listing*,
    regrouped by number from what each candidate file carries now."""
    listing = list(listing)
    confirmed: dict[int, list[Path]] = {}
    for number, files in groups.items():
        again = shared_number_groups(await _read_pairs(_candidates(files, number, listing)))
        if number in again:
            confirmed[number] = again[number]
    return confirmed


@dataclass
class CarrierLog:
    """The ids a scan met while it read the item files anyway, so detecting duplicates costs
    no second read of those files."""

    pairs: list[tuple[object, Path]] = field(default_factory=list[tuple[object, Path]])
    seen: set[Path] = field(default_factory=set[Path])

    def record(self, md: Path, fid: Any) -> Any:
        """Note that *md* was read and carries *fid* (if any); returns *fid*."""
        self.seen.add(md)
        if fid:
            self.pairs.append((fid, md))
        return fid


@dataclass(frozen=True)
class MovedFile:
    """One file given a new number: its id before and after, and its path before and after,
    relative to the squad folder."""

    old: str
    new: str
    file: str
    target: str


@dataclass(frozen=True)
class LeftReference:
    """One reference to an old id that a renumber left unchanged: the id, the file holding it,
    where in that file, and the text."""

    id: str
    file: str
    where: str
    text: str


@dataclass
class SameIdRenumber:
    """What ``repair --renumber`` did about ids carried by more than one file."""

    moved: list[MovedFile] = field(default_factory=list[MovedFile])
    ids: list[str] = field(default_factory=list[str])


def _rel(squad_dir: Path, md: Path) -> str:
    return md.relative_to(squad_dir).as_posix()


def _frontmatter_hits(value: Any, pattern: re.Pattern[str], path: str) -> list[tuple[str, str]]:
    """Every string under *value* that names the id, with the key path it sits under."""
    if isinstance(value, str):
        return [(path, value)] if pattern.search(value) else []
    hits: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, inner in cast("dict[str, Any]", value).items():
            hits += _frontmatter_hits(inner, pattern, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for inner in cast("list[Any]", value):
            hits += _frontmatter_hits(inner, pattern, path)
    return hits


def _text_hits(text: str, pattern: re.Pattern[str], first_line: int) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    in_discussion = False
    for offset, line in enumerate(text.splitlines()):
        if line.strip().endswith(":discussion:end -->"):
            in_discussion = False
        elif line.strip().endswith(":discussion -->") or line.strip() == "<!-- sq:discussion -->":
            in_discussion = True
        elif pattern.search(line):
            where = f"{'comment' if in_discussion else 'body'}:{first_line + offset}"
            hits.append((where, line.strip()))
    return hits


async def references_to(
    squad_dir: Path, item_files: list[Path], old_id: str
) -> list[tuple[str, str, str]]:
    """``(file, where, text)`` for every reference to *old_id* in any item file's frontmatter
    (outside ``id``/``sequence_id``), body prose or discussion."""
    prefix, _, digits = old_id.rpartition("-")
    pattern = re.compile(rf"\b{re.escape(prefix)}-0*{int(digits)}\b")
    found: list[tuple[str, str, str]] = []
    for md in item_files:
        try:
            text = await _aio.read_text(md)
            fm, body = sections.split_frontmatter(text)
        except (OSError, SquadsError):  # fmt: skip
            continue
        rel = _rel(squad_dir, md)
        for key, value in fm.items():
            if key not in ("id", "sequence_id"):
                found += [(rel, w, t) for w, t in _frontmatter_hits(value, pattern, str(key))]
        first_line = text[: len(text) - len(body)].count("\n") + 1
        found += [(rel, w, t) for w, t in _text_hits(body, pattern, first_line)]
    return found


@dataclass(frozen=True)
class RenumberScope:
    """Where the same-id renumber may act: the folder each prefix is scanned from, the file the
    previous index points at for each id, and the live file listing."""

    folder_for_prefix: dict[str, Path]
    indexed_paths: dict[str, Path]
    list_files: Callable[[], list[Path]]
    rehint: Callable[[str, dict[str, Any], Path, str], str]


def _readable_by_index_scan(md: Path, prefix: str, scope: RenumberScope) -> bool:
    """True when the index scan would read *md*: it sits in its id prefix's own type folder and
    is named for that prefix."""
    return scope.folder_for_prefix.get(prefix) == md.parent and md.name.startswith(f"{prefix}-")


def _stem_key(squad_dir: Path, md: Path) -> bytes:
    return _rel(squad_dir, md.with_suffix("")).encode()


async def _group_slugs(files: list[Path], prefix: str) -> list[str]:
    slugs: list[str] = []
    for md in files:
        try:
            fm = sections.split_frontmatter(await _aio.read_text(md))[0]
        except (OSError, SquadsError):  # fmt: skip
            fm = {}
        slugs.append(file_slug(md, fm, prefix))
    return slugs


async def renumberable(files: list[Path], prefix: str, scope: RenumberScope) -> bool:
    """A group is renumbered only when every file is one the index scan reads, no two share a
    slug, and the files are not all byte-identical (an identical set is a copy, not a merge)."""
    if not all(_readable_by_index_scan(md, prefix, scope) for md in files):
        return False
    slugs = await _group_slugs(files, prefix)
    if len(set(slugs)) < len(slugs):
        return False
    return len({await _aio.read_bytes(md) for md in files}) > 1


async def _renumber_files(
    squad_dir: Path,
    ordered: list[Path],
    key: str,
    padding: int,
    first_free: int,
    scope: RenumberScope,
) -> tuple[list[MovedFile], int]:
    """Renumber every file after the first in *ordered*; only each file's own ``id``,
    ``sequence_id``, name and the hint scaffolded from its number change. Returns the moves and
    the next free number."""
    prefix = prefix_from_id(key)
    moved: list[MovedFile] = []
    next_free = first_free
    for md in ordered[1:]:
        new_display = format_item_id(prefix, next_free, DISPLAY_ID_PADDING)
        new_padded = format_item_id(prefix, next_free, padding)
        text = await _aio.read_text(md)
        fm = sections.split_frontmatter(text)[0]
        fm["id"] = new_display
        fm["sequence_id"] = next_free
        slug = file_slug(md, fm, prefix)
        target = md.parent / (f"{new_padded}-{slug}.md" if slug else f"{new_padded}.md")
        new_text = sections.replace_frontmatter(text, fm)
        new_text = scope.rehint(new_text, fm, target, str(number_for_id(key)))
        await write_text(md, new_text)
        await _aio.path_rename(md, target)
        moved.append(MovedFile(key, new_display, _rel(squad_dir, md), _rel(squad_dir, target)))
        next_free += 1
    return moved, next_free


async def references_left(
    squad_dir: Path, item_files: list[Path], old_ids: list[str]
) -> list[LeftReference]:
    """Every reference to each of *old_ids* in *item_files*, as the files stand now."""
    return [
        LeftReference(old_id, rel, where, text)
        for old_id in old_ids
        for rel, where, text in await references_to(squad_dir, item_files, old_id)
    ]


async def renumber_same_id_groups(
    *,
    squad_dir: Path,
    groups: dict[str, list[Path]],
    scope: RenumberScope,
    padding: int,
    first_free: int,
) -> SameIdRenumber:
    """Give every file but the kept one of each renumberable group a fresh number. The outcome
    names the ids it renumbered; :func:`references_left` lists what still cites them.

    The kept file is the one the previous index points at, else the first by name. A group with
    a file outside its own type folder, two files sharing a slug, or nothing but identical
    copies is left for the caller to refuse."""
    outcome = SameIdRenumber()
    next_free = first_free
    for key, files in sorted(groups.items()):
        prefix = prefix_from_id(key)
        if not await renumberable(files, prefix, scope):
            continue
        by_name = sorted(files, key=lambda p: _stem_key(squad_dir, p))
        indexed = scope.indexed_paths.get(key)
        kept = indexed if indexed in files else by_name[0]
        ordered = [kept, *(md for md in by_name if md != kept)]
        moved, next_free = await _renumber_files(squad_dir, ordered, key, padding, next_free, scope)
        outcome.moved += moved
        outcome.ids.append(key)
    return outcome
