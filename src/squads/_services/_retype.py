"""Retype an item in place: flip its type, move its file, carry/reset status, rewrite edges.

The operation runs inside a single index transaction so the rename, frontmatter update, and all
incoming-edge rewrites are atomic from the store's perspective.  The retyped file's new text is
composed in memory and written once; body bytes are left verbatim apart from the id remap.
"""

from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import ensure_no_skew, remap_ids_text, rewrite_ids, write_text
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import Item, format_item_id, make_ref, split_ref
from squads._models._participants import SYSTEM_SLUG
from squads._models._vocab import prefix_for
from squads._paths import SquadPaths
from squads._sections import replace_frontmatter
from squads._services._base import ServiceCore, ensure_subentity_container_text
from squads._services._results import RetypeResult
from squads._services._validators import ValidatorEngine
from squads._workflow._models import WorkflowSpec


def _validate_work_types(spec: WorkflowSpec, old_type: str, new_type: str, old_id: str) -> None:
    """Raise if either type is not a non-roster (work or records) type, or they are the same."""
    wt = spec.non_roster_types()
    if old_type not in wt:
        raise SquadsError(
            f"{old_id} is a {old_type}; only work/records items can be retyped "
            f"({', '.join(sorted(wt))})"
        )
    if new_type not in wt:
        raise SquadsError(
            f"cannot retype to {new_type!r}; target must be a work or records type "
            f"({', '.join(sorted(wt))})"
        )
    if new_type == old_type:
        raise SquadsError(f"{old_id} is already of type {old_type}")


def _validate_refusals(
    spec: WorkflowSpec,
    db: SquadsDB,
    old_id: str,
    new_type: str,
    item_parent: str | None,
    has_subentities: bool,
) -> None:
    """Check and raise the three actionable refusal cases."""
    if has_subentities:
        raise SquadsError(
            f"cannot retype {old_id}: it has sub-entities. "
            "Clear or move all sub-entities first, then retype."
        )
    if item_parent:
        # Overlaps the later `parent_in` gate (same `spec.parent_allowed` verdict) on purpose:
        # this branch has the old_id/current-parent context for a more actionable retype-specific
        # message.
        parent_item = db.get(item_parent)
        if parent_item is not None and not spec.parent_allowed(new_type, parent_item.type):
            raise SquadsError(
                f"cannot retype {old_id} to {new_type}: "
                f"{spec.parent_hint(new_type)} "
                f"(current parent {item_parent} is a {parent_item.type}). "
                "Remove or update the parent first."
            )
    invalid_children = [
        c
        for c in db.items.values()
        if c.parent == old_id and not spec.parent_allowed(c.type, new_type)
    ]
    if invalid_children:
        ids = ", ".join(c.id for c in invalid_children)
        raise SquadsError(
            f"cannot retype {old_id} to {new_type}: "
            f"child item(s) {ids} would have an invalid parent type. "
            "Re-parent or remove those children first."
        )


def _carry_or_reset_status(
    spec: WorkflowSpec,
    old_type: str,
    new_type: str,
    current_status: str,
) -> tuple[bool, str]:
    """Return ``(status_reset, new_status_or_same)``.

    Carries the status when old and new share the same :class:`~squads._workflow._models.Workflow`
    (same transitions/initial) **and** the current status is valid in the new workflow.
    """
    old_wf = spec.workflow_for(old_type)
    new_wf = spec.workflow_for(new_type)
    if old_wf == new_wf and current_status in new_wf.states:
        return False, current_status
    return True, spec.initial_status(new_type)


class RetypeMixin(ServiceCore):
    async def retype(self, item_id: str, new_type: str) -> RetypeResult:
        """Reclassify *item_id* to *new_type* in place. Both must be non-roster types, and it
        refuses an item with sub-entities, a parent or child invalid for the new type, or a result
        the :class:`~squads._services._validators.ValidatorEngine` gate rejects. Status is carried
        when both types share a workflow and it is a state of the new one, else reset to the
        initial status. Incoming edges are rewritten via :func:`~squads._itemfile.rewrite_ids` and a
        system comment is appended.
        """
        new_type = str(new_type)  # coerce StrEnum members to plain str
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            # The rewrite below touches every file that mentions this id, so no duplicated id
            # anywhere may be in play.
            await self._refuse_any_duplicated_id()
            old_type = item.type
            old_id = item.id
            old_status = item.status

            _validate_work_types(self.spec, old_type, new_type, old_id)
            _validate_refusals(self.spec, db, old_id, new_type, item.parent, bool(item.subentities))

            status_reset, new_status = _carry_or_reset_status(
                self.spec, old_type, new_type, old_status
            )

            # Gate the item as it would look after the retype through the per-item validator
            # engine, so category rules (e.g. `no_parent`) fail closed before any file is touched.
            prospective = item.model_copy(
                update={
                    "type": new_type,
                    "status": new_status,
                    "prefix": prefix_for(new_type, self.spec),
                }
            )
            ValidatorEngine(spec=self.spec, playbook=self.playbook, paths=self.paths).gate(
                prospective, db
            )

            # Check the skew before any file moves: apply_type_change renames the file first, so a
            # later refusal would leave the new filename holding old, skewed frontmatter.
            default_kind = self.spec.default_ref_kind()
            base = item.model_copy(deep=True)
            current_text = await self._read_item_file(item, item_file(self.paths, item))
            ensure_no_skew(current_text, base, default_kind=default_kind)

            new_path, text = await apply_type_change(
                self.paths,
                self.spec,
                db,
                item,
                new_type,
                carry_status=not status_reset,
                text=current_text,
            )
            text = self._rescaffolded_body(text, item, base)
            new_id = item.id  # @computed_field formats from item.prefix (now correct); unpadded

            # Rewrite all incoming edges with a single-pair remap (rename builds one combined
            # remap). The retyped file's own text is remapped in memory and written once, below.
            remap = {old_id: new_id}
            remapped = remap_ids_text(text, remap)
            await write_text(
                new_path, _with_retype_comment(remapped, old_id, new_id, status_reset, item)
            )
            other_paths = [
                item_file(self.paths, it)
                for it in db.items.values()
                if it.sequence_id != item.sequence_id
            ]
            touched = await rewrite_ids(other_paths, remap)
            if remapped != text:
                touched.append(new_path)

            # Re-sync in-memory items
            resync_edges(db, remap, exclude={item.sequence_id})

            # Update the index entry
            db.add(item)

            rewritten_names = [str(p.relative_to(self.paths.squad_dir)) for p in touched]

            # Reflog: op=retype captures old→new id/type and status outcome.
            # Appended AFTER os.replace by the store's transaction machinery.
            self.store.log(
                "retype",
                new_id,
                {
                    "old_id": old_id,
                    "new_id": new_id,
                    "old_type": old_type,
                    "new_type": new_type,
                    "status_carried": not status_reset,
                    "status": item.status,
                },
            )

        return RetypeResult(
            item=item,
            old_id=old_id,
            old_type=old_type,
            status_reset=status_reset,
            old_status=old_status,
            rewritten=rewritten_names,
        )


async def apply_type_change(
    paths: SquadPaths,
    spec: WorkflowSpec,
    db: SquadsDB,
    item: Item,
    new_type: str,
    *,
    carry_status: bool,
    text: str,
) -> tuple[Path, str]:
    """Mutate *item* in place for a type change (new prefix/id, moved file, status) and return the
    new path and text, composed from *text* (skew-checked) with body bytes verbatim; the caller
    writes it once. Shared by ``retype()`` and the bulk rename, other items' edges being
    :func:`resync_edges`'s. The file moves before the text is written, so a crash between leaves old
    frontmatter at the new path until ``sq repair``: the permitted markdown-ahead outcome.
    """
    old_path = item_file(paths, item)
    if not carry_status:
        item.status = spec.initial_status(new_type)
    # Stamp the new prefix from the spec before reading item.id so the computed field
    # formats from the correct prefix.
    item.type = new_type
    item.prefix = prefix_for(new_type, spec)
    # Filename stem must stay padded even though item.id is unpadded — format it explicitly
    # from the sequence number, never by concatenating item.id.
    new_stem = format_item_id(item.prefix, item.sequence_id, db.padding)
    new_rel = paths.squad_relative(new_type, f"{new_stem}-{item.slug}.md", spec=spec)
    new_path = paths.abspath(new_rel)
    await _aio.mkdir(new_path.parent, parents=True, exist_ok=True)
    await _aio.path_rename(old_path, new_path)
    item.path = new_rel
    item.updated_at = clock.now()
    composed = replace_frontmatter(text, item.to_frontmatter_dict(), source=str(new_path))
    return new_path, ensure_subentity_container_text(spec, new_type, composed)


def resync_edges(db: SquadsDB, remap: dict[str, str], *, exclude: set[int]) -> None:
    """Update in-memory index entries whose parent, refs or sub-entity ``deferred_to`` point at any
    old ID in *remap*, in one pass. *exclude* holds the sequence IDs of the items being changed
    themselves.
    """
    for other in db.items.values():
        if other.sequence_id in exclude:
            continue
        if other.parent in remap:
            other.parent = remap[other.parent]
        other.refs = [_remap_ref(r, remap) for r in other.refs]
        for sub in other.subentities:
            if sub.deferred_to in remap:
                sub.deferred_to = remap[sub.deferred_to]


def _remap_ref(ref: str, remap: dict[str, str]) -> str:
    """Rewrite a single ``"ID"``/``"ID:kind"`` ref if its ID is a key of *remap*."""
    rid, kind = split_ref(ref)
    return make_ref(remap[rid], kind) if rid in remap else ref


def _with_retype_comment(
    text: str, old_id: str, new_id: str, status_reset: bool, item: Item
) -> str:
    """*text* with a system comment recording the retype appended to its discussion."""
    now_iso = clock.iso(clock.now())
    if status_reset:
        status_note = f"status reset to {item.status} (workflows differ)"
    else:
        status_note = f"status carried as {item.status}"
    msg = f"retyped {old_id} → {new_id}; {status_note}"
    entry = discussion.format_comment(now_iso, SYSTEM_SLUG, SYSTEM_SLUG, [msg])
    if sections.has_section(text, markers.DISCUSSION):
        return sections.append_to_section(text, markers.DISCUSSION, entry)
    return text
