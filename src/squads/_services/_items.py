"""Item lifecycle: status transitions, edits, links, regen, removal."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError, StatusNotInWorkflowError
from squads._index._resolver import item_file, require_item
from squads._interactions import is_system_skill
from squads._itemfile import ensure_no_skew, update_frontmatter
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, format_item_id, ref_id_matches, split_ref
from squads._models._metadata import coerce_extra
from squads._roles._resolver import resolve_role_for_item
from squads._services import _retirement as retirement
from squads._services._base import ServiceCore, reject_body_overwrite, reject_markers
from squads._services._results import RemoveResult, RosterStatusResult, Severance
from squads._services._validators import ValidatorEngine
from squads._util import slugify
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL


class ItemsMixin(ServiceCore):
    async def set_status(self, item_id: str, status: str, *, force: bool = False) -> Item:
        """Opens its own transaction, then delegates to :meth:`_set_status_core` — the bulk
        importer calls that core directly (its own transaction is already open).

        A roster item's transition additionally projects into backend config, **after** the
        transaction commits (see :meth:`~squads._services._base.ServiceCore
        ._project_roster_transition`): materialise when the new status is live, withdraw
        otherwise, then recompile the managed regions. The bulk importer's direct
        ``_set_status_core`` calls skip this — replayed history converges on the next
        ``sq sync``, the same story as any squad already on disk with a retired entry.

        A roster item's transition is additionally held to the config-integrity clauses
        (see ``_services/_retirement.py``), scoped to this transition's own delta, inside
        :meth:`_set_status_model`'s pure half — unconditionally, regardless of ``force``, which
        overrides only the lifecycle's own transition edge, never these. This entry point never
        passes ``--unlink``; the roster ``status`` verb calls :meth:`set_roster_status` instead,
        which also reports what that flag severed.

        Both entry points are held to the per-item catalog gate in that same pure half, so this
        shortcut refuses exactly what ``update --status`` refuses.
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
            await self._project_roster_transition(item)
        # Post-commit partial resync for each severed preload edge — mirrors unlink_role's own
        # existing behaviour: the retiring item's own status/refs are already committed above,
        # this only refreshes the previously-scoped role's re-derivable cache + generated entry.
        preload_kind = self.spec.preload_ref_kind()
        for sev in severed:
            if sev.kind == preload_kind:
                role = await self.get(sev.target)
                await self._resync_role_skills(role.extra.get(X.SLUG, role.slug))
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
    ) -> tuple[Item, str, Item, list[Severance], list[str]]:
        """The PURE half of a status transition: no file I/O. Returns ``(item, old_status, base,
        severed, warnings)``:

        - ``base`` is the item as loaded, before this call's own delta, for the write seam's
          skew guard (see :func:`~squads._itemfile.ensure_no_skew`).
        - ``severed`` is the ``--unlink`` edges removed from *item*'s own refs — always empty
          unless ``unlink`` was passed and the transition is a retirement.
        - ``warnings`` is board-hygiene notices (open assigned work on a retiring role/operator)
          that never block the transition — config integrity and board hygiene are different
          questions (see :func:`~squads._services._retirement.open_assigned_work`).

        A roster item is held to the config-integrity clauses here, scoped to this transition's
        own delta — a pre-existing violation never blocks it — unconditionally with respect to
        ``force``, which overrides only the lifecycle edge just above, never these; see
        ``_services/_retirement.py``.

        Shared by :meth:`_set_status_core` (the interactive/apply path) and the bulk importer's
        pre-pass, which calls this directly against a throwaway ``db`` copy with ``now=ev.at``
        to simulate the transition using the exact same workflow gate the real path runs —
        including the config-integrity gate, so a replayed history is held to the same rule at
        each step it replays.
        """
        item = require_item(db, item_id)
        base = item.model_copy(deep=True)
        old_status = item.status
        self._apply_status(item, status, force=force)
        severed: list[Severance] = []
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
            )
            live = self.spec.live_statuses(item.type)
            is_retirement = old_status in live and item.status not in live
            if item.type in (ROSTER_ROLE, ROSTER_OPERATOR) and is_retirement:
                slug = item.extra.get(X.SLUG, item.slug)
                open_ids = retirement.open_assigned_work(db, self.spec, slug)
                if open_ids:
                    warnings.append(
                        f"{item.id} ({slug}) still holds open assigned work: " + ", ".join(open_ids)
                    )
            if item.type == ROSTER_ROLE and is_retirement:
                warning = retirement.lost_default_designation_warning(
                    db, self.spec, item, self.paths.squad_dir
                )
                if warning:
                    warnings.append(warning)
        item.updated_at = now if now is not None else clock.now()
        item.modified_session, _ = actor.current_session()
        # Fail-closed on the transitioned item's first error-level catalog violation — the
        # same gate `_update_model` runs, reached here for the same reason: the `status` verb
        # is a shortcut for `update --status`, so the two must refuse the same corpus states.
        # A parent cycle is the case that makes it load-bearing: the item is unwritable until
        # the cycle is broken, and `--no-parent` (which never comes through here) is the way
        # out. A warn-level catalog issue never aborts, exactly as on the update path.
        ValidatorEngine(spec=self.spec).gate(item, db)
        return item, old_status, base, severed, warnings

    async def _set_status_core(
        self, db: SquadsDB, item_id: str, status: str, *, force: bool = False, unlink: bool = False
    ) -> tuple[Item, list[Severance], list[str]]:
        """The status-transition mutation core: takes an already-open transaction's ``db``.

        Returns ``(item, severed, warnings)`` — see :meth:`_set_status_model`. Writes the
        retiring item's frontmatter (status plus any severed refs) and reflogs one ``ref``
        removal entry per severance, before the ``status`` entry.
        """
        item, old_status, base, severed, warnings = self._set_status_model(
            db, item_id, status, force=force, unlink=unlink
        )
        await update_frontmatter(
            item_file(self.paths, item), item, base, default_kind=self.spec.default_ref_kind()
        )
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
                priority=priority,
                clear_priority=clear_priority,
                add_labels=add_labels,
                rm_labels=rm_labels,
                author=author,
                status=status,
                force=force,
                parent=parent,
                clear_parent=clear_parent,
                set_extra=set_extra,
                unset_extra=unset_extra,
            )
        if self.spec.item_is_roster(item.type) and item.type != ROSTER_OPERATOR:
            await self.regen(item.id)  # keep the .claude/ pointer in sync with edited config
        return item

    def _update_model(  # noqa: PLR0913 — mirrors `update`'s own keyword surface
        self,
        db: SquadsDB,
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
        now: datetime | None = None,
    ) -> tuple[Item, dict[str, object], tuple[Path, Path] | None, Item]:
        """The PURE half of a metadata update: no file I/O. Returns ``(item, delta, rename,
        base)``.

        ``rename`` is ``(old_path, new_path)`` when the title change requires moving the file
        on disk, else ``None`` — the physical move is a separate I/O step the caller
        (:meth:`_update_core`) performs, kept out of this pure half so the bulk importer's
        pre-pass (which calls this directly against a throwaway ``db`` copy with ``now=ev.at``
        to simulate the update using the exact same checks + catalog gate the real path runs)
        never touches the real filesystem.

        ``base`` is *item* as loaded, before this call's own delta — captured before any
        field is touched, for the write seam's skew guard
        (see :func:`~squads._itemfile.ensure_no_skew`).
        """
        item = require_item(db, item_id)
        base = item.model_copy(deep=True)
        delta: dict[str, object] = {}
        rename_paths: tuple[Path, Path] | None = None
        if title is not None and title != item.title:
            delta["title"] = [item.title, title]
            rename_paths = self._rename(db, item, title)
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
            checked_priority = self._check_priority(item.type, priority)
            delta["priority"] = checked_priority
            item.priority = checked_priority
        if author is not None:
            self._check_author(db, item.type, author, item.slug)
            delta["author"] = author
            item.author = author
        if status is not None:
            if self.spec.item_is_roster(item.type):
                # A roster item's status is held to the config-integrity clauses and projects
                # into backend config — this metadata-update seam evaluates neither. Keep the
                # roster status axis reachable through exactly one gated path
                # (`_set_status_model`/`set_roster_status`), never through this one.
                raise SquadsError(
                    f"{item.id}'s status cannot change through `update` — use the roster "
                    "`status` verb instead (`sq role|skill|operator <addr> status <status>`)"
                )
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
        item.updated_at = now if now is not None else clock.now()
        item.modified_session, _ = actor.current_session()
        # Fail-closed on the updated item's first error-level catalog violation — the
        # same engine `sq check` reports (a warn-level catalog issue never aborts here).
        ValidatorEngine(spec=self.spec).gate(item, db)
        return item, delta, rename_paths, base

    async def _update_core(  # noqa: PLR0913 — mirrors `update`'s own keyword surface
        self,
        db: SquadsDB,
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
        """The metadata-update mutation core: takes an already-open transaction's ``db``.

        Does NOT run the roster pointer regen — that stays in :meth:`update`, since it is its
        own I/O concern outside the index transaction (the bulk importer runs its own regen
        pass, if any, after the whole apply commits).

        A title change shares retype's rename-then-write shape below: the file moves to its
        new path, then its frontmatter is rewritten there — see
        :func:`squads._services._retype.apply_type_change` for the crash window that opens
        between those two steps and why it is the expected, repairable outcome rather than a
        defect. A title-less update never renames, so it stays readable at one path throughout.
        """
        item, delta, rename_paths, base = self._update_model(
            db,
            item_id,
            title=title,
            description=description,
            assignee=assignee,
            priority=priority,
            clear_priority=clear_priority,
            add_labels=add_labels,
            rm_labels=rm_labels,
            author=author,
            status=status,
            force=force,
            parent=parent,
            clear_parent=clear_parent,
            set_extra=set_extra,
            unset_extra=unset_extra,
        )
        default_kind = self.spec.default_ref_kind()
        if rename_paths is not None:
            old_path, new_path = rename_paths
            if old_path != new_path and await _aio.path_exists(old_path):
                # Check for a skew BEFORE the physical move, at the item's still-current
                # path: once moved, a refusal here would otherwise leave the file sitting at
                # the new filename with its old (skewed) frontmatter still inside — a strictly
                # worse intermediate state than not moving it at all. `update_frontmatter`'s
                # own read below (at the possibly-new path) re-checks against the same `base`,
                # which is safe/redundant rather than a second real read of divergent content.
                old_text = await _aio.read_text(old_path)
                ensure_no_skew(old_text, base, default_kind=default_kind)
                await _aio.path_rename(old_path, new_path)
        await update_frontmatter(item_file(self.paths, item), item, base, default_kind=default_kind)
        self.store.log("update", item.id, delta)
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

    def _rename(self, db: SquadsDB, item: Item, new_title: str) -> tuple[Path, Path]:
        """Pure half of a title rename: computes the new slug/path and mutates *item*'s
        title/slug/path fields — no file I/O (see :meth:`_update_model`'s docstring for why).

        Returns ``(old_path, new_path)``; the caller (:meth:`_update_core`) performs the actual
        file move through the ``_aio`` helpers.
        """
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
            base = child.model_copy(deep=True)
            old_parent = child.parent
            self._check_parent(db, child.type, parent_id)
            child.parent = parent_id
            child.updated_at = clock.now()
            child.modified_session, _ = actor.current_session()
            # Fail-closed on the reparented child's first error-level catalog violation
            # (parent type-eligibility, in particular) — the same engine every other
            # create/update site gates through.
            ValidatorEngine(spec=self.spec).gate(child, db)
            await update_frontmatter(
                item_file(self.paths, child), child, base, default_kind=self.spec.default_ref_kind()
            )
            self.store.log(
                "link",
                child.id,
                {"parent": [old_parent, parent_id]},
            )
        return child

    async def unlink(self, child_id: str) -> Item:
        async with self.store.transaction() as db:
            child = require_item(db, child_id)
            base = child.model_copy(deep=True)
            old_parent = child.parent
            child.parent = None
            child.updated_at = clock.now()
            child.modified_session, _ = actor.current_session()
            await update_frontmatter(
                item_file(self.paths, child), child, base, default_kind=self.spec.default_ref_kind()
            )
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
            role_def = resolve_role_for_item(item, self.paths.squad_dir)
            for backend in self._backends():
                await backend.generate_role_entry(ctx, item, role_def)
        elif item.type == ROSTER_SKILL:
            for backend in self._backends():
                await backend.generate_skill_entry(ctx, item)
        else:
            raise SquadsError(f"{item_id} is a {item.type}; only roles/skills have entries")
        return item

    def _body_mutate(
        self, item_id: str, body: str, *, append: bool, force: bool = False
    ) -> Callable[[str, Item], str]:
        """Build the ``mutate(text, item)`` closure :meth:`set_body` applies via the shared
        section-edit core — factored out so the bulk importer's ``body`` op can drive the exact
        same logic through :meth:`~squads._services._base.ServiceCore._section_edit_core`."""
        reject_markers(body)

        def mutate(text: str, item: Item) -> str:
            if item.type == ROSTER_SKILL:
                slug = item.extra.get(X.SLUG, item.slug)
                if is_system_skill(slug, self.spec):
                    raise SquadsError(
                        f"{item_id} is a system skill; its definition is template-owned and"
                        " rendered on read (an authored body here would never be shown)"
                    )
            elif item.type == ROSTER_ROLE:
                raise SquadsError(
                    f"{item_id} is a role; its definition is resolved from the role catalog"
                    " and rendered on read (an authored body here would never be shown) —"
                    " declare it in `.overrides/roles.toml`, or in"
                    " `.overrides/roles/<slug>.toml` for a project-defined role"
                )
            elif self.spec.item_is_roster(item.type) and item.type != ROSTER_OPERATOR:
                raise SquadsError(
                    f"{item_id} is a {item.type}; its body is generated, not authored"
                )
            current = (sections.get_section(text, markers.BODY) or "").strip("\n")
            if append:
                # Append destroys nothing, so it needs no guard and no scaffold distinction —
                # whatever is there is kept and the new prose follows it.
                self.store.log("body", item.id, {})
                new_body = f"{current}\n\n{body}" if current else body
                return sections.replace_section(text, markers.BODY, new_body)
            # Replacing: authored iff there is prose and it is not the template scaffold the
            # item was created with — see ServiceCore.pristine_body for why that is derived
            # rather than pattern-matched.
            authored = bool(current) and current != self.pristine_body(item)
            if authored and not force:
                reject_body_overwrite(item.id, current)
            # The body ops that destroyed prose are the ones worth finding again later.
            delta: dict[str, object] = (
                {"replaced_lines": len(current.splitlines())} if authored else {}
            )
            self.store.log("body", item.id, delta)
            return sections.replace_section(text, markers.BODY, body)

        return mutate

    async def set_body(
        self, item_id: str, body: str, *, append: bool = False, force: bool = False
    ) -> Item:
        """Set (or ``--append`` to) an item's top-level ``:body`` region — no manual editing.

        The body is free-form markdown the agent owns; ``description`` stays a short frontmatter
        summary. A role's body is rejected here because its definition renders from the role
        catalog on every read (``ServiceCore.role_definition_text``) and nothing would ever show
        what was written; a system (template-owned) skill's body is rejected for the same reason
        one document over (``ServiceCore.skill_definition_text``). A *custom* (author-defined)
        skill is the one roster-type exception: its body is authored content, and the only place
        that content lives, so it's admitted.

        Replacing an **authored** body is refused unless ``force`` — the write is destructive and
        there is no undo (see :func:`~squads._services._base.reject_body_overwrite`). Writing over
        the unwritten template scaffold, which is what a first write does, is not affected.
        """
        mutate = self._body_mutate(item_id, body, append=append, force=force)
        return await self._locked_section_edit(item_id, mutate)

    async def read_body(self, item_id: str) -> str:
        """The item's top-level ``:body`` region content (for ``sq show``) — read on a thread."""
        item = await self.get(item_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        return (sections.get_section(text, markers.BODY) or "").strip("\n")

    async def read_discussion(self, item_id: str) -> str:
        """The item's top-level ``:discussion`` region content (for ``sq show --comments``)."""
        item = await self.get(item_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        return (sections.get_section(text, markers.DISCUSSION) or "").strip("\n")

    async def comments(self, item_id: str) -> list[discussion.Comment]:
        """The item's top-level discussion, parsed into timestamped entries (for the dedicated
        ``sq <type> <n> comments`` read-back verb) — composes :meth:`read_discussion` +
        :func:`discussion.split_discussion` so CLI callers never re-parse the region themselves."""
        return discussion.split_discussion(await self.read_discussion(item_id))

    async def remove_item(self, item_id: str, *, purge: bool = False) -> Item:
        """Remove an agent-type item (role/skill/operator) from the index.

        For **work items** (feature/task/bug/decision/review/epic/guide), use
        :meth:`remove_work_item` instead — it enforces ref/child safety, always unlinks the
        ``.md``, and carries the reflog op stub.
        """
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            del db.items[item.sequence_id]
            # Unlink BEFORE the index commit (same direction as remove_work_item): a crash here
            # leaves the file gone with the index still referencing it, which `sq repair` heals
            # by dropping the orphan entry. Unlinking after the commit (the previous shape) is
            # the lossy direction — a crash there leaves the index without the entry and the
            # file still on disk, which `sq repair` re-indexes, resurrecting the removed item.
            if purge:
                await _aio.path_unlink(item_file(self.paths, item), missing_ok=True)
        if self.spec.item_is_roster(item.type) and item.type != ROSTER_OPERATOR:
            ctx = self._ctx
            for backend in self._backends():
                await backend.remove_artifacts(ctx, item)
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
        here and appended post-commit via ``store.log()`` inside the transaction.
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
                # Resolved once for the whole severance loop, not per referrer.
                default_kind = self.spec.default_ref_kind()
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
                    referrer.updated_at = clock.now()
                    await update_frontmatter(
                        item_file(self.paths, referrer), referrer, base, default_kind=default_kind
                    )
                    severed.append(ref_id)

            # ------------------------------------------------------------------
            # 4. Hard-delete: drop index entry + unlink the .md
            # ------------------------------------------------------------------
            path = item_file(self.paths, item)
            # Unlink BEFORE the index commit so the safe failure direction is preserved:
            # a crash here leaves the file gone with the index still referencing it —
            # sq repair drops the orphan entry.  The reverse (index-gone / file-survives)
            # would let sq repair resurrect the removed item.
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
