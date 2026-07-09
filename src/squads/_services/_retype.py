"""Retype an item in place: flip its type, move its file, carry/reset status, rewrite edges.

The operation runs inside a single index transaction so the rename, frontmatter update, and all
incoming-edge rewrites are atomic from the store's perspective.  Body bytes are left verbatim;
only the frontmatter is rewritten via ``update_frontmatter``.
"""

from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import rewrite_ids, update_frontmatter
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import Item, format_item_id
from squads._models._vocab import prefix_for
from squads._services._base import ServiceCore, subentity_container_map, subentity_kind_map
from squads._services._results import RetypeResult
from squads._workflow._models import WorkflowSpec

# Sub-entity container headings for each kind that has one.
_CONTAINER_HEADINGS: dict[str, str] = {
    "story": "User Stories",
    "subtask": "Subtasks",
    "finding": "Findings",
}


def _validate_work_types(spec: WorkflowSpec, old_type: str, new_type: str, old_id: str) -> None:
    """Raise if either type is not a work type, or they are the same."""
    wt = spec.work_types()
    if old_type not in wt:
        raise SquadsError(
            f"{old_id} is a {old_type}; only work items can be retyped ({', '.join(sorted(wt))})"
        )
    if new_type not in wt:
        raise SquadsError(
            f"cannot retype to {new_type!r}; target must be a work type ({', '.join(sorted(wt))})"
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

    Carries the status when old and new share the same :class:`~squads._workflow.Workflow`
    (same transitions/initial) **and** the current status is valid in the new workflow.
    """
    old_wf = spec.workflow_for(old_type)
    new_wf = spec.workflow_for(new_type)
    if old_wf == new_wf and current_status in new_wf.states:
        return False, current_status
    return True, spec.initial_status(new_type)


class RetypeMixin(ServiceCore):
    async def retype(self, item_id: str, new_type: str) -> RetypeResult:
        """Reclassify *item_id* to *new_type* in place.

        - Both the current type and *new_type* must be non-meta work types (``spec.work_types()``).
        - Refuses (actionable :class:`~squads._errors.SquadsError`) when the item has
          sub-entities, when the existing parent would be invalid for the new type, or when
          any current child would become invalid under the new type.
        - Status is carried when old and new share the same :class:`~squads._workflow.Workflow`
          object **and** the current status is a valid state of the new workflow; otherwise the
          status is reset to the new type's initial status.
        - All incoming edges (other items' ``refs``, children's ``parent``, and prose
          ``@``/ID mentions) are rewritten to the new ID via
          :func:`~squads._itemfile.rewrite_ids`.
        - A system comment recording the retype is appended to the item's discussion.
        """
        new_type = str(new_type)  # coerce StrEnum members to plain str
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            old_type = item.type
            old_id = item.id
            old_status = item.status

            _validate_work_types(self.spec, old_type, new_type, old_id)
            _validate_refusals(self.spec, db, old_id, new_type, item.parent, bool(item.subentities))

            status_reset, new_status = _carry_or_reset_status(
                self.spec, old_type, new_type, old_status
            )
            if status_reset:
                item.status = new_status

            # Flip type + move file (body bytes verbatim).
            # Stamp the new prefix from the spec before reading item.id so the computed
            # field formats from the correct prefix.
            old_path = item_file(self.paths, item)
            item.type = new_type
            item.prefix = prefix_for(new_type, self.spec)
            new_id = item.id  # @computed_field formats from item.prefix (now correct); unpadded
            # Filename stem must stay padded even though new_id (item.id) is unpadded —
            # format it explicitly from the sequence number, never by concatenating item.id.
            new_stem = format_item_id(item.prefix, item.sequence_id, db.padding)
            new_rel = self.paths.squad_relative(
                new_type, f"{new_stem}-{item.slug}.md", spec=self.spec
            )
            new_path = self.paths.abspath(new_rel)
            await _aio.mkdir(new_path.parent, parents=True, exist_ok=True)
            await _aio.path_rename(old_path, new_path)
            item.path = new_rel
            item.updated_at = clock.now()
            await update_frontmatter(new_path, item)

            # Append sub-entity container if the new type hosts one and it is absent
            await _ensure_subentity_container(self.spec, new_type, new_path)

            # Rewrite all incoming edges (refs, parent links, prose mentions)
            all_paths = [
                item_file(self.paths, it)
                for it in db.items.values()
                if it.sequence_id != item.sequence_id
            ]
            all_paths.append(new_path)
            touched = await rewrite_ids(all_paths, {old_id: new_id})

            # Re-sync in-memory items
            _resync_edges(db, item.sequence_id, old_id, new_id)

            # Update the index entry
            db.add(item)

            # Append system comment
            await _append_retype_comment(new_path, old_id, new_id, status_reset, item)

            rewritten_names = [str(p.relative_to(self.paths.squad_dir)) for p in touched]

            # Reflog: op=retype captures old→new id/type and status outcome.
            # Appended AFTER os.replace by the store's transaction machinery.
            self.store._log(  # pyright: ignore[reportPrivateUsage]
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


async def _ensure_subentity_container(spec: WorkflowSpec, new_type: str, path: Path) -> None:
    """Append an empty sub-entity container block when *new_type* hosts sub-entities."""
    kind = subentity_kind_map(spec).get(new_type)
    if kind is None:
        return
    container_tag = subentity_container_map(spec)[kind]
    text = await _aio.read_text(path)
    heading = _CONTAINER_HEADINGS[kind]
    text = discussion.ensure_container(text, heading, container_tag)
    await _aio.write_text(path, text)


def _resync_edges(db: SquadsDB, own_seq: int, old_id: str, new_id: str) -> None:
    """Update in-memory index entries whose parent or refs pointed at the old ID."""
    for other in db.items.values():
        if other.sequence_id == own_seq:
            continue
        if other.parent == old_id:
            other.parent = new_id
        other.refs = [
            (new_id + r[len(old_id) :] if r == old_id or r.startswith(old_id + ":") else r)
            for r in other.refs
        ]


async def _append_retype_comment(
    path: Path,
    old_id: str,
    new_id: str,
    status_reset: bool,
    item: Item,
) -> None:
    """Append a system comment recording the retype to the item's discussion."""
    now_iso = clock.iso(clock.now())
    if status_reset:
        status_note = f"status reset to {item.status} (workflows differ)"
    else:
        status_note = f"status carried as {item.status}"
    msg = f"retyped {old_id} → {new_id}; {status_note}"
    entry = discussion.format_comment(now_iso, "squads", [msg])
    text = await _aio.read_text(path)
    if sections.has_section(text, markers.DISCUSSION):
        text = sections.append_to_section(text, markers.DISCUSSION, entry)
        await _aio.write_text(path, text)
