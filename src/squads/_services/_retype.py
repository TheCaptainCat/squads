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
from squads._models._item import Item, format_item_id, make_ref, split_ref
from squads._models._vocab import prefix_for
from squads._paths import SquadPaths
from squads._services._base import ServiceCore, subentity_container_map, subentity_kind_map
from squads._services._results import RetypeResult
from squads._services._validators import ValidatorEngine
from squads._workflow._models import WorkflowSpec

# Bundled sub-entity container headings — an explicit lookup because "User Stories" isn't
# derivable from `plural` ("stories".title() == "Stories", not "User Stories"); a custom kind
# falls back to its `plural` title-cased instead (see _container_heading).
_BUNDLED_CONTAINER_HEADINGS: dict[str, str] = {
    "story": "User Stories",
    "subtask": "Subtasks",
    "finding": "Findings",
}


def _container_heading(spec: WorkflowSpec, kind: str) -> str:
    """The container heading for *kind*: the bundled literal for a built-in kind, else its
    declared ``plural`` title-cased (e.g. ``"actions"`` -> ``"Actions"``)."""
    return _BUNDLED_CONTAINER_HEADINGS.get(kind) or spec.subentity_kinds[kind].plural.title()


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
        # Deliberately overlaps the `parent_in` validator the later `ValidatorEngine.gate()`
        # call runs on the prospective item (same `spec.parent_allowed(new_type, ...)` verdict)
        # — kept because this branch has the old_id/current-parent context to raise the more
        # actionable retype-specific message; the gate's own message is the generic per-item
        # one shared with create/update and would be a worse error here. Not re-encoded logic:
        # same predicate, message-quality duplication only.
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

        - Both the current type and *new_type* must be non-roster types
          (``spec.non_roster_types()``).
        - Refuses (actionable :class:`~squads._errors.SquadsError`) when the item has
          sub-entities, when the existing parent would be invalid for the new type, when any
          current child would become invalid under the new type, or when the new type's own
          category rules (e.g. the records bundle's ``no_parent``) reject the item as it would
          look post-change — enforced by the same
          :class:`~squads._services._validators.ValidatorEngine` gate create/update use.
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

            # Post-change conformance: gate the item as it would look right after the retype
            # (new type/status/prefix, same parent) through the same per-item validator engine
            # create/update use — so a category rule like the records bundle's `no_parent`
            # fails closed here, before any file is touched, rather than being re-encoded as a
            # bespoke retype-only check.
            prospective = item.model_copy(
                update={
                    "type": new_type,
                    "status": new_status,
                    "prefix": prefix_for(new_type, self.spec),
                }
            )
            ValidatorEngine(spec=self.spec).gate(prospective, db)

            new_path = await _apply_type_change(
                self.paths, self.spec, db, item, new_type, carry_status=not status_reset
            )
            new_id = item.id  # @computed_field formats from item.prefix (now correct); unpadded

            # Rewrite all incoming edges (refs, parent links, prose mentions). A single-pair
            # remap here — the bulk rename path builds one combined {old:new} across every
            # renamed item and drives the same two calls once instead of once per item.
            remap = {old_id: new_id}
            all_paths = [
                item_file(self.paths, it)
                for it in db.items.values()
                if it.sequence_id != item.sequence_id
            ]
            all_paths.append(new_path)
            touched = await rewrite_ids(all_paths, remap)

            # Re-sync in-memory items
            _resync_edges(db, remap, exclude={item.sequence_id})

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


async def _apply_type_change(
    paths: SquadPaths,
    spec: WorkflowSpec,
    db: SquadsDB,
    item: Item,
    new_type: str,
    *,
    carry_status: bool,
) -> Path:
    """Mutate *item* in place for a type change: new prefix/id, moved file, frontmatter,
    status, and sub-entity container. Body bytes stay verbatim.

    This is the per-item self-rewrite core shared by ``retype()`` (which resolves
    *carry_status* itself, via :func:`_carry_or_reset_status`) and the bulk rename path
    (which always passes ``carry_status=True``). It does *not* touch other items' edges —
    that is the separate, batchable pass in :func:`~squads._itemfile.rewrite_ids` /
    :func:`_resync_edges`, so a bulk caller can run it once across every renamed item
    instead of once per item. Returns the new file path.
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
    await update_frontmatter(new_path, item)

    # Append sub-entity container if the new type hosts one and it is absent
    await _ensure_subentity_container(spec, new_type, new_path)
    return new_path


async def _ensure_subentity_container(spec: WorkflowSpec, new_type: str, path: Path) -> None:
    """Append an empty sub-entity container block when *new_type* hosts sub-entities."""
    kind = subentity_kind_map(spec).get(new_type)
    if kind is None:
        return
    container_tag = subentity_container_map(spec)[kind]
    text = await _aio.read_text(path)
    heading = _container_heading(spec, kind)
    text = discussion.ensure_container(text, heading, container_tag)
    await _aio.write_text(path, text)


def _resync_edges(db: SquadsDB, remap: dict[str, str], *, exclude: set[int]) -> None:
    """Update in-memory index entries whose parent or refs point at any old ID in *remap*.

    Bulk-capable by construction: one pass over ``db.items`` applies every ``{old: new}``
    pair in *remap*, so a multi-item rename resyncs edges once instead of once per renamed
    item. *exclude* holds the sequence IDs of the items being changed themselves (already
    self-consistent via :func:`_apply_type_change`).
    """
    for other in db.items.values():
        if other.sequence_id in exclude:
            continue
        if other.parent in remap:
            other.parent = remap[other.parent]
        other.refs = [_remap_ref(r, remap) for r in other.refs]


def _remap_ref(ref: str, remap: dict[str, str]) -> str:
    """Rewrite a single ``"ID"``/``"ID:kind"`` ref if its ID is a key of *remap*."""
    rid, kind = split_ref(ref)
    return make_ref(remap[rid], kind) if rid in remap else ref


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
