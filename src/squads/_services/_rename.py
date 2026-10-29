"""Bulk-rename every item of one type to another, in a single transaction. A rename is a vocabulary
change, so sub-entities and status always carry over; it reuses ``_retype``'s per-item and edge-
resync primitives, batching the id rewrite and the resync into one pass.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._itemfile import (
    frontmatter_skew,
    read_item_text,
    remap_ids_text,
    rewrite_ids,
    skew_message,
    write_text,
)
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._metadata import value_problem
from squads._models._participants import SYSTEM_SLUG
from squads._models._subentity import SubEntity
from squads._paths import SquadPaths
from squads._services._base import ServiceCore
from squads._services._results import RenameFieldResult, RenameKindResult, RenameResult
from squads._services._retype import (
    apply_type_change,
    resync_edges,
)
from squads._workflow._models import WorkflowSpec


def _validate_rename_types(spec: WorkflowSpec, old_type: str, new_type: str) -> None:
    """Raise unless both types are declared, non-roster types, and distinct."""
    for t in (old_type, new_type):
        if t not in spec.items:
            raise SquadsError(f"{t!r} is not declared in the active spec")
        if spec.item_is_roster(t):
            raise SquadsError(
                f"{t!r} is a reserved roster type (role/skill/operator) and cannot be renamed"
            )
    if old_type == new_type:
        raise SquadsError(f"cannot rename {old_type!r} to itself")


def _validate_no_invalid_children(
    spec: WorkflowSpec, db: SquadsDB, old_ids: set[str], old_type: str, new_type: str
) -> None:
    """Raise if any live child of a renamed item would have an invalid parent under
    *new_type* — the same check ``_retype.py`` runs per item, applied once across the
    whole renamed set."""
    invalid = [
        c
        for c in db.items.values()
        if c.parent in old_ids and not spec.parent_allowed(c.type, new_type)
    ]
    if invalid:
        ids = ", ".join(sorted(c.id for c in invalid))
        raise SquadsError(
            f"cannot rename {old_type} to {new_type}: child item(s) {ids} would have an "
            "invalid parent type. Re-parent or remove those children first."
        )


def _validate_rename_status(spec: WorkflowSpec, item_type: str, new_status: str) -> None:
    """Raise unless *item_type* is a declared, non-roster type and *new_status* is a
    member of that type's own lifecycle states."""
    if item_type not in spec.items:
        raise SquadsError(f"{item_type!r} is not declared in the active spec")
    if spec.item_is_roster(item_type):
        raise SquadsError(
            f"{item_type!r} is a reserved roster type (role/skill/operator); "
            "its status cannot be bulk-renamed"
        )
    states = spec.workflow_for(item_type).states
    if new_status not in states:
        raise SquadsError(
            f"{new_status!r} is not a state of {item_type}'s lifecycle "
            f"(states: {', '.join(sorted(states))})"
        )


def _move_problem(spec: WorkflowSpec, owner: str, *, is_item: bool, new: str, value: Any) -> str:
    """Why *value* cannot move to key *new* on *owner* (an item type or a sub-entity kind), or an
    empty string when it can: *new* is a declared field whose collection holds the value, or a
    declared attribute of that type that accepts it."""
    fields = {f.code: f for f in spec.fields_for(owner)}
    if new in fields:
        collection = spec.collection(fields[new].collection)
        if collection.declares(value):
            return ""
        return f"{value!r} is not a value of {new!r} (collection {fields[new].collection!r})"
    attribute = spec.item_attributes(owner).get(new) if is_item else None
    if attribute is not None:
        problem = value_problem(attribute, value)
        return "" if problem is None else f"{new!r}: {problem}"
    return f"{owner!r} does not declare {new!r}"


def _renamed_key(attributes: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    """*attributes* with key *old* replaced by *new* in place, the order kept."""
    return {(new if key == old else key): value for key, value in attributes.items()}


async def _snapshot_files(paths: SquadPaths, db: SquadsDB) -> dict[int, tuple[Path, str]]:
    """Read every item's current (path, text) before any mutation, so a mid-flight failure can
    restore the filesystem as well as the index. A stale indexed path is reported cleanly rather
    than raised as ``FileNotFoundError`` (see :func:`~squads._itemfile.read_item_text`).
    """
    snap: dict[int, tuple[Path, str]] = {}
    for it in db.items.values():
        p = item_file(paths, it)
        snap[it.sequence_id] = (p, await read_item_text(p, it.id))
    return snap


def _check_batch_skew(
    items: Iterable[Item], snapshot: dict[int, tuple[Path, str]], *, default_kind: str
) -> None:
    """Refuse before any write if any of *items* has diverged from its on-disk frontmatter: the
    batch form of :func:`~squads._itemfile.ensure_no_skew`, so a bulk op never partially applies
    over an unrepaired item. *default_kind* is resolved once for the batch.
    """
    problems = [
        skew_message(item, diverging)
        for item in items
        if (entry := snapshot.get(item.sequence_id)) is not None
        and (diverging := frontmatter_skew(entry[1], item, default_kind=default_kind))
    ]
    if problems:
        raise SquadsError(" | ".join(problems))


async def _rollback_files(
    paths: SquadPaths, db: SquadsDB, snapshot: dict[int, tuple[Path, str]]
) -> None:
    """Best-effort restoration of every snapshotted file to its original path + bytes."""
    for seq, (orig_path, orig_text) in snapshot.items():
        item = db.items.get(seq)
        current_path = item_file(paths, item) if item is not None else orig_path
        if current_path != orig_path and await _aio.path_exists(current_path):
            await _aio.mkdir(orig_path.parent, parents=True, exist_ok=True)
            await _aio.path_rename(current_path, orig_path)
        await write_text(orig_path, orig_text)


class RenameMixin(ServiceCore):
    async def rename_type(self, old_type: str, new_type: str) -> RenameResult:
        """Bulk-move every item of *old_type* to *new_type* in one transaction. Both must be
        declared non-roster types, and a live child that would become invalid under *new_type* is
        refused. Every item is rewritten first, then one ``{old_id: new_id}`` remap drives a single
        ``rewrite_ids`` pass and edge resync, with a reflog line and system comment per item. Any
        failure restores every squad file to its pre-call bytes and path.
        """
        old_type = str(old_type)  # coerce StrEnum members to plain str
        new_type = str(new_type)
        async with self.store.transaction() as db:
            _validate_rename_types(self.spec, old_type, new_type)

            old_items = sorted(
                (it for it in db.items.values() if it.type == old_type),
                key=lambda it: it.sequence_id,
            )
            old_ids = {it.id for it in old_items}
            _validate_no_invalid_children(self.spec, db, old_ids, old_type, new_type)

            # Everything above is read-only; the snapshot below is taken only once validation
            # has passed, right before the first byte on disk changes.
            snapshot = await _snapshot_files(self.paths, db)
            # Resolved once for the whole batch, before the pre-flight check below — not per
            # item — so a spec declaring the wrong number of default ref kinds fails as one
            # clean refusal naming the spec rather than partway through the rename.
            default_kind = self.spec.default_ref_kind()
            # Pre-flight the whole set before the first write: a mid-flight refusal would leave a
            # partially applied bulk rename. Reuses the snapshot just taken.
            _check_batch_skew(old_items, snapshot, default_kind=default_kind)
            try:
                # Per-item self-rewrite (id/prefix/file/frontmatter; status carried
                # unconditionally). Each renamed file's text stays in memory and is written
                # once, below, after the id remap and the audit comment.
                pairs: list[tuple[str, Item]] = []
                composed: dict[int, tuple[Path, str]] = {}
                remap: dict[str, str] = {}
                for item in old_items:
                    old_id = item.id
                    composed[item.sequence_id] = await apply_type_change(
                        self.paths,
                        self.spec,
                        db,
                        item,
                        new_type,
                        carry_status=True,
                        text=snapshot[item.sequence_id][1],
                    )
                    remap[old_id] = item.id
                    pairs.append((old_id, item))

                # Single batched pass across every other squad file.
                other_paths = [
                    item_file(self.paths, it)
                    for it in db.items.values()
                    if it.sequence_id not in composed
                ]
                changed = set(await rewrite_ids(other_paths, remap))

                # Renamed items are not excluded: two of them may ref each other, and that needs
                # remapping too.
                resync_edges(db, remap, exclude=set())

                ids: list[tuple[str, str]] = []
                for old_id, item in pairs:
                    db.add(item)
                    new_path, text = composed[item.sequence_id]
                    remapped = remap_ids_text(text, remap)
                    if remapped != text:
                        changed.add(new_path)
                    await write_text(
                        new_path, _with_rename_comment(remapped, old_id, item.id, item)
                    )
                    self.store.log(
                        "rename-type",
                        item.id,
                        {
                            "old_id": old_id,
                            "new_id": item.id,
                            "old_type": old_type,
                            "new_type": new_type,
                        },
                    )
                    ids.append((old_id, item.id))
                touched = [
                    p for it in db.items.values() if (p := item_file(self.paths, it)) in changed
                ]
            except Exception:
                await _rollback_files(self.paths, db, snapshot)
                raise

            rewritten_names = [str(p.relative_to(self.paths.squad_dir)) for p in touched]

        return RenameResult(renamed=len(pairs), ids=ids, rewritten=rewritten_names)

    async def rename_status(self, item_type: str, old_status: str, new_status: str) -> RenameResult:
        """Bulk-move every *item_type* item at *old_status* to *new_status* in one transaction,
        scoped to that type's own lifecycle. *new_status* must be a state of that workflow (not a
        ``can_transition`` edge) and brings its terminal/open classification. Frontmatter-only; sub-
        entity statuses are untouched. Each item gets a reflog line and system comment, and any
        failure restores every squad file to its pre-call bytes.
        """
        item_type = str(item_type)  # coerce StrEnum members to plain str
        old_status = str(old_status)
        new_status = str(new_status)
        async with self.store.transaction() as db:
            _validate_rename_status(self.spec, item_type, new_status)
            await self._refuse_any_duplicated_id()

            matching = sorted(
                (
                    it
                    for it in db.items.values()
                    if it.type == item_type and it.status == old_status
                ),
                key=lambda it: it.sequence_id,
            )

            # Everything above is read-only; the snapshot below is taken only once validation
            # has passed, right before the first byte on disk changes.
            snapshot = await _snapshot_files(self.paths, db)
            # Resolved once for the whole batch — see rename_type's matching comment.
            default_kind = self.spec.default_ref_kind()
            # Pre-flight the whole affected set before the first write — see rename_type's
            # matching comment; reuses the snapshot just taken, no extra read.
            _check_batch_skew(matching, snapshot, default_kind=default_kind)
            try:
                ids: list[tuple[str, str]] = []
                rewritten: list[Path] = []
                for item in matching:
                    item.status = new_status
                    item.updated_at = clock.now()
                    path = item_file(self.paths, item)
                    text = sections.replace_frontmatter(
                        snapshot[item.sequence_id][1],
                        item.to_frontmatter_dict(),
                        source=str(path),
                    )
                    await write_text(
                        path, _with_rename_status_comment(text, old_status, new_status)
                    )
                    db.add(item)
                    self.store.log(
                        "rename-status",
                        item.id,
                        {"type": item_type, "old_status": old_status, "new_status": new_status},
                    )
                    ids.append((item.id, item.id))  # id itself never changes
                    rewritten.append(path)
            except Exception:
                await _rollback_files(self.paths, db, snapshot)
                raise

            rewritten_names = [str(p.relative_to(self.paths.squad_dir)) for p in rewritten]

        return RenameResult(renamed=len(matching), ids=ids, rewritten=rewritten_names)

    async def rename_field(
        self, old: str, new: str, *, types: Iterable[str] = (), kinds: Iterable[str] = ()
    ) -> RenameFieldResult:
        """Move every value stored under key *old* to key *new*, on items and sub-entity entries,
        in one transaction. Refuses, writing nothing, when a holder of *old* does not declare *new*,
        already holds *new*, or holds a value *new* does not accept; the refusal names each one.
        *types* and *kinds* limit the move to the items of those types and the entries of those
        kinds; with neither, every holder moves. Frontmatter only; each changed item gets a reflog
        line and a system comment, and any failure restores every squad file to its pre-call bytes.
        """
        old = str(old)
        new = str(new)
        if old == new:
            raise SquadsError(f"cannot rename field {old!r} to itself")
        scope = _FieldScope(set(types), set(kinds))
        scoped = bool(scope.types or scope.kinds)
        scope.refuse_undeclared(self.spec)
        async with self.store.transaction() as db:
            await self._refuse_any_duplicated_id()
            holders: list[tuple[Item, bool, list[SubEntity]]] = []
            problems: list[str] = []
            for item in sorted(db.items.values(), key=lambda it: it.sequence_id):
                kind = self.spec.item_subentity_kind(item.type)
                own = old in item.attributes and scope.takes_type(item.type)
                entries = [
                    s for s in item.subentities if old in s.attributes and scope.takes_kind(kind)
                ]
                if not own and not entries:
                    continue
                holders.append((item, own, entries))
                if own:
                    problems += self._field_move_problems(
                        item.id, item.type, item.attributes, old, new, is_item=True
                    )
                problems += self._entry_move_problems(item, kind, entries, old, new)
            if problems:
                hint = "" if scoped else " (limit the move with --type or --kind)"
                raise SquadsError(
                    f"cannot rename field {old!r} to {new!r}: " + "; ".join(problems) + hint
                )

            snapshot = await _snapshot_files(self.paths, db)
            default_kind = self.spec.default_ref_kind()
            _check_batch_skew([item for item, _, _ in holders], snapshot, default_kind=default_kind)
            try:
                for item, own, entries in holders:
                    if own:
                        item.attributes = _renamed_key(item.attributes, old, new)
                    for entry in entries:
                        entry.attributes = _renamed_key(entry.attributes, old, new)
                    item.updated_at = clock.now()
                    path = item_file(self.paths, item)
                    text = sections.replace_frontmatter(
                        snapshot[item.sequence_id][1],
                        item.to_frontmatter_dict(),
                        source=str(path),
                    )
                    await write_text(path, _with_rename_field_comment(text, old, new))
                    db.add(item)
                    self.store.log("rename-field", item.id, {"old": old, "new": new})
            except Exception:
                await _rollback_files(self.paths, db, snapshot)
                raise

        return RenameFieldResult(
            items=sum(1 for _, own, _ in holders if own),
            entries=sum(len(entries) for _, _, entries in holders),
        )

    async def rename_kind(self, old: str, new: str) -> RenameKindResult:
        """Bring the stored spellings of kind *old* to the declaration of kind *new*, in one
        transaction: block markers (with their regions), the container marker, local ids and the
        mappings that target *new*. Refuses, writing nothing, when *new* is undeclared, a type that
        carries *old* blocks does not host *new*, an item mixes local prefixes, or a marker pair is
        missing. Items that already match are not written. Markdown is rewritten through the marker
        helpers only; each changed item gets a reflog line and a system comment.
        """
        old = str(old)
        new = str(new)
        spec = self.spec
        if new not in spec.subentity_kinds:
            raise SquadsError(f"{new!r} is not a sub-entity kind the active spec declares")
        async with self.store.transaction() as db:
            await self._refuse_any_duplicated_id()
            snapshot = await _snapshot_files(self.paths, db)
            plan = _KindPlan(spec, old, new)
            items = sorted(db.items.values(), key=lambda it: it.sequence_id)
            problems: list[str] = []
            for item in items:
                problems += plan.survey(item, snapshot[item.sequence_id][1])
            if problems:
                raise SquadsError(f"cannot rename kind {old!r} to {new!r}: " + "; ".join(problems))

            texts: dict[int, str] = {}
            for item in items:
                text = plan.rewritten_text(item, snapshot[item.sequence_id][1])
                ids = plan.local_ids(item)
                mapped = plan.mappings(item, db.get(item.parent) if item.parent else None)
                if text != snapshot[item.sequence_id][1] or ids or mapped:
                    texts[item.sequence_id] = text
            changed = [it for it in items if it.sequence_id in texts]
            default_kind = spec.default_ref_kind()
            _check_batch_skew(changed, snapshot, default_kind=default_kind)
            try:
                for item in changed:
                    local = plan.local_ids(item)
                    mapped = plan.mappings(item, db.get(item.parent) if item.parent else None)
                    for entry in item.subentities:
                        entry.local_id = local.get(entry.local_id, entry.local_id)
                        entry.maps_to = mapped.get(entry.local_id, entry.maps_to)
                    item.updated_at = clock.now()
                    path = item_file(self.paths, item)
                    text = sections.replace_frontmatter(
                        texts[item.sequence_id], item.to_frontmatter_dict(), source=str(path)
                    )
                    await write_text(path, _with_rename_kind_comment(text, old, new))
                    db.add(item)
                    self.store.log("rename-kind", item.id, {"old": old, "new": new})
            except Exception:
                await _rollback_files(self.paths, db, snapshot)
                raise
        return RenameKindResult(items=len(changed))

    def _entry_move_problems(
        self, item: Item, kind: str | None, entries: list[SubEntity], old: str, new: str
    ) -> list[str]:
        """The reasons the *entries* of *item* cannot take *old*'s value under *new*."""
        if kind is None:
            return [
                f"{e.local_id} of {item.id}: {item.type} hosts no sub-entity kind" for e in entries
            ]
        return [
            problem
            for e in entries
            for problem in self._field_move_problems(
                f"{e.local_id} of {item.id}", kind, e.attributes, old, new, is_item=False
            )
        ]

    def _field_move_problems(
        self,
        where: str,
        owner: str,
        attributes: dict[str, Any],
        old: str,
        new: str,
        *,
        is_item: bool,
    ) -> list[str]:
        """The reasons the holder *where* cannot take *old*'s value under *new*, naming it."""
        if new in attributes:
            return [f"{where} already holds {new!r}"]
        problem = _move_problem(self.spec, owner, is_item=is_item, new=new, value=attributes[old])
        return [f"{where}: {problem}"] if problem else []


def _with_rename_field_comment(text: str, old: str, new: str) -> str:
    """*text* with a system comment recording the field rename appended to its discussion."""
    now_iso = clock.iso(clock.now())
    entry = discussion.format_comment(
        now_iso, SYSTEM_SLUG, SYSTEM_SLUG, [f"field renamed {old} → {new}"]
    )
    if sections.has_section(text, markers.DISCUSSION):
        return sections.append_to_section(text, markers.DISCUSSION, entry)
    return text


def _with_rename_comment(text: str, old_id: str, new_id: str, item: Item) -> str:
    """*text* with a system comment recording the rename appended to its discussion."""
    now_iso = clock.iso(clock.now())
    msg = f"renamed {old_id} → {new_id}; status carried as {item.status}"
    entry = discussion.format_comment(now_iso, SYSTEM_SLUG, SYSTEM_SLUG, [msg])
    if sections.has_section(text, markers.DISCUSSION):
        return sections.append_to_section(text, markers.DISCUSSION, entry)
    return text


def _with_rename_status_comment(text: str, old_status: str, new_status: str) -> str:
    """*text* with a system comment recording the status rename appended to its discussion."""
    now_iso = clock.iso(clock.now())
    msg = f"status renamed {old_status} → {new_status}"
    entry = discussion.format_comment(now_iso, SYSTEM_SLUG, SYSTEM_SLUG, [msg])
    if sections.has_section(text, markers.DISCUSSION):
        return sections.append_to_section(text, markers.DISCUSSION, entry)
    return text


_LOCAL_ID = re.compile(r"(.*?)(\d+)")
_BLOCK_SUFFIX = r"((?::body|:head|:discussion)?(?::end)?)"


def _split_local_id(local_id: str) -> tuple[str, str] | None:
    """The prefix and number of *local_id*, or ``None`` when it ends in no number."""
    found = _LOCAL_ID.fullmatch(local_id)
    return (found.group(1), found.group(2)) if found else None


@dataclass(frozen=True)
class _FieldScope:
    """The item types and sub-entity kinds a field move is limited to; both empty means all."""

    types: set[str]
    kinds: set[str]

    def refuse_undeclared(self, spec: WorkflowSpec) -> None:
        for name in sorted(self.types - set(spec.items)):
            raise SquadsError(f"--type {name!r} is not an item type the active spec declares")
        for name in sorted(self.kinds - set(spec.subentity_kinds)):
            raise SquadsError(f"--kind {name!r} is not a sub-entity kind the active spec declares")

    def takes_type(self, item_type: str) -> bool:
        return not (self.types or self.kinds) or item_type in self.types

    def takes_kind(self, kind: str | None) -> bool:
        return not (self.types or self.kinds) or (kind is not None and kind in self.kinds)


class _KindPlan:
    """What bringing kind *old* to kind *new*'s declaration changes, read from the active spec
    and each item's text: which items host or carry the kind, their stored prefix, and the new
    spelling of each marker tag, local id and mapping."""

    def __init__(self, spec: WorkflowSpec, old: str, new: str) -> None:
        self.new = new
        self.new_prefix = spec.subentity_kinds[new].local_prefix
        self.plural = spec.subentity_plural(new)
        self.spec = spec
        self.block = re.compile(rf"(?:{re.escape(old)}|{re.escape(new)}):([^:]+){_BLOCK_SUFFIX}")
        self.old_prefix: dict[str, str] = {}
        self.stale: dict[str, str] = {}
        self.targeting = {k for k in spec.subentity_kinds if spec.mapping_target_kind(k) == new}

    def hosts(self, item: Item) -> bool:
        return self.spec.item_subentity_kind(item.type) == self.new

    def _carries(self, text: str) -> bool:
        return any(
            self.block.fullmatch(tag.removeprefix(markers.PREFIX))
            for tag, _, _ in sections.iter_marker_spans(text)
        )

    def survey(self, item: Item, text: str) -> list[str]:
        """The reasons *item* cannot be brought to the declaration; records its stored prefix and
        stale container for the rewrite."""
        if not self.hosts(item):
            if self._carries(text):
                return [f"{item.id}: {item.type} does not host {self.new!r}"]
            return []
        if not item.subentities:
            return []
        problems: list[str] = []
        prefixes = {(_split_local_id(s.local_id) or (s.local_id, ""))[0] for s in item.subentities}
        if len(prefixes) > 1:
            return [
                f"{item.id}: entries carry more than one prefix ({', '.join(sorted(prefixes))})"
            ]
        self.old_prefix[item.id] = next(iter(prefixes))
        names = {self.new, *self._old_names(text)}
        problems += [
            f"{item.id}: no marker pair for {entry.local_id}"
            for entry in item.subentities
            if not any(
                markers.open_marker(f"{kind}:{entry.local_id}") in text
                and markers.close_marker(f"{kind}:{entry.local_id}") in text
                for kind in names
            )
        ]
        plural_pair = (
            markers.open_marker(self.plural) in text and markers.close_marker(self.plural) in text
        )
        if not plural_pair:
            stale = discussion.stale_container_tags(text, self.plural)
            if len(stale) != 1 or not (
                markers.open_marker(stale[0]) in text and markers.close_marker(stale[0]) in text
            ):
                problems.append(f"{item.id}: no container marker pair for {self.plural!r}")
            else:
                self.stale[item.id] = stale[0]
        return problems

    def _old_names(self, text: str) -> set[str]:
        """The kind names the block markers of *text* carry, besides the declared one."""
        names = {
            tag.removeprefix(markers.PREFIX).split(":")[0]
            for tag, _, _ in sections.iter_marker_spans(text)
            if self.block.fullmatch(tag.removeprefix(markers.PREFIX))
        }
        return names

    def _renamed(self, item_id: str, local_id: str) -> str:
        split = _split_local_id(local_id)
        if split is None or split[0] != self.old_prefix.get(item_id):
            return local_id
        return f"{self.new_prefix}{split[1]}"

    def local_ids(self, item: Item) -> dict[str, str]:
        """The entries of *item* whose local id changes, old to new."""
        if not self.hosts(item):
            return {}
        renamed = {s.local_id: self._renamed(item.id, s.local_id) for s in item.subentities}
        return {old: new for old, new in renamed.items() if old != new}

    def mappings(self, item: Item, parent: Item | None) -> dict[str, str | None]:
        """For each entry of *item* mapping onto *new*, its new ``maps_to``, keyed by local id."""
        if parent is None or self.spec.item_subentity_kind(item.type) not in self.targeting:
            return {}
        out: dict[str, str | None] = {}
        for entry in item.subentities:
            if (
                entry.maps_to
                and (renamed := self._renamed(parent.id, entry.maps_to)) != entry.maps_to
            ):
                out[entry.local_id] = renamed
        return out

    def rewritten_text(self, item: Item, text: str) -> str:
        """*text* with the block markers, container marker and block headings of *item* in the
        declared spelling; every other byte is kept."""
        if not self.hosts(item) or not item.subentities:
            return text

        def retag(tag: str) -> str | None:
            name = tag.removeprefix(markers.PREFIX)
            stale = self.stale.get(item.id)
            if stale is not None and name in (stale, f"{stale}:end"):
                return markers.PREFIX + self.plural + name.removeprefix(stale)
            found = self.block.fullmatch(name)
            if found is None:
                return None
            local = self._renamed(item.id, found.group(1))
            return f"{markers.PREFIX}{self.new}:{local}{found.group(2)}"

        text = sections.retag_markers(text, retag)
        for entry in item.subentities:
            renamed = self._renamed(item.id, entry.local_id)
            if renamed != entry.local_id:
                text = _with_heading_id(text, self.new, entry.local_id, renamed)
        return text


def _with_heading_id(text: str, kind: str, old_id: str, new_id: str) -> str:
    """*text* with the ``### <id>`` heading under the block ``<kind>:<new_id>`` carrying *new_id*
    in place of *old_id*; the rest of the heading line is kept."""
    opener = markers.open_marker(f"{kind}:{new_id}")
    start = text.find(opener)
    if start == -1:
        return text
    heading = re.compile(rf"(###[ \t]*){re.escape(old_id)}(?![\w])")
    found = heading.search(text, start + len(opener))
    if found is None:
        return text
    return text[: found.start()] + found.group(1) + new_id + text[found.end() :]


def _with_rename_kind_comment(text: str, old: str, new: str) -> str:
    """*text* with a system comment recording the kind rename appended to its discussion."""
    now_iso = clock.iso(clock.now())
    msg = f"kind spellings brought from {old} to {new}"
    entry = discussion.format_comment(now_iso, SYSTEM_SLUG, SYSTEM_SLUG, [msg])
    if sections.has_section(text, markers.DISCUSSION):
        return sections.append_to_section(text, markers.DISCUSSION, entry)
    return text
