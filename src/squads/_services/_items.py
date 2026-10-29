"""Item lifecycle: status transitions, edits, links, regen, removal."""

import dataclasses
from collections.abc import Callable
from datetime import datetime
from functools import cache
from pathlib import Path

from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads import _view_tags as view_tags
from squads import _views as views
from squads._errors import InvalidTransitionError, SquadsError, StatusNotInWorkflowError
from squads._index._resolver import item_file, require_item
from squads._itemfile import ensure_no_skew
from squads._models import _markers as markers
from squads._models._attributes import AttributeKey, parse_invocable_choice
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, format_item_id, ref_id_matches, split_ref
from squads._models._metadata import coerce_attribute, require_settable
from squads._paths import number_for_id
from squads._pronouns import checked_pronouns
from squads._roles._catalog import RoleDef
from squads._roles._resolver import model_problem, resolve_role_for_item
from squads._services import _retirement as retirement
from squads._services._base import (
    ServiceCore,
    reject_body_overwrite,
    reject_non_view_markers,
    require_title,
)
from squads._services._results import RemoveResult, RosterRemoval, RosterStatusResult
from squads._services._validators import ValidatorEngine
from squads._transform import TransformData
from squads._util import slugify
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL, bundled_spec


class ItemsMixin(ServiceCore):
    async def set_status(self, item_id: str, status: str, *, force: bool = False) -> Item:
        """Open a transaction and delegate to :meth:`_set_status_core`, which the importer calls
        directly. A roster transition is projected into backend config after commit (the importer
        skips that, as replayed history converges on the next ``sq sync``) and held to the config-
        integrity clauses regardless of ``force``. It never passes ``--unlink``
        (:meth:`set_roster_status` does) and gets the same catalog gate as ``update --status``.
        """
        result = await self._set_roster_status_impl(item_id, status, force=force, unlink=False)
        return result.item

    async def set_roster_status(
        self, item_id: str, status: str, *, force: bool = False, unlink: bool = False
    ) -> RosterStatusResult:
        """The roster ``status`` verb's entry point: the same transition as :meth:`set_status`,
        plus ``--unlink`` and the richer result reporting it needs (severed edges, board-hygiene
        warnings)."""
        return await self._set_roster_status_impl(item_id, status, force=force, unlink=unlink)

    async def _set_roster_status_impl(
        self, item_id: str, status: str, *, force: bool, unlink: bool
    ) -> RosterStatusResult:
        async with self.store.transaction() as db:
            item, severed, warnings = await self._set_status_core(
                db, item_id, status, force=force, unlink=unlink
            )
        if self.spec.item_is_roster(item.type):
            await self.roster_projection.project_transition(item)
        # Post-commit partial resync for each severed preload edge, as unlink_role does: refresh
        # the previously-scoped role's cache and generated entry.
        preload_kind = self.spec.preload_ref_kind()
        for sev in severed:
            if sev.kind == preload_kind:
                role = await self.get(sev.target)
                await self.roster_projection.resync_role_skills(role.slug)
        return RosterStatusResult(item=item, severed=severed, warnings=warnings)

    def _set_status_model(
        self,
        db: SquadsDB,
        item_id: str,
        status: str,
        *,
        force: bool = False,
        unlink: bool = False,
        now: datetime | None = None,
    ) -> tuple[Item, str, Item, list[retirement.Severance], list[str]]:
        """The pure half of a status transition (no file I/O), returning ``(item, old_status, base,
        severed, warnings)``: *base* is the item as loaded for the skew guard, *severed* the
        ``--unlink`` edges removed, *warnings* non-blocking hygiene notices. A roster item is held
        to the config-integrity clauses on this delta regardless of ``force``. Shared with the
        importer's pre-pass, which runs it on a throwaway index copy.
        """
        item = require_item(db, item_id)
        base = item.model_copy(deep=True)
        old_status = item.status
        self._apply_status(item, status, force=force)
        severed: list[retirement.Severance] = []
        warnings: list[str] = []
        if self.spec.item_is_roster(item.type):
            severed = retirement.enforce(
                self.spec,
                db,
                item,
                active_backends=self.paths.config.active_backends,
                unlink=unlink,
                old_status=old_status,
                playbook=self.playbook,
                squad_dir=self.paths.squad_dir,
                catalog=self.catalog,
            )
            live = self.spec.live_statuses(item.type)
            if old_status in live and item.status not in live:
                warnings = self._retirement_warnings(db, item)
        item.updated_at = now if now is not None else clock.now()
        item.modified_session, _ = actor.current_session()
        # Fail closed on the item's first error-level catalog violation, as `_update_model` does:
        # `status` is a shortcut for `update --status`, so both refuse the same states (a parent
        # cycle leaves the item unwritable until `--no-parent`). A warn-level issue never aborts.
        ValidatorEngine(spec=self.spec, playbook=self.playbook, paths=self.paths).gate(item, db)
        return item, old_status, base, severed, warnings

    def _retirement_warnings(self, db: SquadsDB, item: Item, *, purged: bool = False) -> list[str]:
        """The board-hygiene notices for retiring or removing *item*: open assigned work, and the
        loss of the default-role designation. They inform and never block."""
        warnings: list[str] = []
        if item.type in (ROSTER_ROLE, ROSTER_OPERATOR):
            open_ids = retirement.open_assigned_work(db, self.spec, item.slug)
            if open_ids:
                warnings.append(
                    f"{item.id} ({item.slug}) still holds open assigned work: "
                    + ", ".join(open_ids)
                )
        if item.type == ROSTER_ROLE:
            warning = retirement.lost_default_designation_warning(
                db, self.spec, item, self.paths.squad_dir, purged=purged, catalog=self.catalog
            )
            if warning:
                warnings.append(warning)
        return warnings

    async def _set_status_core(
        self, db: SquadsDB, item_id: str, status: str, *, force: bool = False, unlink: bool = False
    ) -> tuple[Item, list[retirement.Severance], list[str]]:
        """The status-transition mutation core: takes an already-open transaction's ``db``.

        Returns ``(item, severed, warnings)`` — see :meth:`_set_status_model`. Writes the
        retiring item's frontmatter (status plus any severed refs) and reflogs one ``ref``
        removal entry per severance, before the ``status`` entry.
        """
        await self._refuse_duplicated_ids(require_item(db, item_id))
        item, old_status, base, severed, warnings = self._set_status_model(
            db, item_id, status, force=force, unlink=unlink
        )
        await self._update_item_frontmatter(item, base)
        for sev in severed:
            self.store.log("ref", item.id, {"remove": sev.target, "kind": sev.kind})
        self.store.log(
            "status",
            item.id,
            {"status": [old_status, item.status]},
        )
        return item, severed, warnings

    async def update(  # noqa: PLR0913 — the one metadata entry point
        self,
        item_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        priority: str | None = None,
        clear_priority: bool = False,
        add_labels: list[str] | None = None,
        rm_labels: list[str] | None = None,
        author: str | None = None,
        status: str | None = None,
        force: bool = False,
        parent: str | None = None,
        clear_parent: bool = False,
        set_attributes: dict[str, str] | None = None,
        unset_attributes: list[str] | None = None,
        pronouns: str | None = None,
        operator_invocable: str | None = None,
    ) -> Item:
        """Opens its own transaction, then delegates to :meth:`_update_core` — the bulk
        importer calls that core directly (its own transaction is already open). The
        post-transaction pointer regen (roster items only) stays here, outside the core: it is
        its own I/O concern, not part of the index mutation."""
        async with self.store.transaction() as db:
            item = await self._update_core(
                db,
                item_id,
                title=title,
                description=description,
                assignee=assignee,
                clear_assignee=clear_assignee,
                priority=priority,
                clear_priority=clear_priority,
                add_labels=add_labels,
                rm_labels=rm_labels,
                author=author,
                status=status,
                force=force,
                parent=parent,
                clear_parent=clear_parent,
                set_attributes=set_attributes,
                unset_attributes=unset_attributes,
                pronouns=pronouns,
                operator_invocable=operator_invocable,
            )
        if (
            self.spec.item_is_roster(item.type)
            and item.type != ROSTER_OPERATOR
            and item.status in self.spec.live_statuses(item.type)
        ):
            await self.regen(item.id)  # keep the .claude/ pointer in sync with edited config
        return item

    def _gate_roster_update(
        self,
        item_id: str,
        item: Item,
        title: str | None,
        description: str | None,
        set_attributes: dict[str, str] | None,
        unset_attributes: list[str] | None,
    ) -> None:
        """Ask the gate about the fields an update changes on a role or skill: its title and
        description and the attributes the bundled spec declares (for a role, also the fields
        its role document supplies). A project-declared attribute is not in the set, so writing
        it shadows no override file's content."""
        if item.type in (ROSTER_ROLE, ROSTER_SKILL):
            touched = {*(set_attributes or {}), *(unset_attributes or [])}
            supplied = set(bundled_spec().item_attributes(item.type))
            if item.type == ROSTER_ROLE:
                supplied |= {f.name for f in dataclasses.fields(RoleDef)} - {"slug"}
            # Pronouns are identity the operator sets, not content a role document supplies.
            supplied.discard(AttributeKey.PRONOUNS)
            # The squad's own choice, written by its dedicated option.
            supplied.discard(AttributeKey.OPERATOR_INVOCABLE)
            changed = {
                name
                for name, given in (("title", title), ("description", description))
                if given is not None
            } | (touched & supplied)
            if changed:
                self._refuse_classified_roster_write(item_id, item, "An update", fields=changed)

    def _update_model(  # noqa: PLR0913 — mirrors `update`'s own keyword surface
        self,
        db: SquadsDB,
        item_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        priority: str | None = None,
        clear_priority: bool = False,
        add_labels: list[str] | None = None,
        rm_labels: list[str] | None = None,
        author: str | None = None,
        status: str | None = None,
        force: bool = False,
        parent: str | None = None,
        clear_parent: bool = False,
        set_attributes: dict[str, str] | None = None,
        unset_attributes: list[str] | None = None,
        pronouns: str | None = None,
        operator_invocable: str | None = None,
        now: datetime | None = None,
    ) -> tuple[Item, dict[str, object], tuple[Path, Path] | None, Item]:
        """The pure half of a metadata update (no file I/O). Returns ``(item, delta, rename,
        base)``: *rename* is ``(old_path, new_path)`` when a title change moves the file, else
        ``None``, left to :meth:`_update_core` so the bulk importer's pre-pass (against a throwaway
        ``db`` copy with ``now=ev.at``) never touches the filesystem; *base* is *item* as loaded
        before any field is touched, for the skew guard (:func:`~squads._itemfile.ensure_no_skew`).
        """
        item = require_item(db, item_id)
        # Only what the role document or playbook supplies is gated; tracking metadata
        # (labels, assignee, parent, priority, author) and project-declared attributes stay
        # writable.
        self._gate_roster_update(
            item_id, item, title, description, set_attributes, unset_attributes
        )
        base = item.model_copy(deep=True)
        delta: dict[str, object] = {}
        rename_paths: tuple[Path, Path] | None = None
        if title is not None and title != item.title:
            delta["title"] = [item.title, title]
            rename_paths = self._rename(db, item, title)
        if description is not None:
            delta["description"] = description
            item.description = description
        if clear_assignee:
            delta["assignee"] = None
            item.assignee = None
        elif assignee is not None:
            self._check_assignee(db, assignee or None)
            delta["assignee"] = assignee or None
            item.assignee = assignee or None
        if clear_priority:
            delta["priority"] = None
            item.priority = None
        elif priority is not None:
            checked_priority = self._check_priority(item.type, priority)
            delta["priority"] = checked_priority
            item.priority = checked_priority
        if author is not None:
            self._check_author(db, item.type, author, item.slug)
            delta["author"] = author
            item.author = author
        if status is not None:
            if self.spec.item_is_roster(item.type):
                # A roster item's status is gated by the config-integrity clauses and projected
                # into backend config, which this seam does neither; keep that axis reachable only
                # through `_set_status_model`/`set_roster_status`.
                raise SquadsError(
                    f"{item.id}'s status cannot change through `update` — use the roster "
                    "`status` verb instead (`sq role|skill|operator <addr> status <status>`)"
                )
            old_st = item.status
            self._apply_status(item, status, force=force)
            delta["status"] = [old_st, item.status]
        if clear_parent:  # before the gate below, so `--no-parent` escapes a parent cycle
            delta["parent"] = None
            item.parent = None
        elif parent is not None:
            self._check_parent(db, item.type, parent)
            delta["parent"] = parent
            item.parent = parent
        self._apply_labels(item, add_labels, rm_labels)
        self._apply_attributes(item, set_attributes, unset_attributes)
        self._apply_own_choices(item, delta, pronouns, operator_invocable)
        item.updated_at = now if now is not None else clock.now()
        item.modified_session, _ = actor.current_session()
        # Fail-closed on the updated item's first error-level catalog violation — the
        # same engine `sq check` reports (a warn-level catalog issue never aborts here).
        ValidatorEngine(spec=self.spec, playbook=self.playbook, paths=self.paths).gate(item, db)
        return item, delta, rename_paths, base

    async def _update_core(  # noqa: PLR0913 — mirrors `update`'s own keyword surface
        self,
        db: SquadsDB,
        item_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        priority: str | None = None,
        clear_priority: bool = False,
        add_labels: list[str] | None = None,
        rm_labels: list[str] | None = None,
        author: str | None = None,
        status: str | None = None,
        force: bool = False,
        parent: str | None = None,
        clear_parent: bool = False,
        set_attributes: dict[str, str] | None = None,
        unset_attributes: list[str] | None = None,
        pronouns: str | None = None,
        operator_invocable: str | None = None,
    ) -> Item:
        """The metadata-update core: takes an already-open transaction's ``db``. The roster pointer
        regen stays in :meth:`update`, outside the index transaction. A title change moves the file
        then rewrites its frontmatter, the crash window described at
        :func:`squads._services._retype.apply_type_change`; a title-less update never renames.
        """
        await self._refuse_duplicated_ids(require_item(db, item_id))
        item, delta, rename_paths, base = self._update_model(
            db,
            item_id,
            title=title,
            description=description,
            assignee=assignee,
            clear_assignee=clear_assignee,
            priority=priority,
            clear_priority=clear_priority,
            add_labels=add_labels,
            rm_labels=rm_labels,
            author=author,
            status=status,
            force=force,
            parent=parent,
            clear_parent=clear_parent,
            set_attributes=set_attributes,
            unset_attributes=unset_attributes,
            pronouns=pronouns,
            operator_invocable=operator_invocable,
        )
        default_kind = self.spec.default_ref_kind()
        if rename_paths is not None:
            old_path, new_path = rename_paths
            if old_path != new_path and await self._item_file_exists(old_path):
                # Check for skew before the move, at the still-current path: after it, a refusal
                # would leave the new filename holding old, skewed frontmatter.
                # `update_frontmatter`'s read re-checks against the same `base`.
                old_text = await self._read_item_file(item, old_path)
                ensure_no_skew(old_text, base, default_kind=default_kind)
                await self._move_item_file(old_path, new_path)
        await self._update_item_frontmatter(
            item,
            base,
            rescaffold=True,
        )
        self.store.log("update", item.id, delta)
        return item

    @staticmethod
    def _apply_labels(item: Item, add: list[str] | None, rm: list[str] | None) -> None:
        for lbl in add or []:
            if lbl not in item.labels:
                item.labels.append(lbl)
        if rm:
            item.labels = [lab for lab in item.labels if lab not in rm]

    def _apply_attributes(
        self, item: Item, set_attributes: dict[str, str] | None, unset: list[str] | None
    ) -> None:
        for key, raw in (set_attributes or {}).items():
            field = self._badge_field(item.type, key)
            if field is not None:
                item.set_badge_value(field.code, self._parse_badge_code(field, raw))
            else:
                value = coerce_attribute(item.type, key, raw, self.spec.item_attributes(item.type))
                if item.type == ROSTER_ROLE and key == AttributeKey.MODEL:
                    problem = model_problem(value)
                    if problem is not None:
                        raise SquadsError(problem)
                item.attributes[key] = value
        for key in unset or []:
            field = self._badge_field(item.type, key)
            if field is not None:
                item.set_badge_value(field.code, None)
            else:
                require_settable(item.type, key, self.spec.item_attributes(item.type))
                item.attributes.pop(key, None)

    def _apply_own_choices(
        self, item: Item, delta: dict[str, object], pronouns: str | None, invocable: str | None
    ) -> None:
        """Apply the values the operator or squad chooses for themselves, each through its own
        dedicated option rather than the generic attribute setter."""
        if pronouns is not None:
            delta["pronouns"] = self._apply_pronouns(item, pronouns)
        if invocable is not None:
            delta["operator_invocable"] = self._apply_operator_invocable(item, invocable)

    def _apply_pronouns(self, item: Item, raw: str) -> str | None:
        """Store *raw* as the item's pronouns, trimmed; blank removes them. Returns the value now
        stored. Refuses a value that fails the shape rule, or a type that declares no pronouns."""
        if AttributeKey.PRONOUNS not in self.spec.item_attributes(item.type):
            raise SquadsError(f"a {item.type} does not carry pronouns")
        value = checked_pronouns(raw)
        if value is None:
            item.attributes.pop(AttributeKey.PRONOUNS, None)
        else:
            item.attributes[AttributeKey.PRONOUNS] = value
        return value

    def _apply_operator_invocable(self, item: Item, raw: str) -> bool | None:
        """Store the squad's own ``operator_invocable`` choice (``yes``/``no``, even when it
        equals the default); ``default`` removes it. Returns the value now stored. Not a field a
        role document supplies, so the roster write gate is never asked."""
        value = parse_invocable_choice(raw)
        if AttributeKey.OPERATOR_INVOCABLE not in self.spec.item_attributes(item.type):
            raise SquadsError(f"a {item.type} does not carry operator_invocable")
        if value is None:
            item.attributes.pop(AttributeKey.OPERATOR_INVOCABLE, None)
        else:
            item.attributes[AttributeKey.OPERATOR_INVOCABLE] = value
        return value

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

    def _rename(self, db: SquadsDB, item: Item, new_title: str) -> tuple[Path, Path] | None:
        """Pure half of a title rename: computes the new slug/path and mutates *item*'s
        title/slug/path fields — no file I/O (see :meth:`_update_model`'s docstring for why).

        Returns ``(old_path, new_path)``; the caller (:meth:`_update_core`) performs the actual
        file move through the ``_aio`` helpers. A roster entry's slug is permanent, so only its
        display title changes and nothing moves (``None``).
        """
        require_title(new_title)
        if self.spec.item_is_roster(item.type):
            item.title = new_title
            return None
        new_slug = slugify(new_title)
        old_path = item_file(self.paths, item)
        # Filename stem must stay padded even though item.id is unpadded — format it
        # explicitly from the sequence number, never by concatenating item.id.
        new_stem = format_item_id(item.prefix, item.sequence_id, db.padding)
        new_rel = self.paths.squad_relative(item.type, f"{new_stem}-{new_slug}.md", spec=self.spec)
        new_path = self.paths.abspath(new_rel)
        item.title = new_title
        item.slug = new_slug
        item.path = new_rel
        return old_path, new_path

    async def link(self, child_id: str, parent_id: str) -> Item:
        async with self.store.transaction() as db:
            child = require_item(db, child_id)
            await self._refuse_duplicated_ids(child)
            base = child.model_copy(deep=True)
            old_parent = child.parent
            self._check_parent(db, child.type, parent_id)
            child.parent = parent_id
            child.updated_at = clock.now()
            child.modified_session, _ = actor.current_session()
            # Fail-closed on the reparented child's first error-level catalog violation
            # (parent type-eligibility, in particular) — the same engine every other
            # create/update site gates through.
            ValidatorEngine(spec=self.spec, playbook=self.playbook, paths=self.paths).gate(
                child, db
            )
            await self._update_item_frontmatter(child, base)
            self.store.log(
                "link",
                child.id,
                {"parent": [old_parent, parent_id]},
            )
        return child

    async def unlink(self, child_id: str) -> Item:
        async with self.store.transaction() as db:
            child = require_item(db, child_id)
            await self._refuse_duplicated_ids(child)
            base = child.model_copy(deep=True)
            old_parent = child.parent
            child.parent = None
            child.updated_at = clock.now()
            child.modified_session, _ = actor.current_session()
            await self._update_item_frontmatter(child, base)
            self.store.log(
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
            role_def = resolve_role_for_item(item, self.paths.squad_dir, catalog=self.catalog)
            for backend in self._backends():
                await backend.generate_role_entry(ctx, item, role_def)
        elif item.type == ROSTER_SKILL:
            for backend in self._backends():
                await backend.generate_skill_entry(ctx, item)
        else:
            raise SquadsError(f"{item_id} is a {item.type}; only roles/skills have entries")
        return item

    def _reject_unwritable_body(self, item_id: str, item: Item, *, append: bool) -> None:
        """Raise when *item*'s body write is refused independently of the overwrite guard
        (:func:`~squads._services._base.reject_body_overwrite`), shared with the importer's
        simulation. A skill whose body renders through a declared view is refused on replace and
        append, ``--force`` lifting neither; so is a project-declared roster type outside
        role/skill/operator. A role takes prose beside its view tag.
        """
        if item.type == ROSTER_SKILL:
            self._refuse_classified_roster_write(item_id, item, "Append" if append else "A replace")
        if self.spec.item_is_roster(item.type) and item.type not in (
            ROSTER_ROLE,
            ROSTER_SKILL,
            ROSTER_OPERATOR,
        ):
            raise SquadsError(f"{item_id} is a {item.type}; its body is generated, not authored")

    def _refuse_unplaced_view_tags(self, item: Item, region: str, body: str) -> None:
        """Raise when *body* carries a view tag that *region* (the item's current ``sq:body``
        content) has not placed with the same name and state. The one check the body write and
        the importer's pre-pass both run."""
        if unplaced := view_tags.unplaced_view_tags(region, body):
            raise SquadsError(self._unplaced_view_tag_message(item, unplaced[0]))

    def _unplaced_view_tag_message(self, item: Item, raw_tag: str) -> str:
        """The refusal for a body write carrying view tag *raw_tag* that the item has not placed
        in that state, naming the view verbs only when they work for this host."""
        parts = markers.view_tag_parts(raw_tag)
        assert parts is not None  # `unplaced_view_tags` only returns view tags
        text = (
            f"the body contains the view tag line {raw_tag}, which is not placed on {item.id} "
            "in that state. Leave it out of the body: sq keeps a placed tag in place"
        )
        has_view_verbs = item.type == ROSTER_SKILL or not self.spec.item_is_roster(item.type)
        if (
            not has_view_verbs
            or views.resolve_view_target(
                parts.name, item.type, self.spec, self.playbook, from_squad=self.paths.squad_dir
            )
            is not None
        ):
            return f"{text}."
        addr = item.slug if item.type == ROSTER_SKILL else number_for_id(item.id)
        return (
            f"{text}; to show or hide the view use `sq {item.type} {addr} view add {parts.name}` "
            f"or `sq {item.type} {addr} view disable {parts.name}`."
        )

    def _body_mutate(
        self, item_id: str, body: str, *, append: bool, force: bool = False
    ) -> Callable[[str, Item], tuple[str, bool]]:
        """Build the ``mutate(text, item)`` closure :meth:`set_body` applies through the shared
        section-edit core, so the importer's ``body`` op runs the same logic. It first asks
        :meth:`_reject_unwritable_body`, then applies the prose edit through
        :func:`~squads._view_tags.place_view_tags`, which re-inserts every view tag at its declared
        position; an incoming tag matching a placed one is dropped and any other refused.
        """
        reject_non_view_markers(body)

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            self._reject_unwritable_body(item_id, item, append=append)
            region = sections.get_section(text, markers.BODY)
            if region is None:
                raise SquadsError(
                    f"{item.id} has no complete {markers.PREFIX}{markers.BODY} region in "
                    f"{item_file(self.paths, item)} — restore the "
                    f"`{markers.open_marker(markers.BODY)}` / "
                    f"`{markers.close_marker(markers.BODY)}` marker pair in that file "
                    "(for example from git) and run the command again"
                )
            current = region.strip("\n")
            self._refuse_unplaced_view_tags(item, current, body)
            incoming = view_tags.strip_view_tags(body)
            authored = False
            if not append:
                # Replacing: authored iff there is prose (tags stripped from both sides) that is not
                # the template scaffold (`ServiceCore.pristine_body`); tag stripping and placing are
                # exact spacing inverses, so a scaffold compares equal.
                current_prose = view_tags.strip_view_tags(current).strip()
                authored = not view_tags.body_is_unwritten(current, self.pristine_body(item))
                if authored and not force:
                    reject_body_overwrite(item.id, current_prose)
            slug = item.slug
            addr: int | str = (
                slug if item.type in (ROSTER_ROLE, ROSTER_SKILL) else number_for_id(item_id)
            )
            new_inner = view_tags.place_view_tags(
                current,
                incoming,
                append=append,
                seeded=views.seeded_view_names(
                    item.type, slug, self.spec, from_squad=self.paths.squad_dir
                ),
                spec=self.spec,
                item_type=item.type,
                addr=addr,
            )
            # The body ops that destroyed prose are the ones worth finding again later.
            delta: dict[str, object] = (
                {"replaced_lines": len(current.splitlines())} if authored else {}
            )
            self.store.log("body", item.id, delta)
            return sections.replace_section(text, markers.BODY, new_inner), True

        return mutate

    async def set_body(
        self, item_id: str, body: str, *, append: bool = False, force: bool = False
    ) -> Item:
        """Set (or ``--append`` to) an item's top-level ``:body`` region. A system skill's
        and per-item-type skill's body is refused (:meth:`_reject_unwritable_body`), while a
        role's, a custom skill's and an ordinary item's is admitted. Replacing authored prose is
        refused unless ``force`` (:func:`~squads._services._base.reject_body_overwrite`), which
        never lifts the skill refusal.
        """
        mutate = self._body_mutate(item_id, body, append=append, force=force)
        item, _changed = await self._locked_section_edit(item_id, mutate)
        return item

    async def read_body(self, item_id: str, *, keep_view: str | None = None) -> str:
        """The item's top-level ``:body`` content with any ``sq:view:<name>`` tag expanded but
        *keep_view*'s, which stays as written: the one
        body-read boundary for rendered text (:func:`~squads._view_tags.expand_view_tags`), while
        ``show --json`` reads :meth:`read_stored_body` unexpanded. No writer may source its text
        from here, or expanded view output would be persisted over the tag. A body with no tag
        returns without an index load, as ``sq ui`` opts out of the read scope.
        """
        item = await self.get(item_id)
        body = await self._stored_body(item)
        if not views.has_view_tag(body):
            return body
        db = await self.store.load()
        roster = cache(lambda: self.roster_from_db(db))
        return view_tags.expand_view_tags(
            body,
            item,
            db,
            self.spec,
            self.playbook,
            roster,
            self.paths.squad_dir,
            self.catalog,
            self.paths.config.squad_dir,
            self.working_language,
            keep=keep_view,
        )

    async def _stored_body(self, item: Item) -> str:
        text = await self._read_item_file(item, item_file(self.paths, item))
        return (sections.get_section(text, markers.BODY) or "").strip("\n")

    async def read_stored_body(self, item_id: str) -> str:
        """The item's ``:body`` region exactly as stored, each ``sq:view:<name>`` tag left as a
        tag. The text a client can write back; :meth:`read_body` is the one that expands tags."""
        return await self._stored_body(await self.get(item_id))

    async def view_data(self, item_id: str) -> dict[str, TransformData]:
        """The transform output of each enabled, resolvable view tag in the item's stored body
        whose view declares a transform, keyed by view name; ``{}`` when none qualifies. No
        index load when the body carries no tag."""
        item = await self.get(item_id)
        body = await self._stored_body(item)
        if not views.has_view_tag(body):
            return {}
        db = await self.store.load()
        roster = cache(lambda: self.roster_from_db(db))
        return views.view_data(
            body, item, db, self.spec, self.playbook, roster, self.paths.squad_dir, self.catalog
        )

    async def read_discussion(self, item_id: str) -> str:
        """The item's top-level ``:discussion`` region content (for ``sq show --comments``)."""
        item = await self.get(item_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        return (sections.get_section(text, markers.DISCUSSION) or "").strip("\n")

    async def comments(self, item_id: str) -> list[discussion.Comment]:
        """The item's top-level discussion, parsed into timestamped entries (for the dedicated
        ``sq <type> <n> comments`` read-back verb) — composes :meth:`read_discussion` +
        :func:`discussion.split_discussion` so CLI callers never re-parse the region themselves."""
        item = await self.get(item_id)
        region = await self.read_discussion(item_id)
        return discussion.split_discussion(region, sequence_id=item.sequence_id)

    def _enforce_retirement(
        self, db: SquadsDB, item: Item, target: str, *, purge: bool = False
    ) -> None:
        """Hold *item*, standing at the non-live *target* on a copy of *db*, to the retirement
        gate. The target is set directly rather than reached by a lifecycle edge, so a custom
        lifecycle cannot route around the check. Raises when the result would leave the squad
        structurally invalid."""
        trial = db.model_copy(deep=True)
        probe = trial.items[item.sequence_id]
        probe.status = target
        retirement.enforce(
            self.spec,
            trial,
            probe,
            active_backends=self.paths.config.active_backends,
            unlink=False,
            old_status=item.status,
            playbook=self.playbook,
            squad_dir=self.paths.squad_dir,
            purge=purge,
            catalog=self.catalog,
        )

    def _non_live_status(self, item: Item) -> str | None:
        """A non-live status of *item*'s lifecycle while it is live, else ``None``."""
        live = self.spec.live_statuses(item.type)
        if item.status not in live:
            return None
        others = sorted(self.spec.machine_for(item.type).states - live)
        return others[0] if others else None

    def _retiring_targets(self, item: Item) -> list[str]:
        """The non-live statuses *item* can move to from its live status; empty when it is not
        live or has no such edge."""
        live = self.spec.live_statuses(item.type)
        if item.status not in live:
            return []
        machine = self.spec.machine_for(item.type)
        return [t for t in machine.transitions.get(item.status, []) if t not in live]

    def _retire_status(self, db: SquadsDB, item: Item) -> str | None:
        """The status that retires *item* now, or ``None`` when no such move would be accepted
        (already retired, no retiring edge, or the retirement gate refuses it). Dry-runs the
        real transition against a copy of *db*."""
        for target in self._retiring_targets(item):
            try:
                self._enforce_retirement(db, item, target)
            except SquadsError:
                continue
            return target
        return None

    def _purge_required_message(self, db: SquadsDB, item: Item) -> str:
        message = (
            f"cannot remove {item.id} without --purge: the markdown file would stay on disk "
            "and `sq check` would flag it. To delete it for good, run "
            f"`sq {item.type} {item.id} remove --purge`"
        )
        target = self._retire_status(db, item)
        if target is None:
            return message + "."
        return (
            f"{message}; to retire it and keep it on record, run "
            f"`sq {item.type} {item.id} status {target}`."
        )

    async def remove_item(self, item_id: str, *, purge: bool) -> RosterRemoval:
        """Remove an agent-type item (role/skill/operator): index entry, file and pointers. Refused
        without *purge*, since removing only the index entry would leave a file ``sq check`` flags
        and ``sq repair`` re-indexes; archiving is the non-destructive retirement. A live entry is
        held to the same structural clauses as retiring it, carries the same board-hygiene warnings,
        and the removal is reflogged. Work items use :meth:`remove_work_item`.
        """
        warnings: list[str] = []
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            non_live = self._non_live_status(item)
            if non_live is not None:
                self._enforce_retirement(db, item, non_live, purge=True)
            if not purge:
                raise SquadsError(self._purge_required_message(db, item))
            if non_live is not None:
                warnings = self._retirement_warnings(db, item, purged=True)
            del db.items[item.sequence_id]
            # Unlink before the index commit, as remove_work_item does: a crash leaves the file
            # gone and the index referencing it, which `sq repair` heals by dropping the entry. The
            # reverse would let `sq repair` resurrect the removed item.
            await _aio.path_unlink(item_file(self.paths, item), missing_ok=True)
            self.store.log(
                "remove",
                item.id,
                {"type": item.type, "title": item.title, "status": item.status, "severed_refs": []},
            )
        if self.spec.item_is_roster(item.type) and item.type != ROSTER_OPERATOR:
            ctx = self._ctx
            for backend in self._backends():
                await backend.remove_artifacts(ctx, item)
        return RosterRemoval(item=item, warnings=warnings)

    async def remove_work_item(
        self,
        item_id: str,
        *,
        force: bool = False,
    ) -> RemoveResult:
        """Hard-delete a work item: unlink the ``.md`` and drop its index entry atomically. It
        refuses an item with children even with ``force``, and refuses incoming refs unless
        ``force``, which severs each referrer's edge (a sub-entity's ``deferred_to`` counts) in the
        same transaction. ``db.counter`` is never modified, so a freed number is a sanctioned gap,
        and the ``op=remove`` reflog line is appended inside the transaction.
        """
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            await self._refuse_duplicated_ids(item)

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
            referrer_ids = sorted({*db.backrefs(item.id), *db.deferral_holders(item.id)})
            if referrer_ids and not force:
                listed = ", ".join(referrer_ids)
                raise SquadsError(
                    f"cannot remove {item.id}: it is referenced by: {listed}. "
                    "Re-parent/remove those items first, or re-run with --force to sever them."
                )

            # ------------------------------------------------------------------
            # 3. Sever incoming refs from referrers' frontmatter (--force path)
            # ------------------------------------------------------------------
            severed: list[str] = []
            if force and referrer_ids:
                # Every file the severance will write is checked before the first is written.
                await self._refuse_duplicated_ids(
                    *(r for rid in referrer_ids if (r := db.get(rid)) is not None)
                )
                target_prefix = effective_prefix(item.prefix)
                target_seq = item.sequence_id
                for ref_id in referrer_ids:
                    referrer = db.get(ref_id)
                    if referrer is None:
                        continue
                    base = referrer.model_copy(deep=True)
                    referrer.refs = [
                        r
                        for r in referrer.refs
                        if not ref_id_matches(split_ref(r)[0], target_prefix, target_seq)
                    ]
                    for sub in referrer.subentities:
                        if sub.deferred_to and ref_id_matches(
                            sub.deferred_to, target_prefix, target_seq
                        ):
                            sub.deferred_to = None
                    referrer.updated_at = clock.now()
                    await self._update_item_frontmatter(referrer, base)
                    severed.append(ref_id)

            # ------------------------------------------------------------------
            # 4. Hard-delete: drop index entry + unlink the .md
            # ------------------------------------------------------------------
            path = item_file(self.paths, item)
            # Unlink before the index commit so a crash leaves the file gone and the index
            # referencing it, which `sq repair` heals; the reverse would resurrect the item.
            await _aio.path_unlink(path, missing_ok=True)
            del db.items[item.sequence_id]
            # counter is intentionally NOT modified — the gap is sanctioned.

            # Reflog: op=remove + gone-item snapshot.
            # Appended AFTER os.replace by the store's transaction machinery.
            self.store.log(
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
