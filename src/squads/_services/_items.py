"""Item lifecycle: status transitions, edits, links, regen, removal."""

from squads import _actor as actor
from squads import _clock as clock
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError, StatusNotInWorkflowError
from squads._index._resolver import item_file, require_item
from squads._interactions import is_system_skill
from squads._itemfile import update_frontmatter
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, format_item_id, ref_id_matches, split_ref
from squads._models._metadata import coerce_extra
from squads._roles._catalog import RoleDef
from squads._services._base import ServiceCore, reject_markers
from squads._services._results import RemoveResult
from squads._services._validators import ValidatorEngine
from squads._util import slugify
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL
from squads._workflow._models import Field


class ItemsMixin(ServiceCore):
    async def set_status(self, item_id: str, status: str, *, force: bool = False) -> Item:
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            old_status = item.status
            self._apply_status(item, status, force=force)
            item.updated_at = clock.now()
            item.modified_session, _ = actor.current_session()
            await update_frontmatter(item_file(self.paths, item), item)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "status",
                item.id,
                {"status": [old_status, item.status]},
            )
        return item

    async def update(  # noqa: PLR0913 — the one metadata entry point
        self,
        item_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        clear_priority: bool = False,
        add_labels: list[str] | None = None,
        rm_labels: list[str] | None = None,
        author: str | None = None,
        status: str | None = None,
        force: bool = False,
        parent: str | None = None,
        clear_parent: bool = False,
        set_extra: dict[str, str] | None = None,
        unset_extra: list[str] | None = None,
    ) -> Item:
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            delta: dict[str, object] = {}
            if title is not None and title != item.title:
                delta["title"] = [item.title, title]
                self._rename(db, item, title)
            if description is not None:
                delta["description"] = description
                item.description = description
            if assignee is not None:
                self._check_assignee(db, assignee or None)
                delta["assignee"] = assignee or None
                item.assignee = assignee or None
            if clear_priority:
                delta["priority"] = None
                item.priority = None
            elif priority is not None:
                delta["priority"] = priority
                item.priority = priority
            if author is not None:
                self._check_author(db, item.type, author, item.slug)
                delta["author"] = author
                item.author = author
            if status is not None:
                old_st = item.status
                self._apply_status(item, status, force=force)
                delta["status"] = [old_st, item.status]
            if clear_parent:
                delta["parent"] = None
                item.parent = None
            elif parent is not None:
                self._check_parent(db, item.type, parent)
                delta["parent"] = parent
                item.parent = parent
            self._apply_labels(item, add_labels, rm_labels)
            self._apply_extra(item, set_extra, unset_extra)
            item.updated_at = clock.now()
            item.modified_session, _ = actor.current_session()
            # Fail-closed on the updated item's first error-level catalog violation — the
            # same engine `sq check` reports (a warn-level catalog issue never aborts here).
            ValidatorEngine(spec=self.spec).gate(item, db)
            await update_frontmatter(item_file(self.paths, item), item)
            self.store._log("update", item.id, delta)  # pyright: ignore[reportPrivateUsage]
        if self.spec.item_is_roster(item.type) and item.type != ROSTER_OPERATOR:
            await self.regen(item.id)  # keep the .claude/ pointer in sync with edited config
        return item

    @staticmethod
    def _apply_labels(item: Item, add: list[str] | None, rm: list[str] | None) -> None:
        for lbl in add or []:
            if lbl not in item.labels:
                item.labels.append(lbl)
        if rm:
            item.labels = [lab for lab in item.labels if lab not in rm]

    def _apply_extra(
        self, item: Item, set_extra: dict[str, str] | None, unset: list[str] | None
    ) -> None:
        for key, raw in (set_extra or {}).items():
            field = self._badge_field(item.type, key)
            if field is not None:
                item.set_badge_value(field.code, self._parse_badge_code(field, raw))
            else:
                item.extra[key] = coerce_extra(
                    item.type, key, raw, self.spec.item_extra_fields(item.type)
                )
        for key in unset or []:
            field = self._badge_field(item.type, key)
            if field is not None:
                item.set_badge_value(field.code, None)
            else:
                item.extra.pop(key, None)

    def _badge_field(self, item_type: str, key: str) -> Field | None:
        """The declared field for *key* on *item_type*, generic over every axis (``--set
        <field>=<code>``): priority/severity/a project's own custom axis alike — not a
        hand-maintained allowlist of attribute-backed codes."""
        return next((f for f in self.spec.fields_for(item_type) if f.code == key), None)

    def _parse_badge_code(self, field: Field, raw: str) -> str:
        """Validate/normalize a ``--set <field>=<code>`` value against its bound collection."""
        coll = self.spec.collection(field.collection)
        code = raw.strip().lower()
        if code not in coll.badge_codes:
            choices = ", ".join(b.code for b in coll.badges)
            raise SquadsError(f"invalid {field.code} {raw!r} (one of: {choices})")
        return code

    def _apply_status(self, item: Item, status: str, *, force: bool) -> None:
        # Defensive str() — status is spec vocabulary (a plain string), no enum involved.
        status = str(status)
        states = self.spec.workflow_for(item.type).states
        if status not in states:
            allowed = ", ".join(sorted(states))
            raise StatusNotInWorkflowError(
                f"'{status}' is not a valid status for {item.type} (allowed: {allowed})"
            )
        if (
            not force
            and item.status != status
            and not self.spec.can_transition(item.type, item.status, status)
        ):
            raise InvalidTransitionError(
                f"{item.type} cannot move {item.status} → {status} (use --force to override)"
            )
        item.status = status

    def _rename(self, db: SquadsDB, item: Item, new_title: str) -> None:
        new_slug = slugify(new_title)
        old_path = item_file(self.paths, item)
        # Filename stem must stay padded even though item.id is unpadded — format it
        # explicitly from the sequence number, never by concatenating item.id.
        new_stem = format_item_id(item.prefix, item.sequence_id, db.padding)
        new_rel = self.paths.squad_relative(item.type, f"{new_stem}-{new_slug}.md", spec=self.spec)
        new_path = self.paths.abspath(new_rel)
        if old_path.exists() and old_path != new_path:
            old_path.rename(new_path)
        item.title = new_title
        item.slug = new_slug
        item.path = new_rel

    async def link(self, child_id: str, parent_id: str) -> Item:
        async with self.store.transaction() as db:
            child = require_item(db, child_id)
            old_parent = child.parent
            self._check_parent(db, child.type, parent_id)
            child.parent = parent_id
            child.updated_at = clock.now()
            child.modified_session, _ = actor.current_session()
            # Fail-closed on the reparented child's first error-level catalog violation
            # (parent type-eligibility, in particular) — the same engine every other
            # create/update site gates through.
            ValidatorEngine(spec=self.spec).gate(child, db)
            await update_frontmatter(item_file(self.paths, child), child)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "link",
                child.id,
                {"parent": [old_parent, parent_id]},
            )
        return child

    async def unlink(self, child_id: str) -> Item:
        async with self.store.transaction() as db:
            child = require_item(db, child_id)
            old_parent = child.parent
            child.parent = None
            child.updated_at = clock.now()
            child.modified_session, _ = actor.current_session()
            await update_frontmatter(item_file(self.paths, child), child)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "link",
                child.id,
                {"parent": [old_parent, None]},
            )
        return child

    async def regen(self, item_id: str) -> Item:
        """Regenerate the backend pointer for a role or skill from its current item data."""
        item = await self.get(item_id)
        ctx = self._ctx
        if item.type == ROSTER_ROLE:
            for backend in self._backends():
                await backend.generate_role_entry(ctx, item, RoleDef.from_extra(item.extra))
        elif item.type == ROSTER_SKILL:
            for backend in self._backends():
                await backend.generate_skill_entry(ctx, item)
        else:
            raise SquadsError(f"{item_id} is a {item.type}; only roles/skills have entries")
        return item

    async def set_body(self, item_id: str, body: str, *, append: bool = False) -> Item:
        """Set (or ``--append`` to) an item's top-level ``:body`` region — no manual editing.

        The body is free-form markdown the agent owns; ``description`` stays a short frontmatter
        summary. Role bodies are generated from their fields, so they're rejected here — and so
        is a system (template-owned) skill's body, since ``sq sync`` regenerates it. A *custom*
        (author-defined) skill is the one roster-type exception: its body is authored content with
        no regeneration path, so it's admitted.
        """
        reject_markers(body)

        def mutate(text: str, item: Item) -> str:
            if item.type == ROSTER_SKILL:
                slug = item.extra.get(X.SLUG, item.slug)
                if is_system_skill(slug, self.spec):
                    raise SquadsError(
                        f"{item_id} is a system skill; its body is regenerated by `sq sync`"
                        " (authoring it would be silently discarded)"
                    )
            elif self.spec.item_is_roster(item.type) and item.type != ROSTER_OPERATOR:
                raise SquadsError(
                    f"{item_id} is a {item.type}; its body is generated from its fields"
                    " (edit via `sq update --set …` / `sq sync`)"
                )
            new_body = body
            if append:
                current = (sections.get_section(text, markers.BODY) or "").strip("\n")
                if current:
                    new_body = f"{current}\n\n{body}"
            self.store._log("body", item.id, {})  # pyright: ignore[reportPrivateUsage]
            return sections.replace_section(text, markers.BODY, new_body)

        return await self._locked_section_edit(item_id, mutate)

    async def read_body(self, item_id: str) -> str:
        """The item's top-level ``:body`` region content (for ``sq show``) — read on a thread."""
        from squads import _aio

        item = await self.get(item_id)
        text = await _aio.read_text(item_file(self.paths, item))
        return (sections.get_section(text, markers.BODY) or "").strip("\n")

    async def read_discussion(self, item_id: str) -> str:
        """The item's top-level ``:discussion`` region content (for ``sq show --comments``)."""
        from squads import _aio

        item = await self.get(item_id)
        text = await _aio.read_text(item_file(self.paths, item))
        return (sections.get_section(text, markers.DISCUSSION) or "").strip("\n")

    async def remove_item(self, item_id: str, *, purge: bool = False) -> Item:
        """Remove an agent-type item (role/skill/operator) from the index.

        For **work items** (feature/task/bug/decision/review/epic/guide), use
        :meth:`remove_work_item` instead — it enforces ref/child safety, always unlinks the
        ``.md``, and carries the reflog op stub.
        """
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            del db.items[item.sequence_id]
        if self.spec.item_is_roster(item.type) and item.type != ROSTER_OPERATOR:
            ctx = self._ctx
            for backend in self._backends():
                await backend.remove_artifacts(ctx, item)
        if purge:
            item_file(self.paths, item).unlink(missing_ok=True)
        return item

    async def remove_work_item(
        self,
        item_id: str,
        *,
        force: bool = False,
    ) -> RemoveResult:
        """Hard-delete a work item: unlink the ``.md`` and drop its index entry atomically.

        **Safety checks** (performed inside the transaction):

        - Refuses when the item has children (items whose ``parent`` == *item_id*), even with
          ``--force``.  Children must be re-parented or removed first.
        - Refuses when the item has incoming refs **and** ``force`` is False; lists every
          referrer so the operator can act.
        - When ``force`` is True, severs every incoming ref by removing the matching forward-
          edge entry from each referrer's frontmatter, inside the **same transaction**.

        **Counter invariant:** ``db.counter`` is **never modified** here.  A freed sequence
        number is a sanctioned gap — it is never reissued.

        **Reflog:** the op identity (``op=remove``) and gone-item snapshot are assembled
        here and appended post-commit via ``store._log()`` inside the transaction.
        """
        async with self.store.transaction() as db:
            item = require_item(db, item_id)

            # ------------------------------------------------------------------
            # 1. Children check — refuse regardless of --force
            # ------------------------------------------------------------------
            child_ids = db.children(item.id)
            if child_ids:
                listed = ", ".join(child_ids)
                raise SquadsError(
                    f"cannot remove {item.id}: it has child items: {listed}. "
                    "Re-parent or remove each child first."
                )

            # ------------------------------------------------------------------
            # 2. Incoming refs check
            # ------------------------------------------------------------------
            referrer_ids = db.backrefs(item.id)
            if referrer_ids and not force:
                listed = ", ".join(referrer_ids)
                raise SquadsError(
                    f"cannot remove {item.id}: it is referenced by: {listed}. "
                    "Re-parent/remove those items first, or re-run with --force to sever refs."
                )

            # ------------------------------------------------------------------
            # 3. Sever incoming refs from referrers' frontmatter (--force path)
            # ------------------------------------------------------------------
            severed: list[str] = []
            if force and referrer_ids:
                target_prefix = effective_prefix(item.prefix)
                target_seq = item.sequence_id
                for ref_id in referrer_ids:
                    referrer = db.get(ref_id)
                    if referrer is None:
                        continue
                    referrer.refs = [
                        r
                        for r in referrer.refs
                        if not ref_id_matches(split_ref(r)[0], target_prefix, target_seq)
                    ]
                    referrer.updated_at = clock.now()
                    await update_frontmatter(item_file(self.paths, referrer), referrer)
                    severed.append(ref_id)

            # ------------------------------------------------------------------
            # 4. Hard-delete: drop index entry + unlink the .md
            # ------------------------------------------------------------------
            path = item_file(self.paths, item)
            # Unlink BEFORE the index commit so the safe failure direction is preserved:
            # a crash here leaves the file gone with the index still referencing it —
            # sq repair drops the orphan entry.  The reverse (index-gone / file-survives)
            # would let sq repair resurrect the removed item.
            path.unlink(missing_ok=True)
            del db.items[item.sequence_id]
            # counter is intentionally NOT modified — the gap is sanctioned.

            # Reflog: op=remove + gone-item snapshot.
            # Appended AFTER os.replace by the store's transaction machinery.
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "remove",
                item.id,
                {
                    "type": item.type,
                    "title": item.title,
                    "status": item.status,
                    "severed_refs": severed,
                },
            )

        return RemoveResult(removed_id=item.id, severed_refs=severed)
