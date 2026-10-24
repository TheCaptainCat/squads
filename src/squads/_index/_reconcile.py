"""Rebuild the index from the item files alone, before any migration runner reads it.

The routine resolves no vocabulary, and nothing declared reaches it. With a readable previous
index a file is the squad's item only where the index keeps items of its prefix: a *location*
is the directory and file-name prefix of an entry's recorded path, and nothing outside a
location's directory is opened, indexed, reported, counted or written. With no readable previous
index there are no locations, so the tree is walked and every file with an item's name and a
well-formed ``id`` is recognised. It carries forward and never fabricates: a file's own
frontmatter replaces its entry, a file with no entry gains one, an entry whose file is gone is
dropped and named, and a file it cannot index leaves its previous entry as it was. It builds the
index and reports; it refuses nothing and writes no markdown file, and the caller decides
whether the built index is kept.
"""

import os
import re
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any

from squads import _aio
from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._models._index import SquadsDB
from squads._models._item import (
    DEFAULT_ID_PADDING,
    INVENTED_WHEN_ABSENT,
    Item,
    prefix_from_id,
)
from squads._paths import number_for_id
from squads._sections import split_frontmatter

#: The shape of an item file name in the tree walk, which is the only place a prefix is read
#: by pattern: ``<PREFIX>-<digits>-<slug>.md``, a prefix being hyphen-joined segments of letters,
#: digits and underscores that each hold a character other than a digit, so the first segment of
#: digits alone is the number even when the slug starts with digits.
_SEGMENT = r"[A-Za-z0-9_]*[A-Za-z_][A-Za-z0-9_]*"
_WALK_NAME_RE = re.compile(
    rf"^(?P<prefix>{_SEGMENT}(?:-{_SEGMENT})*)-(?P<digits>\d+)-(?P<slug>.+)\.md$"
)


@dataclass(frozen=True)
class Unindexable:
    """An item file that could not be given an index entry of its own, and why."""

    path: str
    cause: str
    #: The cause is a number two different ids share, which only a renumber resolves.
    shared_number: bool = False


@dataclass(frozen=True)
class ReconcileResult:
    """What the reconcile did: ids newly indexed, ids dropped because no file backs them any
    more, and files it could not index."""

    indexed: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    unindexable: tuple[Unindexable, ...] = ()
    #: The counter the built index carries.
    counter: int = field(default=0, compare=False)
    #: Whether a readable previous index was read (otherwise the tree was walked).
    had_index: bool = field(default=True, compare=False)


@dataclass(frozen=True)
class _Candidate:
    path: Path
    rel: str
    prefix: str
    digits: str


def fold_stem_into_floor(
    max_n: int, max_filename_width: int, stem_seq: int | None, digit_run: str | None
) -> tuple[int, int]:
    """Fold one file's filename-derived sequence number and digit-run width into a running
    counter/padding floor, so no file's own number or width can regress either."""
    if stem_seq is not None:
        max_n = max(max_n, stem_seq)
    if digit_run:
        max_filename_width = max(max_filename_width, len(digit_run))
    return max_n, max_filename_width


def carry_forward_indexed_timestamps(
    item: Item, data: dict[str, Any], known_corpus: SquadsDB | None
) -> None:
    """Keep the previously indexed timestamp for any key the file just read carries no value
    for, so a rebuild never commits an invented ``now`` over an entry the index held."""
    if known_corpus is None:
        return
    previous = known_corpus.get(item.id)
    if previous is None:
        return
    for key in INVENTED_WHEN_ABSENT:
        if data.get(key) is None:
            setattr(item, key, getattr(previous, key))


def entry_prefix(entry: Item) -> str:
    """The spelling of *entry*'s prefix as its recorded file name carries it: the id's prefix
    when the name starts with it, otherwise what stands before the entry's own number in the
    name (an index from before ids were stored has no id). ``""`` when neither applies."""
    name = Path(entry.path).name
    if entry.prefix and name.startswith(f"{entry.prefix}-"):
        return entry.prefix
    found = re.match(rf"^(.+?)-0*{entry.sequence_id}(?=-|\.md$)", name)
    return found[1] if found else ""


def entry_name(entry: Item) -> str:
    """The id an operator can find *entry* by: its stored id, else the prefix and number its
    recorded file name carries, else the recorded path."""
    if entry.prefix:
        return entry.id
    prefix = entry_prefix(entry)
    return f"{prefix}-{entry.sequence_id}" if prefix else entry.path


type Location = tuple[str, str]
"""A directory (squad-relative, ``.`` for the squad directory itself) and an item prefix."""


def _locations(previous: SquadsDB) -> set[Location]:
    """Where the squad keeps items: the directory and file-name prefix of every previous entry's
    recorded path."""
    found: set[Location] = set()
    for entry in previous.items.values():
        prefix = entry_prefix(entry)
        if prefix:
            found.add((Path(entry.path).parent.as_posix(), prefix))
    return found


def _rel(directory: str, name: str) -> str:
    return name if directory == "." else f"{directory}/{name}"


def _scan_directories(
    squad_dir: Path, locations: set[Location]
) -> tuple[list[_Candidate], list[Path]]:
    """The candidates named for an item of a location's prefix in that location's directory,
    and the other markdown files in those directories (listed, not recursed into). A directory
    with an item's name is a candidate too: the read of it is then refused."""
    prefixes: dict[str, dict[str, re.Pattern[str]]] = {}
    for directory, prefix in locations:
        named = re.compile(rf"^{re.escape(prefix)}-(?P<digits>\d+)(?:-.+)?\.md$")
        prefixes.setdefault(directory, {})[prefix] = named
    candidates: list[_Candidate] = []
    others: list[Path] = []
    for directory, wanted in sorted(prefixes.items()):
        folder = squad_dir / directory
        if not folder.is_dir():
            continue
        for entry in sorted(os.scandir(folder), key=lambda e: e.name):
            hit = next(((p, m) for p, rx in wanted.items() if (m := rx.match(entry.name))), None)
            if hit:
                prefix, match = hit
                candidates.append(
                    _Candidate(
                        Path(entry.path), _rel(directory, entry.name), prefix, match["digits"]
                    )
                )
            elif entry.name.endswith(".md") and entry.is_file():
                others.append(Path(entry.path))
    return sorted(candidates, key=lambda c: c.rel), others


def _walk_tree(squad_dir: Path) -> list[_Candidate]:
    """With no readable index there are no locations: every entry under *squad_dir* with an
    item's name, dot-directories skipped. A directory with such a name is a candidate too."""
    found: list[_Candidate] = []
    for root, dirs, files in os.walk(squad_dir):
        named = [d for d in dirs if _WALK_NAME_RE.match(d)]
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in named)
        for name in sorted([*files, *named]):
            match = _WALK_NAME_RE.match(name)
            if match:
                path = Path(root) / name
                rel = path.relative_to(squad_dir).as_posix()
                found.append(_Candidate(path, rel, match["prefix"], match["digits"]))
    return sorted(found, key=lambda c: c.rel)


def _parse_id(fid: object) -> tuple[str, int] | None:
    """The prefix and number the model's own id parsing reads from *fid*, or ``None``."""
    if not isinstance(fid, str) or not prefix_from_id(fid):
        return None
    try:
        return prefix_from_id(fid), number_for_id(fid)
    except SquadsError:
        return None


async def _read_previous(store: IndexStore) -> SquadsDB | None:
    try:
        return await store.load(validate_vocab=False)
    except SquadsError:
        return None


def _identity_problem(data: dict[str, Any]) -> str | None:
    """Why *data* names no usable identity, or ``None`` when its ``id`` is well formed."""
    fid = data.get("id")
    if fid is None:
        return "frontmatter has no id"
    if _parse_id(fid) is None:
        return f"id {fid!r} is not of the shape PREFIX-NUMBER"
    return None


def _build_item(data: dict[str, Any], rel: str) -> Item:
    """The index entry *data* describes, reading a missing ``sequence_id`` from the ``id``."""
    fid = str(data["id"])
    number = int(fid.rpartition("-")[2])
    if data.get("sequence_id") is None:
        data = {**data, "sequence_id": number}
    elif data["sequence_id"] != number:
        raise SquadsError(f"id {fid} and sequence_id {data['sequence_id']!r} name different items")
    return Item.from_frontmatter_verbatim(data, path=rel)


class _Scan:
    """What one pass over the candidate files found."""

    def __init__(self, squad_dir: Path, previous: SquadsDB | None) -> None:
        self.squad_dir = squad_dir
        self.previous = previous
        self.by_path = {i.path: i for i in previous.items.values()} if previous else {}
        self.built: dict[int, list[tuple[_Candidate, Item]]] = {}
        #: Other markdown files in a location's directory that carry some id, by that id.
        self.carriers: dict[tuple[str, int], list[str]] = {}
        self.unindexable: list[Unindexable] = []
        #: Previous entries a file that could not be indexed stands for.
        self.carried: set[int] = set()
        self.max_n = 0
        self.max_width = 0

    def prior(self, cand: _Candidate) -> Item | None:
        """The previous entry for *cand*: by the path it sits at, then, only when that entry's
        own file is gone, by its file-name number under the same prefix."""
        if self.previous is None:
            return None
        hit = self.by_path.get(cand.rel)
        if hit is not None:
            return hit
        entry = self.previous.items.get(int(cand.digits))
        if entry is None or entry_prefix(entry) != cand.prefix:
            return None
        if (self.squad_dir / entry.path).exists():
            return None
        return entry

    def note(self, cand: _Candidate) -> None:
        self.max_n, self.max_width = fold_stem_into_floor(
            self.max_n, self.max_width, int(cand.digits), cand.digits
        )

    def reject(self, cand: _Candidate, cause: str) -> None:
        """Report *cand*. A file that is not accepted as an item moves neither floor."""
        self.unindexable.append(Unindexable(cand.rel, cause))
        prior = self.prior(cand)
        if prior is not None:
            self.carried.add(prior.sequence_id)

    async def read(self, cand: _Candidate) -> None:
        try:
            data, _ = split_frontmatter(await _aio.read_text(cand.path), source=cand.rel)
        except FileNotFoundError:
            return
        except SquadsError as exc:
            self.reject(cand, str(exc))
            return
        problem = _identity_problem(data)
        if problem is not None:
            # With no index nothing says this file is an item, so one with no usable id is not.
            if self.previous is not None:
                self.reject(cand, problem)
            return
        try:
            item = _build_item(data, cand.rel)
        except SquadsError as exc:
            self.reject(cand, str(exc))
            return
        carry_forward_indexed_timestamps(item, data, self.previous)
        self.built.setdefault(item.sequence_id, []).append((cand, item))

    async def read_carriers(self, others: list[Path]) -> None:
        """Note the id of each other markdown file in a location's directory; one that cannot be
        read, or carries none, is left alone."""
        for path in others:
            try:
                data, _ = split_frontmatter(await _aio.read_text(path))
            except (SquadsError, FileNotFoundError):  # fmt: skip
                continue
            key = _parse_id(data.get("id"))
            if key is not None:
                self.carriers.setdefault(key, []).append(
                    path.relative_to(self.squad_dir).as_posix()
                )

    def settle(self) -> dict[int, Item]:
        """The items whose id and number exactly one file claims; every file of a clash is
        rejected, and the entry the index held stays."""
        accepted: dict[int, Item] = {}
        for seq, group in sorted(self.built.items()):
            copies = [
                rel
                for _, item in group
                for rel in self.carriers.get(_parse_id(item.id) or ("", 0), [])
            ]
            if len(group) == 1 and not copies:
                accepted[seq] = group[0][1]
                self.note(group[0][0])
                self.max_n = max(self.max_n, seq)
                continue
            self.carried.add(seq)
            self._reject_clash(seq, group, copies)
        return accepted

    def _reject_clash(
        self, seq: int, group: list[tuple[_Candidate, Item]], copies: list[str]
    ) -> None:
        ids = sorted({item.id for _, item in group})
        where = {cand.rel: item.id for cand, item in group}
        if len(ids) > 1:
            named = " and ".join(f"{i} ({r})" for r, i in sorted(where.items()))
            cause = f"number {seq} is used by {named}; the index holds one item per number"
            for rel in where:
                self.unindexable.append(Unindexable(rel, cause, shared_number=True))
            return
        every = sorted([*where, *copies])
        for rel in every:
            others = ", ".join(r for r in every if r != rel)
            self.unindexable.append(Unindexable(rel, f"id {ids[0]} is also claimed by {others}"))


async def plan_reconcile(
    squad_dir: Path, store: IndexStore, schema_version: str
) -> tuple[SquadsDB, ReconcileResult]:
    """Build, without writing, the index that mirrors the item files under *squad_dir*, stamped
    with *schema_version* (the corpus's own)."""
    previous = await _read_previous(store)
    scan = _Scan(squad_dir, previous)
    if previous is None:
        candidates = await _aio.to_thread(partial(_walk_tree, squad_dir))
        others: list[Path] = []
    else:
        candidates, others = await _aio.to_thread(
            partial(_scan_directories, squad_dir, _locations(previous))
        )
    for cand in candidates:
        await scan.read(cand)
    await scan.read_carriers(
        [
            p
            for p in others
            if p.relative_to(squad_dir).as_posix() not in {c.rel for c in candidates}
        ]
    )
    items = scan.settle()
    accepted = dict(items)
    accepted_paths = {item.path for item in items.values()}
    missing: list[str] = []
    if previous is not None:
        for seq, entry in sorted(previous.items.items()):
            if seq in items:
                continue
            kept = seq in scan.carried or (
                entry.path not in accepted_paths and (squad_dir / entry.path).is_file()
            )
            if kept:
                if not entry.prefix:
                    entry.prefix = entry_prefix(entry)
                items[seq] = entry
            else:
                missing.append(entry_name(entry))
    indexed = tuple(
        item.id
        for seq, item in sorted(accepted.items())
        if previous is None or seq not in previous.items
    )
    db = SquadsDB(
        schema_version=schema_version,
        counter=max(previous.counter if previous else 0, scan.max_n),
        padding=max(previous.padding if previous else DEFAULT_ID_PADDING, scan.max_width),
        items=dict(sorted(items.items())),
    )
    result = ReconcileResult(
        indexed=indexed,
        missing=tuple(missing),
        unindexable=tuple(scan.unindexable),
        counter=db.counter,
        had_index=previous is not None,
    )
    return db, result


async def reconcile_index(
    squad_dir: Path, store: IndexStore, schema_version: str
) -> ReconcileResult:
    """:func:`plan_reconcile`, then write the built index."""
    db, result = await plan_reconcile(squad_dir, store, schema_version)
    await store.overwrite(db)
    return result
