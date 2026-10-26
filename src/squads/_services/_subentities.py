"""Sub-entities (user stories, subtasks, review findings): scaffold and status machine. Their state
lives in the parent's frontmatter as ``Item.subentities``; this layer mutates that model atomically
and re-renders the block's ``### <local_id> — title`` heading. The ``:head`` badge line and
``:summary`` roll-up are computed on request, and each sub-entity's prose (``:body`` +
``:discussion``) stays marker-owned in the body.
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import ensure_no_skew
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._services._base import (
    ServiceCore,
    reject_body_overwrite,
    reject_markers,
    subentity_title,
)
from squads._services._results import BlockResult, SubentityDetail


class SubentitiesMixin(ServiceCore):
    def _checked_field_values(self, kind: str, fields: dict[str, str] | None) -> dict[str, str]:
        """One validated badge code per field code, refusing a code *kind* does not declare: the
        sub-entity mirror of the item axis's ``_create_model`` gate, so the generic ``fields=`` door
        cannot store a field the spec does not declare, which would render nowhere and pass ``sq
        check``.
        """
        checked: dict[str, str] = {}
        for code, value in (fields or {}).items():
            field = self._badge_field(kind, code)
            if field is None:
                declared = ", ".join(f.code for f in self.spec.fields_for(kind)) or "(none)"
                raise SquadsError(
                    f"{code!r} is not a settable field on a {kind}; valid: {declared}"
                )
            checked[code] = self._parse_badge_code(field, value)
        return checked

    async def add_story(
        self,
        feature_id: str,
        title: str = "",
        *,
        assignee: str | None = None,
        status: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        return await self.add_block(
            feature_id, "story", title, assignee=assignee, status=status, body=body
        )

    async def add_subtask(
        self,
        task_id: str,
        title: str = "",
        *,
        story: str | None = None,
        assignee: str | None = None,
        status: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        return await self.add_block(
            task_id, "subtask", title, story=story, assignee=assignee, status=status, body=body
        )

    async def add_finding(
        self,
        review_id: str,
        title: str = "",
        *,
        severity: str | None = None,
        assignee: str | None = None,
        status: str | None = None,
        deferred_to: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        # Omit the field when the spec's `finding` kind declares no `severity`: a hardcoded
        # default would be the undeclared write `_checked_field_values` refuses.
        resolved_severity = severity or self.field_default("finding", "severity")
        return await self.add_block(
            review_id,
            "finding",
            title,
            fields={"severity": resolved_severity} if resolved_severity is not None else None,
            assignee=assignee,
            status=status,
            deferred_to=deferred_to,
            body=body,
        )

    # Public kind-taking surface: these methods take any declared kind, including project-declared
    # ones, and the per-kind wrappers above delegate to them.

    async def add_block(  # noqa: PLR0913 — the sub-entity scaffold entry point
        self,
        item_id: str,
        kind: str,
        title: str,
        *,
        story: str | None = None,
        fields: dict[str, str] | None = None,
        assignee: str | None = None,
        status: str | None = None,
        deferred_to: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        """Opens its own transaction, then delegates to :meth:`_add_block_core` — the bulk
        importer calls that core directly (its own transaction is already open)."""
        async with self.store.transaction() as db:
            return await self._add_block_core(
                db,
                item_id,
                kind,
                title,
                story=story,
                fields=fields,
                assignee=assignee,
                status=status,
                deferred_to=deferred_to,
                body=body,
            )

    def _add_block_model(  # noqa: PLR0913 — mirrors `add_block`'s own keyword surface
        self,
        db: SquadsDB,
        item_id: str,
        kind: str,
        title: str,
        *,
        story: str | None = None,
        fields: dict[str, str] | None = None,
        assignee: str | None = None,
        status: str | None = None,
        deferred_to: str | None = None,
        body: str | None = None,
        now: datetime | None = None,
    ) -> tuple[Item, SubEntity, Item]:
        """The pure half of scaffolding a sub-entity: every check, the local-id allocation and the
        ``SubEntity`` itself, with no file I/O. Returns ``(item, sub, base)``, *base* being *item*
        as loaded for the write seam's skew guard (:func:`~squads._itemfile.ensure_no_skew`). Shared
        by :meth:`_add_block_core` and the bulk importer's pre-pass, which runs it on a throwaway
        ``db`` copy.
        """
        title = subentity_title(title)
        reject_markers(title, "title")
        if body is not None:
            reject_markers(body)
        # _require_parent validates `kind` against the item's declared subentity_kind first, so a
        # bad kind raises a SquadsError the bulk importer can collect; resolving the status first
        # would KeyError and abort the pre-pass.
        item = self._require_parent(db, item_id, kind)
        base = item.model_copy(deep=True)
        initial_status = self._resolve_add_status(kind, status)
        self._check_assignee(db, assignee)
        if story:
            self._check_maps_parent_story(kind)
            self._validate_subtask_story(db, item, story)
        local_id = discussion.next_local_id(item.subentities, kind, self.spec)
        sub = SubEntity(
            local_id=local_id,
            title=title,
            status=initial_status,
            assignee=assignee,
            story=story,
        )
        # Generic field-code -> badge-code store: ``severity`` (typed attribute) or any
        # other declared field (SubEntity.extra) — the same dispatch for every code, gated
        # on the kind's own declarations first.
        for code, value in self._checked_field_values(kind, fields).items():
            sub.set_badge_value(code, value)
        self._settle_deferral(db, kind, item, sub, moved=True, deferred_to=deferred_to)
        item.subentities.append(sub)
        item.updated_at = now if now is not None else clock.now()
        return item, sub, base

    async def _add_block_core(  # noqa: PLR0913 — mirrors `add_block`'s own keyword surface
        self,
        db: SquadsDB,
        item_id: str,
        kind: str,
        title: str,
        *,
        story: str | None = None,
        fields: dict[str, str] | None = None,
        assignee: str | None = None,
        status: str | None = None,
        deferred_to: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        """The sub-entity-scaffold mutation core: takes an already-open transaction's ``db``."""
        container = self._container_for(kind)
        item, sub, base = self._add_block_model(
            db,
            item_id,
            kind,
            title,
            story=story,
            fields=fields,
            assignee=assignee,
            status=status,
            deferred_to=deferred_to,
            body=body,
        )
        local_id = sub.local_id
        path = item_file(self.paths, item)
        text = await self._read_item_file(item, path)
        if not sections.has_section(text, container):
            if discussion.stale_container_tags(text, container):
                raise SquadsError(f"no {container} section in {item_id}")
            opened, closed = markers.open_marker(container), markers.close_marker(container)
            if (opened in text) != (closed in text):
                raise SquadsError(
                    f"{item_id}: the {container} container is half present -- restore its "
                    f"{opened} and {closed} lines by hand"
                )
            text = discussion.restore_container(text, item, kind, self.spec)
        block = discussion.build_block(
            kind, local_id, title, body=body, spec=self.spec, from_squad=self.paths.squad_dir
        )
        text = sections.append_to_section(text, container, block)
        await self._write_block_file(item, path, text=text, sub=sub, base=base)
        # Advisory title-length check against the same type-aware threshold `sq check`'s
        # `subentity_title_max` reads (`None` when the type does not select it), so create and check
        # agree. The warning rides back on the result; the service never prints.
        body_cmd = f'sq {item.type} {item.sequence_id} {kind} {local_id} body -m "…"'
        title_advisory: str | None = None
        threshold = self.spec.item_subentity_title_max(item.type)
        if threshold is not None and len(title) > threshold:
            title_advisory = (
                f"Title is {len(title)} chars — a sub-entity title is a one-line handle,"
                f" not the description. Put the detail in the body:\n  {body_cmd}"
            )
        log_delta: dict[str, object] = {
            "op": "add",
            "kind": kind,
            "local_id": local_id,
            "title": title,
        }
        if title_advisory is not None:
            log_delta["title_advisory"] = {"advisory": True, "title_len": len(title)}
        self.store.log(
            "subentity",
            item.id,
            log_delta,
        )
        btag = discussion.body_tag(kind, local_id)
        span = sections.region_lines(await self._read_item_file(item, path), btag)
        return BlockResult(
            local_id=local_id,
            path=path,
            body_tag=btag,
            start_line=span[0] if span else None,
            end_line=span[1] if span else None,
            title_advisory=title_advisory,
            body_command=body_cmd,
        )

    async def list_stories(self, feature_id: str) -> list[SubEntity]:
        return await self.list_blocks(feature_id, "story")

    async def list_subtasks(self, task_id: str) -> list[SubEntity]:
        return await self.list_blocks(task_id, "subtask")

    async def list_findings(self, review_id: str) -> list[SubEntity]:
        return await self.list_blocks(review_id, "finding")

    async def list_blocks(self, parent_id: str, kind: str) -> list[SubEntity]:
        item = await self.get(parent_id)
        self._check_type(item, kind)
        return item.subentities

    async def set_subtask_status(
        self, task_id: str, local_id: str, status: str, **kw: bool
    ) -> None:
        await self.set_block_status(task_id, "subtask", local_id, status, **kw)

    async def set_story_status(
        self, feature_id: str, local_id: str, status: str, **kw: bool
    ) -> None:
        await self.set_block_status(feature_id, "story", local_id, status, **kw)

    async def set_subtask_done(self, task_id: str, local_id: str, *, done: bool = True) -> None:
        # convenience toggle (forces past intermediate states).
        # Resolves the subtask machine's designated completion status / start state by
        # its role in the state machine rather than a hardcoded status literal.
        target = (
            self.spec.subentity_completion("subtask")
            if done
            else self.spec.subentity_initial("subtask")
        )
        await self.set_block_status(task_id, "subtask", local_id, target, force=True)

    async def set_subtask_assignee(self, task_id: str, local_id: str, assignee: str | None) -> None:
        await self._set_block_assignee(task_id, "subtask", local_id, assignee)

    async def set_subtask_body(
        self, task_id: str, local_id: str, body: str, *, append: bool = False, force: bool = False
    ) -> None:
        await self.set_block_body(task_id, "subtask", local_id, body, append=append, force=force)

    async def set_story_body(
        self,
        feature_id: str,
        local_id: str,
        body: str,
        *,
        append: bool = False,
        force: bool = False,
    ) -> None:
        await self.set_block_body(feature_id, "story", local_id, body, append=append, force=force)

    async def update_subtask(  # noqa: PLR0913 — full metadata entry point for a subtask
        self,
        task_id: str,
        local_id: str,
        *,
        title: str | None = None,
        story: str | None = None,
        clear_story: bool = False,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: str | None = None,
        force: bool = False,
    ) -> None:
        await self.update_block(
            task_id,
            "subtask",
            local_id,
            title=title,
            story=story,
            clear_story=clear_story,
            assignee=assignee,
            clear_assignee=clear_assignee,
            status=status,
            force=force,
        )

    async def update_finding(  # noqa: PLR0913 — mirrors `update_block`'s keyword surface
        self,
        review_id: str,
        local_id: str,
        *,
        title: str | None = None,
        severity: str | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: str | None = None,
        deferred_to: str | None = None,
        force: bool = False,
    ) -> None:
        await self.update_block(
            review_id,
            "finding",
            local_id,
            title=title,
            fields={"severity": severity} if severity is not None else None,
            assignee=assignee,
            clear_assignee=clear_assignee,
            status=status,
            deferred_to=deferred_to,
            force=force,
        )

    async def get_subtask(self, task_id: str, local_id: str) -> SubentityDetail:
        return await self.get_block(task_id, "subtask", local_id)

    async def get_story(self, feature_id: str, local_id: str) -> SubentityDetail:
        return await self.get_block(feature_id, "story", local_id)

    async def set_block_status(
        self, parent_id: str, kind: str, local_id: str, status: str, *, force: bool = False
    ) -> None:
        """Opens its own transaction, then delegates to :meth:`_set_block_status_core` — the
        bulk importer calls that core directly (its own transaction is already open)."""
        async with self.store.transaction() as db:
            await self._set_block_status_core(db, parent_id, kind, local_id, status, force=force)

    def _set_block_status_model(
        self,
        db: SquadsDB,
        parent_id: str,
        kind: str,
        local_id: str,
        status: str,
        *,
        force: bool = False,
        deferred_to: str | None = None,
        now: datetime | None = None,
    ) -> tuple[Item, SubEntity, str, Item]:
        """The PURE half of a sub-entity status transition: no file I/O.

        Returns ``(item, sub, old_status, base)`` — ``base`` is *item* as loaded, before this
        call's own delta. Shared by :meth:`_set_block_status_core` (the interactive/apply path)
        and the bulk importer's pre-pass, which calls this directly against a throwaway ``db``
        copy with ``now=ev.at``.
        """
        item = self._require_parent(db, parent_id, kind)
        sub = self._find(item, kind, local_id)
        base = item.model_copy(deep=True)
        old_status = sub.status
        self._apply_subentity_status(kind, sub, status, force=force)
        self._settle_deferral(db, kind, item, sub, moved=True, deferred_to=deferred_to)
        item.updated_at = now if now is not None else clock.now()
        return item, sub, old_status, base

    async def _set_block_status_core(
        self,
        db: SquadsDB,
        parent_id: str,
        kind: str,
        local_id: str,
        status: str,
        *,
        force: bool = False,
        deferred_to: str | None = None,
    ) -> None:
        """The sub-entity status-transition mutation core: takes an already-open ``db``."""
        item, sub, old_status, base = self._set_block_status_model(
            db, parent_id, kind, local_id, status, force=force, deferred_to=deferred_to
        )
        await self._write_block_file(item, item_file(self.paths, item), sub=sub, base=base)
        self.store.log(
            "subentity",
            item.id,
            {
                "op": "status",
                "kind": kind,
                "local_id": local_id,
                "status": [old_status, sub.status],
            },
        )

    def _require_declared_status(self, kind: str, status: str) -> str:
        """*status* itself, provided it names one of *kind*'s own declared lifecycle states: the
        vocabulary gate shared by ``add-<kind>`` and ``<kind> <k> update --status``, resolved from
        the active spec. It is unconditional, unlike the edge gate ``--force`` waives
        (:meth:`_apply_subentity_status`), because a stored non-member is a ``sq check`` error.
        """
        valid = self.spec.subentity_workflow(kind).states
        if status not in valid:
            choices = ", ".join(sorted(valid))
            raise SquadsError(f"{status!r} is not a valid {kind} status (one of: {choices})")
        return status

    def _resolve_add_status(self, kind: str, status: str | None) -> str:
        """The status a fresh *kind* sub-entity is seeded with: the kind's own initial state
        when *status* is omitted (unchanged behaviour), else *status* itself once
        :meth:`_require_declared_status` has cleared it (creation seeds, it does not transition
        from a prior state, so membership is the only question here)."""
        if status is None:
            return self.spec.subentity_initial(kind)
        return self._require_declared_status(kind, status)

    def _apply_subentity_status(
        self, kind: str, sub: SubEntity, status: str, *, force: bool
    ) -> None:
        """Move *sub* to *status* through two gates. The vocabulary gate is unconditional: the
        target must be one of the kind's declared states. The transition gate is waivable by
        *force*: the edge ``current -> status`` must be one the machine permits. Checking vocabulary
        first keeps a sub-entity already holding a non-member status recoverable, since ``force``
        skips the lookup of ``current``.
        """
        # Defensive str() — status is spec vocabulary (a plain string), no enum involved.
        status = str(status)
        self._require_declared_status(kind, status)
        current = sub.status
        if (
            not force
            and current != status
            and not self.spec.subentity_can_transition(kind, current, status)
        ):
            raise InvalidTransitionError(
                f"{kind} {sub.local_id} cannot move {current} → {status} (use --force to override)"
            )
        sub.status = status

    def _settle_deferral(
        self,
        db: SquadsDB,
        kind: str,
        item: Item,
        sub: SubEntity,
        *,
        moved: bool,
        deferred_to: str | None,
    ) -> None:
        """Bring *sub*'s ``deferred_to`` in line with its status, after a status move
        (*moved*; a new sub-entity enters its status) and/or a carrier named by the caller.

        A pointer needs a deferred-role status and an existing item; entering such a status
        without one, stored or given, is refused (``--force`` never waives that); leaving one
        clears the pointer.
        """
        deferred_statuses = self.spec.subentity_deferred_statuses(kind)
        in_deferred = sub.status in deferred_statuses
        if deferred_to is not None:
            if not deferred_statuses:
                raise SquadsError(
                    f"{kind}s have no deferred status, so --deferred-to / deferred_to cannot apply"
                )
            if not in_deferred:
                choices = ", ".join(sorted(deferred_statuses))
                raise SquadsError(
                    f"a carrier (--deferred-to / deferred_to) applies to a {kind} in a deferred "
                    f"status ({choices}); "
                    f"{sub.local_id} is {sub.status}"
                )
            carrier = require_item(db, deferred_to)
            if carrier.id == item.id:
                raise SquadsError(f"{item.id} cannot carry its own {kind}'s work")
            if self.spec.item_is_roster(carrier.type):
                raise SquadsError(
                    f"{carrier.id} is a {carrier.type}, not an item that carries work"
                )
            sub.deferred_to = carrier.id
        elif moved and not in_deferred:
            sub.deferred_to = None
        if moved and in_deferred and sub.deferred_to is None:
            raise SquadsError(
                f"{sub.local_id} cannot be {sub.status} without the item that carries the "
                "work; pass --deferred-to <ID> (import: deferred_to)"
            )

    async def _set_block_assignee(
        self, parent_id: str, kind: str, local_id: str, assignee: str | None
    ) -> None:
        """Opens its own transaction, then delegates to :meth:`_set_block_assignee_core` —
        the bulk importer calls that core directly (its own transaction is already open)."""
        async with self.store.transaction() as db:
            await self._set_block_assignee_core(db, parent_id, kind, local_id, assignee)

    def _set_block_assignee_model(
        self,
        db: SquadsDB,
        parent_id: str,
        kind: str,
        local_id: str,
        assignee: str | None,
        *,
        now: datetime | None = None,
    ) -> tuple[Item, SubEntity, Item]:
        """The PURE half of a sub-entity assignee change: no file I/O. Returns ``(item, sub,
        base)`` — ``base`` is *item* as loaded, before this call's own delta.

        Shared by :meth:`_set_block_assignee_core` (the interactive/apply path) and the bulk
        importer's pre-pass, which calls this directly against a throwaway ``db`` copy.
        """
        self._check_assignee(db, assignee)
        item = self._require_parent(db, parent_id, kind)
        sub = self._find(item, kind, local_id)
        base = item.model_copy(deep=True)
        sub.assignee = assignee
        item.updated_at = now if now is not None else clock.now()
        return item, sub, base

    async def _set_block_assignee_core(
        self, db: SquadsDB, parent_id: str, kind: str, local_id: str, assignee: str | None
    ) -> None:
        """The sub-entity assignee mutation core: takes an already-open transaction's ``db``."""
        item, sub, base = self._set_block_assignee_model(db, parent_id, kind, local_id, assignee)
        await self._write_block_file(item, item_file(self.paths, item), sub=sub, base=base)
        self.store.log(
            "subentity",
            item.id,
            {"op": "assignee", "kind": kind, "local_id": local_id, "assignee": assignee},
        )

    async def update_block(  # noqa: PLR0913 — the sub-entity metadata entry point, like item `update`
        self,
        parent_id: str,
        kind: str,
        local_id: str,
        *,
        title: str | None = None,
        fields: dict[str, str] | None = None,
        story: str | None = None,
        clear_story: bool = False,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: str | None = None,
        deferred_to: str | None = None,
        force: bool = False,
    ) -> None:
        """Opens its own transaction, then delegates to :meth:`_update_block_core` — the bulk
        importer calls that core directly (its own transaction is already open)."""
        async with self.store.transaction() as db:
            await self._update_block_core(
                db,
                parent_id,
                kind,
                local_id,
                title=title,
                fields=fields,
                story=story,
                clear_story=clear_story,
                assignee=assignee,
                clear_assignee=clear_assignee,
                status=status,
                deferred_to=deferred_to,
                force=force,
            )

    async def _update_block_core(  # noqa: PLR0913 — mirrors `update_block`'s own keyword surface
        self,
        db: SquadsDB,
        parent_id: str,
        kind: str,
        local_id: str,
        *,
        title: str | None = None,
        fields: dict[str, str] | None = None,
        story: str | None = None,
        clear_story: bool = False,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: str | None = None,
        deferred_to: str | None = None,
        force: bool = False,
    ) -> None:
        """The sub-entity metadata-update mutation core: takes an already-open ``db``."""
        if title is not None:
            title = subentity_title(title)
            reject_markers(title, "title")
        item = self._require_parent(db, parent_id, kind)
        sub = self._find(item, kind, local_id)
        base = item.model_copy(deep=True)
        if title is not None:
            sub.title = title
        for code, value in self._checked_field_values(kind, fields).items():
            sub.set_badge_value(code, value)
        if clear_story:
            sub.story = None
        elif story is not None:
            self._check_maps_parent_story(kind)
            self._validate_subtask_story(db, item, story)
            sub.story = story
        if clear_assignee:
            sub.assignee = None
        elif assignee is not None:
            self._check_assignee(db, assignee)
            sub.assignee = assignee
        if status is not None:
            self._apply_subentity_status(kind, sub, status, force=force)
        self._settle_deferral(
            db, kind, item, sub, moved=status is not None, deferred_to=deferred_to
        )
        item.updated_at = clock.now()
        await self._write_block_file(item, item_file(self.paths, item), sub=sub, base=base)
        self.store.log(
            "subentity",
            item.id,
            {"op": "update", "kind": kind, "local_id": local_id},
        )

    def _block_body_mutate(
        self, kind: str, local_id: str, body: str, *, append: bool, force: bool = False
    ) -> Callable[[str, Item], tuple[str, bool]]:
        """Build the ``mutate(text, item)`` closure :meth:`set_block_body` applies through the
        shared section-edit core, so the bulk importer's ``sub-body`` op runs the same logic. Sub-
        entity prose has no regeneration path, so it carries the item body's replace guard
        (:func:`~squads._services._base.reject_body_overwrite`), with the block's placeholder line
        as the "nothing written yet" value.
        """
        reject_markers(body)
        btag = discussion.body_tag(kind, local_id)

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            self._check_type(item, kind)
            self._find(item, kind, local_id)  # ensure it exists
            if sections.get_section(text, btag) is None:
                missing = (
                    btag
                    if sections.has_section(text, f"{kind}:{local_id}")
                    else (f"{kind}:{local_id}")
                )
                raise SquadsError(
                    f"{item.id} {local_id} has no {markers.PREFIX}{missing} region in its file; "
                    "restore the marker pair, for example from git. Nothing was written"
                )
            current = (sections.get_section(text, btag) or "").strip("\n")
            authored = bool(current) and current.strip() != discussion.body_placeholder(
                kind, self.spec
            )
            new_body = body
            if append:
                if authored:
                    new_body = f"{current}\n\n{body}"
            elif authored and not force:
                reject_body_overwrite(f"{item.id} {local_id}", current)
            delta: dict[str, object] = {"op": "body", "kind": kind, "local_id": local_id}
            if authored and not append:
                delta["replaced_lines"] = len(current.splitlines())
            self.store.log("subentity", item.id, delta)
            return sections.replace_section(text, btag, new_body), True

        return mutate

    async def set_block_body(
        self,
        parent_id: str,
        kind: str,
        local_id: str,
        body: str,
        *,
        append: bool,
        force: bool = False,
    ) -> None:
        mutate = self._block_body_mutate(kind, local_id, body, append=append, force=force)
        await self._locked_section_edit(parent_id, mutate)

    async def remove_block(self, parent_id: str, kind: str, local_id: str) -> None:
        """Hard-delete a sub-entity: drop it from ``item.subentities`` and excise its span
        (:func:`sections.remove_section`, marker-safe), atomically in one ``store.transaction()``
        with a reflog entry. A removed id below the highest stays a gap, but removing the highest
        frees its number for reissue (:func:`discussion.next_local_id`). Removing a kind another
        kind's ``maps_parent_story`` targets is refused while a subtask still maps to it.
        """
        async with self.store.transaction() as db:
            item = self._require_parent(db, parent_id, kind)
            sub = self._find(item, kind, local_id)
            base = item.model_copy(deep=True)
            if self._kind_is_story_target(item.type):
                dependents = self._dependent_subtasks(db, item, local_id)
                if dependents:
                    listed = ", ".join(f"{task.id} {s.local_id}" for task, s in dependents)
                    raise SquadsError(
                        f"cannot remove {local_id}: subtasks still map to it: {listed}. "
                        "Remap (--story) or remove those subtasks first."
                    )
            item.subentities = [s for s in item.subentities if s.local_id != local_id]
            item.updated_at = clock.now()
            await self._refuse_duplicated_ids(item)
            path = item_file(self.paths, item)
            text = await self._read_item_file(item, path)
            ensure_no_skew(text, base, default_kind=self.spec.default_ref_kind())
            text = sections.remove_section(text, f"{kind}:{local_id}")
            text = sections.replace_frontmatter(text, item.to_frontmatter_dict())
            await self._write_item_file(path, text)
            self.store.log(
                "subentity",
                item.id,
                {
                    "op": "remove",
                    "kind": kind,
                    "local_id": local_id,
                    "title": sub.title,
                    "status": sub.status,
                },
            )

    def _dependent_subtasks(
        self, db: SquadsDB, feature: Item, story_local_id: str
    ) -> list[tuple[Item, SubEntity]]:
        """``(task, subtask)`` pairs, across *feature*'s child tasks, still mapped to
        *story_local_id* — the guard :meth:`remove_block` applies before dropping a story."""
        deps: list[tuple[Item, SubEntity]] = []
        for child_id in db.children(feature.id):
            child = db.get(child_id)
            if child is None:
                continue
            deps.extend((child, s) for s in child.subentities if s.story == story_local_id)
        return deps

    async def get_block(self, parent_id: str, kind: str, local_id: str) -> SubentityDetail:
        item = await self.get(parent_id)
        self._check_type(item, kind)
        sub = self._find(item, kind, local_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        body = (sections.get_section(text, discussion.body_tag(kind, local_id)) or "").strip("\n")
        disc = (
            sections.get_section(text, markers.discussion_tag(f"{kind}:{local_id}")) or ""
        ).strip("\n")
        comments = discussion.split_discussion(
            disc, sequence_id=item.sequence_id, scope=f"{kind}:{local_id}"
        )
        carrier = (await self.store.load()).get(sub.deferred_to) if sub.deferred_to else None
        return SubentityDetail(
            info=sub,
            body=body,
            discussion=disc,
            comments=comments,
            carrier_title=carrier.title if carrier else None,
        )

    async def _write_block_file(
        self,
        item: Item,
        path: Path,
        *,
        text: str | None = None,
        sub: SubEntity,
        base: Item,
    ) -> None:
        """Persist the item's frontmatter from the model and re-render *sub*'s block heading; the
        ``:head`` and ``:summary`` renderings are computed on request. *base* is *item* as loaded
        before the caller's delta, checked against the on-disk frontmatter in ``text`` before it is
        replaced.
        """
        kind = self.subentity_kind[item.type]
        await self._refuse_duplicated_ids(item)
        text = await self._read_item_file(item, path) if text is None else text
        ensure_no_skew(text, base, default_kind=self.spec.default_ref_kind())
        text = sections.replace_frontmatter(text, item.to_frontmatter_dict())
        text = discussion.set_heading(text, kind, sub.local_id, sub.title)
        await self._write_item_file(path, text)

    def _validate_subtask_story(self, db: SquadsDB, task: Item, story: str) -> None:
        required = self.spec.item_parent_required(task.type)
        host = required or "parent"
        if not task.parent:
            raise SquadsError(
                f"{task.id} has no {host} parent; set one before mapping a subtask to {story}"
            )
        parent = db.get(task.parent)
        if parent is None or (required is not None and parent.type != required):
            kind = parent.type if parent else "missing parent"
            raise SquadsError(f"{task.id}'s parent is a {kind}, not a {host}")
        if story not in {s.local_id for s in parent.subentities}:
            raise SquadsError(f"user story {story} not found in {parent.id}")

    def _require_parent(self, db: SquadsDB, parent_id: str, kind: str) -> Item:
        item = require_item(db, parent_id)
        self._check_type(item, kind)
        return item

    def _container_for(self, kind: str) -> str:
        """The container marker tag for *kind*, or a clean ``SquadsError`` — never a bare
        ``KeyError`` — when *kind* names no declared sub-entity kind at all (e.g. a stale
        CLI registration, or a bulk-import event citing a typo'd/dropped kind). A ``kind``
        that IS declared but not hosted by the item in hand is a separate, better-worded
        refusal from :meth:`_check_type`; this only guards the dict lookup itself."""
        container = self.subentity_container.get(kind)
        if container is None:
            raise SquadsError(f"{kind!r} is not a declared sub-entity kind")
        return container

    def _check_type(self, item: Item, kind: str) -> None:
        # Forward, 1:1 check (spec.item_subentity_kind) — never resolve ownership by
        # inverting kind->type, which collapses when two types share a kind.
        hosts = self.spec.item_subentity_kind(item.type)
        if hosts == kind:
            return
        hint = f" ({item.type}s host {hosts}s)" if hosts else ""
        raise SquadsError(f"{item.id} is a {item.type}, which does not host {kind}s{hint}")

    def _check_maps_parent_story(self, kind: str) -> None:
        """Raise unless *kind* declares the ``maps_parent_story`` capability — the
        feature/story mapping stays a bounded built-in, gated by the flag rather than
        a ``kind == "subtask"`` literal."""
        ks = self.spec.subentity_kinds.get(kind)
        if ks is None or not ks.maps_parent_story:
            raise SquadsError(f"{kind} sub-entities don't map to a parent story")

    def _kind_is_story_target(self, item_type: str) -> bool:
        """True when some other item type's hosted sub-entity kind declares ``maps_parent_story``
        and maps onto *item_type*'s hosted kind, so removing one of those could orphan a mapped
        child's reference. The flag is on the mapping (child) kind, so this walks every declared
        type, however either kind is named.
        """
        for other_type, ts in self.spec.items.items():
            child_kind = ts.subentity_kind
            if child_kind is None:
                continue
            ks = self.spec.subentity_kinds.get(child_kind)
            if (
                ks is not None
                and ks.maps_parent_story
                and self.spec.item_parent_required(other_type) == item_type
            ):
                return True
        return False

    @staticmethod
    def _find(item: Item, kind: str, local_id: str) -> SubEntity:
        for s in item.subentities:
            if s.local_id == local_id:
                return s
        raise SquadsError(f"no {kind} {local_id} in {item.id}")
