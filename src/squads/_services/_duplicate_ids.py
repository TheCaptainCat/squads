"""One detector for item files that carry the same frontmatter ``id``, shared by ``check``,
``repair`` and the managed-skill restamp."""

import re
from collections.abc import Iterable
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

#: What the restamp reports when it declines to write over a duplicate.
RESTAMP_BLOCKED_REMEDY = "remove or rename one of the two files"

_CONFLICT_LINE = re.compile(r"^(<{7}|={7}|>{7})( .*)?$", re.MULTILINE)


def has_conflict_markers(text: str) -> bool:
    """True when *text* carries a line that starts a merge-conflict marker."""
    return _CONFLICT_LINE.search(text) is not None


def normalized_id(fid: object) -> str | None:
    """*fid* spelled one way whatever its padding, or ``None`` when it is not a well-formed id."""
    if not isinstance(fid, str):
        return None
    try:
        return format_item_id(prefix_from_id(fid), number_for_id(fid), DISPLAY_ID_PADDING)
    except SquadsError:
        return None


def duplicate_groups(pairs: Iterable[tuple[object, Path]]) -> dict[str, list[Path]]:
    """Every id carried by more than one file, mapped to those files in path order."""
    groups: dict[str, list[Path]] = {}
    for fid, md in pairs:
        key = normalized_id(fid)
        if key is not None:
            groups.setdefault(key, []).append(md)
    return {key: sorted(files) for key, files in groups.items() if len(files) > 1}


# --------------------------------------------------------------------------- repair --renumber


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


@dataclass
class SameIdRenumber:
    """What ``repair --renumber`` did about ids carried by more than one file."""

    lines: list[str] = field(default_factory=list[str])
    references_left: bool = False


def _file_slug(md: Path, fm: dict[str, Any], prefix: str) -> str:
    """A file's slug: the roster slug in ``extra``, else the frontmatter ``slug``, else the
    slug segment of its name."""
    extra = fm.get("extra")
    for candidate in (
        cast("dict[str, Any]", extra).get("slug") if isinstance(extra, dict) else None,
        fm.get("slug"),
    ):
        if isinstance(candidate, str) and candidate:
            return candidate
    return md.stem.removeprefix(f"{prefix}-").partition("-")[2]


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
            snippet = line.strip()
            hits.append((where, f'"{snippet[:70]}{"..." if len(snippet) > 70 else ""}"'))
    return hits


async def _references_to(
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
        except OSError, SquadsError:
            continue
        rel = _rel(squad_dir, md)
        for key, value in fm.items():
            if key not in ("id", "sequence_id"):
                found += [(rel, w, t) for w, t in _frontmatter_hits(value, pattern, str(key))]
        first_line = text[: len(text) - len(body)].count("\n") + 1
        found += [(rel, w, t) for w, t in _text_hits(body, pattern, first_line)]
    return found


async def renumber_same_id_groups(
    *,
    squad_dir: Path,
    item_files: list[Path],
    groups: dict[str, list[Path]],
    padding: int,
    first_free: int,
) -> SameIdRenumber:
    """Give every file but the first (by squad-relative path, byte order) of each group whose
    slugs all differ a fresh number, rewriting only that file's own ``id``/``sequence_id`` and
    its name, then list every reference to the old id without changing any. A group where two
    files share a slug is left alone for the caller to refuse."""
    outcome = SameIdRenumber()
    next_free = first_free
    for key, files in sorted(groups.items()):
        prefix = prefix_from_id(key)
        slugs: list[str] = []
        for md in files:
            try:
                fm = sections.split_frontmatter(await _aio.read_text(md))[0]
            except OSError, SquadsError:
                fm = {}
            slugs.append(_file_slug(md, fm, prefix))
        if len(set(slugs)) < len(slugs):
            continue
        if len({md.read_bytes() for md in files}) == 1:
            continue  # an identical copy, not a collision: nothing to keep apart
        ordered = sorted(files, key=lambda p: _rel(squad_dir, p).encode())
        block = [
            f"{key}: {len(ordered)} files, different slugs",
            f"  kept       {_rel(squad_dir, ordered[0])}",
        ]
        for md in ordered[1:]:
            new_display = format_item_id(prefix, next_free, DISPLAY_ID_PADDING)
            new_padded = format_item_id(prefix, next_free, padding)
            text = await _aio.read_text(md)
            fm = sections.split_frontmatter(text)[0]
            fm["id"] = new_display
            fm["sequence_id"] = next_free
            slug = _file_slug(md, fm, prefix)
            target = md.parent / (f"{new_padded}-{slug}.md" if slug else f"{new_padded}.md")
            await write_text(md, sections.replace_frontmatter(text, fm))
            await _aio.path_rename(md, target)
            block.append(
                f"  renumbered {_rel(squad_dir, md)} -> {new_display} ({_rel(squad_dir, target)})"
            )
            next_free += 1
        current = [p for p in item_files if p.exists()]
        refs = await _references_to(squad_dir, current, key)
        if refs:
            outcome.references_left = True
            block.append(f"  references to {key} left unchanged; check each by hand:")
            block += [f"    {rel}   {where}   {text}" for rel, where, text in refs]
        else:
            block.append("  no references")
        outcome.lines += block
    return outcome
