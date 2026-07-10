"""Bulk-rename every item of one type to another, in a single transaction.

A rename is a **vocabulary** change (same semantic type, new label/prefix), not a
reclassification: unlike :mod:`squads._services._retype`, sub-entities carry over unchanged
and status always carries over. It reuses ``_retype.py``'s per-item primitive
(``_apply_type_change``) and edge-resync primitive (``_resync_edges``) under its own
validation, batching both the id-rewrite and the edge-resync into one pass across every
renamed item instead of once per item.
"""

from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._itemfile import rewrite_ids
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._paths import SquadPaths
from squads._services._base import ServiceCore
from squads._services._results import RenameResult
from squads._services._retype import (
    _apply_type_change,  # pyright: ignore[reportPrivateUsage]
    _resync_edges,  # pyright: ignore[reportPrivateUsage]
)
from squads._workflow._models import WorkflowSpec


def _validate_rename_types(spec: WorkflowSpec, old_type: str, new_type: str) -> None:
    """Raise unless both types are declared, non-meta work types, and distinct."""
    for t in (old_type, new_type):
        if t not in spec.items:
            raise SquadsError(f"{t!r} is not declared in the active spec")
        if spec.item_is_meta(t):
            raise SquadsError(
                f"{t!r} is a reserved meta-type (role/skill/operator) and cannot be renamed"
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


async def _snapshot_files(paths: SquadPaths, db: SquadsDB) -> dict[int, tuple[Path, str]]:
    """Read every item's current (path, text) before any mutation.

    The index's own atomicity comes for free from ``IndexStore.transaction()`` (nothing is
    written until the body returns normally) — but ``_apply_type_change``/``rewrite_ids``
    write ``.md`` files eagerly, ahead of that commit. This snapshot is what lets a mid-flight
    failure restore the filesystem, not just the index, to exactly its pre-call state.
    """
    snap: dict[int, tuple[Path, str]] = {}
    for it in db.items.values():
        p = item_file(paths, it)
        snap[it.sequence_id] = (p, await _aio.read_text(p))
    return snap


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
        await _aio.write_text(orig_path, orig_text)


class RenameMixin(ServiceCore):
    async def rename_type(self, old_type: str, new_type: str) -> RenameResult:
        """Bulk-move every item of *old_type* to *new_type* in one transaction.

        - Both types must be declared, non-meta work types (``spec.work_types()``); *new_type*
          must already exist in the active spec — this call never declares it.
        - Refuses (actionable :class:`~squads._errors.SquadsError`) when any live child of a
          renamed item would become invalid under *new_type*.
        - Sub-entities carry over unchanged and status always carries over (``carry_status=True``
          on the shared per-item primitive) — deliberately unlike ``retype()``, which refuses on
          sub-entities and may reset status.
        - Every renamed item's id/file/frontmatter is rewritten first, then one combined
          ``{old_id: new_id}`` remap drives a single ``rewrite_ids`` pass across every file and
          a single edge resync, so the whole operation is O(N) rather than O(N²).
        - Each renamed item gets one reflog line (``op="rename-type"``) and one system comment,
          mirroring ``retype()``'s audit trail.

        A failure anywhere in the mutation phase — including mid-flight, after some items'
        files have already been moved/rewritten on disk — restores every squad file to its
        pre-call bytes and path before re-raising, so the index (never written until the
        transaction body returns) and the filesystem both end up untouched.
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
            try:
                # Per-item self-rewrite (id/prefix/file/frontmatter; status carried
                # unconditionally).
                pairs: list[tuple[str, Item]] = []
                remap: dict[str, str] = {}
                for item in old_items:
                    old_id = item.id
                    await _apply_type_change(
                        self.paths, self.spec, db, item, new_type, carry_status=True
                    )
                    remap[old_id] = item.id
                    pairs.append((old_id, item))

                # Single batched pass across every squad file (renamed items included — their
                # `item.path` already reflects the new location at this point).
                all_paths = [item_file(self.paths, it) for it in db.items.values()]
                touched = await rewrite_ids(all_paths, remap)

                # Not excluding the renamed items themselves: two renamed items of the same
                # old_type may ref each other, and that cross-reference needs remapping too
                # (retype's single-pair exclude is a no-op there since an item can't ref
                # itself; a multi-entry bulk remap has no such guarantee).
                _resync_edges(db, remap, exclude=set())

                ids: list[tuple[str, str]] = []
                for old_id, item in pairs:
                    db.add(item)
                    new_path = item_file(self.paths, item)
                    await _append_rename_comment(new_path, old_id, item.id, item)
                    self.store._log(  # pyright: ignore[reportPrivateUsage]
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
            except Exception:
                await _rollback_files(self.paths, db, snapshot)
                raise

            rewritten_names = [str(p.relative_to(self.paths.squad_dir)) for p in touched]

        return RenameResult(renamed=len(pairs), ids=ids, rewritten=rewritten_names)


async def _append_rename_comment(path: Path, old_id: str, new_id: str, item: Item) -> None:
    """Append a system comment recording the rename to the item's discussion."""
    now_iso = clock.iso(clock.now())
    msg = f"renamed {old_id} → {new_id}; status carried as {item.status}"
    entry = discussion.format_comment(now_iso, "squads", [msg])
    text = await _aio.read_text(path)
    if sections.has_section(text, markers.DISCUSSION):
        text = sections.append_to_section(text, markers.DISCUSSION, entry)
        await _aio.write_text(path, text)
