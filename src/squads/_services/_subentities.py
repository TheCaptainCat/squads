"""Sub-entities: user stories, subtasks, and review findings (scaffold + status machine).

Their machine state (status/assignee/severity/story) lives in the parent item's frontmatter as
``Item.subentities``; this layer mutates that model (atomically, via the index transaction) and
re-renders the body's presentation regions (``:head`` per block, the parent's ``:summary`` table).
Each sub-entity's prose (``:body`` + ``:discussion``) stays marker-owned in the body.
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._interactions import TITLE_ADVISORY_MAX
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._services._base import ServiceCore, reject_markers
from squads._services._results import BlockResult, SubentityDetail

#: Last-resort finding-severity fallback — only reached when the active spec's ``finding``
#: kind carries no ``severity`` field at all (a customized spec that dropped it), so
#: ``add_finding`` never crashes for want of a default.
_DEFAULT_FINDING_SEVERITY = "medium"


class SubentitiesMixin(ServiceCore):
    def field_default(self, type_or_kind: str, code: str) -> str | None:
        """The badge code an omitted field falls back to: the field's own ``default``,
        else its collection's ``default``, else ``None`` (generic — no field/collection
        special-cased by name). Public: the CLI's generic add-<kind> builder calls this
        directly for every declared field, not just ``finding``'s ``severity``."""
        field = next((f for f in self.spec.fields_for(type_or_kind) if f.code == code), None)
        if field is None:
            return None
        if field.default:
            return field.default
        coll = self.spec.collections.get(field.collection)
        return coll.default if coll else None

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
        body: str | None = None,
    ) -> BlockResult:
        resolved_severity = (
            severity or self.field_default("finding", "severity") or _DEFAULT_FINDING_SEVERITY
        )
        return await self.add_block(
            review_id,
            "finding",
            title,
            fields={"severity": resolved_severity},
            assignee=assignee,
            status=status,
            body=body,
        )

    # ------------------------------------------------------------------ public kind-taking surface
    # The generic surface below (add_block/list_blocks/get_block/update_block/set_block_body/
    # set_block_status) takes an arbitrary declared kind string, including a project-declared
    # custom one — it is the surface a future CLI dispatch drives directly instead of the
    # per-kind wrappers. The wrappers above stay thin delegators over it for their existing
    # (test) call sites.

    async def add_block(
        self,
        item_id: str,
        kind: str,
        title: str,
        *,
        story: str | None = None,
        fields: dict[str, str] | None = None,
        assignee: str | None = None,
        status: str | None = None,
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
        body: str | None = None,
        now: datetime | None = None,
    ) -> tuple[Item, SubEntity]:
        """The PURE half of scaffolding a sub-entity: every check, the local-id allocation, and
        the ``SubEntity`` itself — no file I/O. Returns ``(item, sub)``.

        Shared by :meth:`_add_block_core` (the interactive/apply path, which appends the
        rendered block to the item's file text around this) and the bulk importer's pre-pass,
        which calls this directly against a throwaway ``db`` copy with ``now=ev.at``.
        """
        reject_markers(title, "title")
        if body is not None:
            reject_markers(body)
        # _require_parent's _check_type validates `kind` against the item's declared
        # subentity_kind FIRST — an unknown/mismatched kind raises a clean SquadsError here.
        # Resolving _resolve_add_status before this would KeyError on a bogus kind instead
        # (self.spec.subentity_kinds[kind] has no fallback), which the bulk importer's
        # pre-pass cannot collect as an ImportIssue (KeyError isn't in _COLLECTIBLE) — it
        # would abort the whole validate-first pass instead of reporting one bad line.
        item = self._require_parent(db, item_id, kind)
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
        # other declared field (SubEntity.extra) — the same dispatch for every code.
        for code, value in (fields or {}).items():
            sub.set_badge_value(code, value)
        item.subentities.append(sub)
        item.updated_at = now if now is not None else clock.now()
        return item, sub

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
        body: str | None = None,
    ) -> BlockResult:
        """The sub-entity-scaffold mutation core: takes an already-open transaction's ``db``."""
        container = self.subentity_container[kind]
        item, sub = self._add_block_model(
            db,
            item_id,
            kind,
            title,
            story=story,
            fields=fields,
            assignee=assignee,
            status=status,
            body=body,
        )
        local_id = sub.local_id
        path = item_file(self.paths, item)
        text = await _aio.read_text(path)
        if not sections.has_section(text, container):
            raise SquadsError(f"no {container} section in {item_id}")
        block = discussion.build_block(kind, local_id, title, body=body, spec=self.spec)
        text = sections.append_to_section(text, container, block)
        await self._write_block_file(db, item, path, text=text, head_for=sub)
        # Advisory title-length check.
        # Fires when title length > TITLE_ADVISORY_MAX.  Service must NOT print;
        # the warning rides back on the result to be rendered at the CLI edge.
        title_advisory: str | None = None
        if len(title) > TITLE_ADVISORY_MAX:
            body_cmd = f'sq {item.type} {item.sequence_id} {kind} {local_id} body -m "…"'
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
        self.store._log(  # pyright: ignore[reportPrivateUsage]
            "subentity",
            item.id,
            log_delta,
        )
        btag = discussion.body_tag(kind, local_id)
        span = sections.region_lines(await _aio.read_text(path), btag)
        return BlockResult(
            local_id=local_id,
            path=path,
            body_tag=btag,
            start_line=span[0] if span else None,
            end_line=span[1] if span else None,
            title_advisory=title_advisory,
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
        # convenience toggle (forces past intermediate states, like the old checkbox).
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
        self, task_id: str, local_id: str, body: str, *, append: bool = False
    ) -> None:
        await self.set_block_body(task_id, "subtask", local_id, body, append=append)

    async def set_story_body(
        self, feature_id: str, local_id: str, body: str, *, append: bool = False
    ) -> None:
        await self.set_block_body(feature_id, "story", local_id, body, append=append)

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

    async def update_finding(
        self,
        review_id: str,
        local_id: str,
        *,
        title: str | None = None,
        severity: str | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: str | None = None,
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
        now: datetime | None = None,
    ) -> tuple[Item, SubEntity, str]:
        """The PURE half of a sub-entity status transition: no file I/O.

        Returns ``(item, sub, old_status)``. Shared by :meth:`_set_block_status_core` (the
        interactive/apply path) and the bulk importer's pre-pass, which calls this directly
        against a throwaway ``db`` copy with ``now=ev.at``.
        """
        item = self._require_parent(db, parent_id, kind)
        sub = self._find(item, kind, local_id)
        old_status = sub.status
        self._apply_subentity_status(kind, sub, status, force=force)
        item.updated_at = now if now is not None else clock.now()
        return item, sub, old_status

    async def _set_block_status_core(
        self,
        db: SquadsDB,
        parent_id: str,
        kind: str,
        local_id: str,
        status: str,
        *,
        force: bool = False,
    ) -> None:
        """The sub-entity status-transition mutation core: takes an already-open ``db``."""
        item, sub, old_status = self._set_block_status_model(
            db, parent_id, kind, local_id, status, force=force
        )
        await self._write_block_file(db, item, item_file(self.paths, item), head_for=sub)
        self.store._log(  # pyright: ignore[reportPrivateUsage]
            "subentity",
            item.id,
            {
                "op": "status",
                "kind": kind,
                "local_id": local_id,
                "status": [old_status, sub.status],
            },
        )

    def _resolve_add_status(self, kind: str, status: str | None) -> str:
        """The status a fresh *kind* sub-entity is seeded with: the kind's own initial state
        when *status* is omitted (unchanged behaviour), else *status* itself — provided it
        names one of that kind's OWN lifecycle states (creation seeds, it does not transition
        from a prior state, so this is a membership check, not ``can_transition``). Scoped to
        the kind's machine, not the spec's global status set, so a status that only exists on
        a different kind's lifecycle is rejected."""
        if status is None:
            return self.spec.subentity_initial(kind)
        valid = self.spec.subentity_workflow(kind).states
        if status not in valid:
            choices = ", ".join(sorted(valid))
            raise SquadsError(f"{status!r} is not a valid {kind} status (one of: {choices})")
        return status

    def _apply_subentity_status(
        self, kind: str, sub: SubEntity, status: str, *, force: bool
    ) -> None:
        # Defensive str() — status is spec vocabulary (a plain string), no enum involved.
        status = str(status)
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
    ) -> tuple[Item, SubEntity]:
        """The PURE half of a sub-entity assignee change: no file I/O. Returns ``(item, sub)``.

        Shared by :meth:`_set_block_assignee_core` (the interactive/apply path) and the bulk
        importer's pre-pass, which calls this directly against a throwaway ``db`` copy.
        """
        self._check_assignee(db, assignee)
        item = self._require_parent(db, parent_id, kind)
        sub = self._find(item, kind, local_id)
        sub.assignee = assignee
        item.updated_at = now if now is not None else clock.now()
        return item, sub

    async def _set_block_assignee_core(
        self, db: SquadsDB, parent_id: str, kind: str, local_id: str, assignee: str | None
    ) -> None:
        """The sub-entity assignee mutation core: takes an already-open transaction's ``db``."""
        item, sub = self._set_block_assignee_model(db, parent_id, kind, local_id, assignee)
        await self._write_block_file(db, item, item_file(self.paths, item), head_for=sub)
        self.store._log(  # pyright: ignore[reportPrivateUsage]
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
        force: bool = False,
    ) -> None:
        """The sub-entity metadata-update mutation core: takes an already-open ``db``."""
        if title is not None:
            reject_markers(title, "title")
        item = self._require_parent(db, parent_id, kind)
        sub = self._find(item, kind, local_id)
        if title is not None:
            sub.title = title
        for code, value in (fields or {}).items():
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
        item.updated_at = clock.now()
        await self._write_block_file(db, item, item_file(self.paths, item), head_for=sub)
        self.store._log(  # pyright: ignore[reportPrivateUsage]
            "subentity",
            item.id,
            {"op": "update", "kind": kind, "local_id": local_id},
        )

    def _block_body_mutate(
        self, kind: str, local_id: str, body: str, *, append: bool
    ) -> Callable[[str, Item], str]:
        """Build the ``mutate(text, item)`` closure :meth:`set_block_body` applies via the
        shared section-edit core — factored out so the bulk importer's ``sub-body`` op can
        drive the exact same logic through
        :meth:`~squads._services._base.ServiceCore._section_edit_core`."""
        reject_markers(body)
        btag = discussion.body_tag(kind, local_id)

        def mutate(text: str, item: Item) -> str:
            self._check_type(item, kind)
            self._find(item, kind, local_id)  # ensure it exists
            new_body = body
            if append:
                current = (sections.get_section(text, btag) or "").strip("\n")
                if current and current.strip() != discussion.body_placeholder(kind, self.spec):
                    new_body = f"{current}\n\n{body}"
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "subentity",
                item.id,
                {"op": "body", "kind": kind, "local_id": local_id},
            )
            return sections.replace_section(text, btag, new_body)

        return mutate

    async def set_block_body(
        self, parent_id: str, kind: str, local_id: str, body: str, *, append: bool
    ) -> None:
        mutate = self._block_body_mutate(kind, local_id, body, append=append)
        await self._locked_section_edit(parent_id, mutate)

    async def remove_block(self, parent_id: str, kind: str, local_id: str) -> None:
        """Hard-delete a story/subtask/finding sub-entity: drop it from ``item.subentities``,
        excise its whole body/head/discussion span marker-safely (:func:`sections.remove_section`
        on the block's own tag removes the nested regions too — they all live between its open
        and matching ``:end`` marker), and re-render the parent's roll-up ``:summary`` table.

        Mirrors ``remove_work_item``'s hard-delete contract (guard/confirmation lives at the CLI
        edge): atomic within one ``store.transaction()``, reflog'd, and the freed local id is
        never reissued to a *different* future sub-entity added later in the same run — see the
        note on :func:`discussion.next_local_id` for the one case that isn't fully covered.

        **Dangling story map:** removing a ``story`` refuses (``SquadsError``) while any subtask
        in a child task still maps to it — findings/subtasks have no such inbound mapping, so the
        check is scoped to ``kind == "story"`` (a bounded built-in, like the mapping itself).
        """
        container = self.subentity_container[kind]
        async with self.store.transaction() as db:
            item = self._require_parent(db, parent_id, kind)
            sub = self._find(item, kind, local_id)
            if kind == "story":
                dependents = self._dependent_subtasks(db, item, local_id)
                if dependents:
                    listed = ", ".join(f"{task.id} {s.local_id}" for task, s in dependents)
                    raise SquadsError(
                        f"cannot remove {local_id}: subtasks still map to it: {listed}. "
                        "Remap (--story) or remove those subtasks first."
                    )
            item.subentities = [s for s in item.subentities if s.local_id != local_id]
            item.updated_at = clock.now()
            path = item_file(self.paths, item)
            text = await _aio.read_text(path)
            text = sections.remove_section(text, f"{kind}:{local_id}")
            text = sections.replace_frontmatter(text, item.to_frontmatter_dict())
            text = discussion.ensure_summary(text, kind, container, item.subentities, self.spec)
            await _aio.write_text(path, text)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
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
        text = await _aio.read_text(item_file(self.paths, item))
        body = (sections.get_section(text, discussion.body_tag(kind, local_id)) or "").strip("\n")
        disc = (
            sections.get_section(text, markers.discussion_tag(f"{kind}:{local_id}")) or ""
        ).strip("\n")
        return SubentityDetail(info=sub, body=body, discussion=disc)

    async def _write_block_file(
        self, db: SquadsDB, item: Item, path: Path, *, text: str | None = None, head_for: SubEntity
    ) -> None:
        """Persist the item's frontmatter from the model + re-render its block's head + summary."""
        kind = self.subentity_kind[item.type]
        container = self.subentity_container[kind]
        text = await _aio.read_text(path) if text is None else text
        text = sections.replace_frontmatter(text, item.to_frontmatter_dict())
        text = discussion.set_heading(text, kind, head_for.local_id, head_for.title)
        text = await self._refresh_head(text, db, item, kind, head_for)
        text = discussion.ensure_summary(text, kind, container, item.subentities, self.spec)
        await _aio.write_text(path, text)

    async def _refresh_head(
        self, text: str, db: SquadsDB, item: Item, kind: str, sub: SubEntity
    ) -> str:
        """Re-render the block's ``:head`` from its current state (resolving slugs/story titles)."""
        return discussion.set_head(
            text,
            kind,
            sub.local_id,
            status=sub.status,
            severity=sub.severity,
            story=self._story_label(db, item, sub.story),
            assignee_name=await self.author(sub.assignee) if sub.assignee else None,
            spec=self.spec,
        )

    def _story_label(self, db: SquadsDB, task: Item, us_id: str | None) -> str | None:
        """A subtask's mapped story as ``USn — title`` (just the id if no title resolves)."""
        if not us_id or not task.parent:
            return us_id
        parent = db.get(task.parent)
        if parent is None:
            return us_id
        title = next((s.title for s in parent.subentities if s.local_id == us_id), "")
        return f"{us_id} — {title}" if title else us_id

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

    @staticmethod
    def _find(item: Item, kind: str, local_id: str) -> SubEntity:
        for s in item.subentities:
            if s.local_id == local_id:
                return s
        raise SquadsError(f"no {kind} {local_id} in {item.id}")
