"""Sub-entities: user stories, subtasks, and review findings (scaffold + status machine).

Their machine state (status/assignee/severity/story) lives in the parent item's frontmatter as
``Item.subentities``; this layer mutates that model (atomically, via the index transaction) and
re-renders the body's presentation regions (``:head`` per block, the parent's ``:summary`` table).
Each sub-entity's prose (``:body`` + ``:discussion``) stays marker-owned in the body.
"""

from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._interactions import TITLE_ADVISORY_MAX
from squads._models import _markers as markers
from squads._models._enums import DEFAULT_SEVERITY, Severity, Status
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._services._base import (
    SUBENTITY_CONTAINER,
    SUBENTITY_KIND,
    SUBENTITY_PARENT,
    ServiceCore,
    reject_markers,
)
from squads._services._results import BlockResult, SubentityDetail


class SubentitiesMixin(ServiceCore):
    async def add_story(
        self,
        feature_id: str,
        title: str = "",
        *,
        assignee: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        return await self._add_block(feature_id, "story", title, assignee=assignee, body=body)

    async def add_subtask(
        self,
        task_id: str,
        title: str = "",
        *,
        story: str | None = None,
        assignee: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        return await self._add_block(
            task_id, "subtask", title, story=story, assignee=assignee, body=body
        )

    async def add_finding(
        self,
        review_id: str,
        title: str = "",
        *,
        severity: Severity = DEFAULT_SEVERITY,
        assignee: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        return await self._add_block(
            review_id, "finding", title, severity=severity, assignee=assignee, body=body
        )

    async def _add_block(
        self,
        item_id: str,
        kind: str,
        title: str,
        *,
        story: str | None = None,
        severity: Severity | None = None,
        assignee: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        expect, container = SUBENTITY_PARENT[kind], SUBENTITY_CONTAINER[kind]
        reject_markers(title, "title")
        if body is not None:
            reject_markers(body)
        async with self.store.transaction() as db:
            item = self._require_parent(db, item_id, kind, expect)
            self._check_assignee(db, assignee)
            if kind == "subtask" and story:
                self._validate_subtask_story(db, item, story)
            path = item_file(self.paths, item)
            text = await _aio.read_text(path)
            if not sections.has_section(text, container):
                raise SquadsError(f"no {container} section in {item_id}")
            local_id = discussion.next_local_id(item.subentities, kind)
            sub = SubEntity(
                local_id=local_id,
                title=title,
                status=self.spec.subentity_initial(kind),
                assignee=assignee,
                severity=severity,
                story=story,
            )
            item.subentities.append(sub)
            item.updated_at = clock.now()
            block = discussion.build_block(kind, local_id, title, body=body)
            text = sections.append_to_section(text, container, block)
            await self._write_block_file(db, item, path, text=text, head_for=sub)
            # Advisory title-length check (ADR-000167 / FEAT-000166).
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
        return await self._list_blocks(feature_id, "story")

    async def list_subtasks(self, task_id: str) -> list[SubEntity]:
        return await self._list_blocks(task_id, "subtask")

    async def list_findings(self, review_id: str) -> list[SubEntity]:
        return await self._list_blocks(review_id, "finding")

    async def _list_blocks(self, parent_id: str, kind: str) -> list[SubEntity]:
        item = await self.get(parent_id)
        self._check_type(item, kind)
        return item.subentities

    async def set_subtask_status(
        self, task_id: str, local_id: str, status: str, **kw: bool
    ) -> None:
        await self._set_block_status(task_id, "subtask", local_id, status, **kw)

    async def set_story_status(
        self, feature_id: str, local_id: str, status: str, **kw: bool
    ) -> None:
        await self._set_block_status(feature_id, "story", local_id, status, **kw)

    async def set_finding_status(
        self, review_id: str, local_id: str, status: str, **kw: bool
    ) -> None:
        await self._set_block_status(review_id, "finding", local_id, status, **kw)

    async def set_subtask_done(self, task_id: str, local_id: str, *, done: bool = True) -> None:
        # convenience toggle (forces past intermediate states, like the old checkbox)
        await self._set_block_status(
            task_id, "subtask", local_id, Status.DONE if done else Status.TODO, force=True
        )

    async def set_subtask_assignee(self, task_id: str, local_id: str, assignee: str | None) -> None:
        await self._set_block_assignee(task_id, "subtask", local_id, assignee)

    async def set_story_assignee(
        self, feature_id: str, local_id: str, assignee: str | None
    ) -> None:
        await self._set_block_assignee(feature_id, "story", local_id, assignee)

    async def set_finding_assignee(
        self, review_id: str, local_id: str, assignee: str | None
    ) -> None:
        await self._set_block_assignee(review_id, "finding", local_id, assignee)

    async def set_subtask_body(
        self, task_id: str, local_id: str, body: str, *, append: bool = False
    ) -> None:
        await self._set_block_body(task_id, "subtask", local_id, body, append=append)

    async def set_story_body(
        self, feature_id: str, local_id: str, body: str, *, append: bool = False
    ) -> None:
        await self._set_block_body(feature_id, "story", local_id, body, append=append)

    async def set_finding_body(
        self, review_id: str, local_id: str, body: str, *, append: bool = False
    ) -> None:
        await self._set_block_body(review_id, "finding", local_id, body, append=append)

    async def update_story(
        self,
        feature_id: str,
        local_id: str,
        *,
        title: str | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: str | None = None,
        force: bool = False,
    ) -> None:
        await self._update_block(
            feature_id,
            "story",
            local_id,
            title=title,
            assignee=assignee,
            clear_assignee=clear_assignee,
            status=status,
            force=force,
        )

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
        await self._update_block(
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
        severity: Severity | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: str | None = None,
        force: bool = False,
    ) -> None:
        await self._update_block(
            review_id,
            "finding",
            local_id,
            title=title,
            severity=severity,
            assignee=assignee,
            clear_assignee=clear_assignee,
            status=status,
            force=force,
        )

    async def get_subtask(self, task_id: str, local_id: str) -> SubentityDetail:
        return await self._get_block(task_id, "subtask", local_id)

    async def get_story(self, feature_id: str, local_id: str) -> SubentityDetail:
        return await self._get_block(feature_id, "story", local_id)

    async def get_finding(self, review_id: str, local_id: str) -> SubentityDetail:
        return await self._get_block(review_id, "finding", local_id)

    # ------------------------------------------------------------------ helpers
    async def _set_block_status(
        self, parent_id: str, kind: str, local_id: str, status: str, *, force: bool = False
    ) -> None:
        async with self.store.transaction() as db:
            item = self._require_parent(db, parent_id, kind, SUBENTITY_PARENT[kind])
            sub = self._find(item, kind, local_id)
            old_status = sub.status
            self._apply_subentity_status(kind, sub, status, force=force)
            item.updated_at = clock.now()
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

    def _apply_subentity_status(
        self, kind: str, sub: SubEntity, status: str, *, force: bool
    ) -> None:
        # Coerce to plain str — callers may pass a Status StrEnum member
        # (use_enum_values=False prevents auto-coercion).
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
        async with self.store.transaction() as db:
            self._check_assignee(db, assignee)
            item = self._require_parent(db, parent_id, kind, SUBENTITY_PARENT[kind])
            sub = self._find(item, kind, local_id)
            sub.assignee = assignee
            item.updated_at = clock.now()
            await self._write_block_file(db, item, item_file(self.paths, item), head_for=sub)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "subentity",
                item.id,
                {"op": "assignee", "kind": kind, "local_id": local_id, "assignee": assignee},
            )

    async def _update_block(  # noqa: PLR0913 — the sub-entity metadata entry point, like item `update`
        self,
        parent_id: str,
        kind: str,
        local_id: str,
        *,
        title: str | None = None,
        severity: Severity | None = None,
        story: str | None = None,
        clear_story: bool = False,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: str | None = None,
        force: bool = False,
    ) -> None:
        if title is not None:
            reject_markers(title, "title")
        async with self.store.transaction() as db:
            item = self._require_parent(db, parent_id, kind, SUBENTITY_PARENT[kind])
            sub = self._find(item, kind, local_id)
            if title is not None:
                sub.title = title
            if severity is not None:
                sub.severity = severity
            if clear_story:
                sub.story = None
            elif story is not None:
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

    async def _set_block_body(
        self, parent_id: str, kind: str, local_id: str, body: str, *, append: bool
    ) -> None:
        reject_markers(body)
        btag = discussion.body_tag(kind, local_id)

        def mutate(text: str, item: Item) -> str:
            self._check_type(item, kind)
            self._find(item, kind, local_id)  # ensure it exists
            new_body = body
            if append:
                current = (sections.get_section(text, btag) or "").strip("\n")
                if current and current.strip() != discussion.body_placeholder(kind):
                    new_body = f"{current}\n\n{body}"
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "subentity",
                item.id,
                {"op": "body", "kind": kind, "local_id": local_id},
            )
            return sections.replace_section(text, btag, new_body)

        await self._locked_section_edit(parent_id, mutate)

    async def _get_block(self, parent_id: str, kind: str, local_id: str) -> SubentityDetail:
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
        kind, container = SUBENTITY_KIND[item.type], SUBENTITY_CONTAINER[SUBENTITY_KIND[item.type]]
        text = await _aio.read_text(path) if text is None else text
        text = sections.replace_frontmatter(text, item.to_frontmatter_dict())
        text = discussion.set_heading(text, kind, head_for.local_id, head_for.title)
        text = await self._refresh_head(text, db, item, kind, head_for)
        text = discussion.ensure_summary(text, kind, container, item.subentities)
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
            severity=sub.severity.value if sub.severity else None,
            story=self._story_label(db, item, sub.story),
            assignee_name=await self.author(sub.assignee) if sub.assignee else None,
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
        if not task.parent:
            raise SquadsError(
                f"{task.id} has no feature parent; set one before mapping a subtask to {story}"
            )
        parent = db.get(task.parent)
        required = self.spec.item_parent_required(task.type)
        if parent is None or (required is not None and parent.type != required):
            kind = parent.type if parent else "missing parent"
            raise SquadsError(f"{task.id}'s parent is a {kind}, not a feature")
        if story not in {s.local_id for s in parent.subentities}:
            raise SquadsError(f"user story {story} not found in {parent.id}")

    def _require_parent(self, db: SquadsDB, parent_id: str, kind: str, expect: str) -> Item:
        item = require_item(db, parent_id)
        if item.type != expect:
            raise SquadsError(f"{parent_id} is a {item.type}; {kind}s live on a {expect}")
        return item

    @staticmethod
    def _check_type(item: Item, kind: str) -> None:
        expect = SUBENTITY_PARENT[kind]
        if item.type != expect:
            raise SquadsError(f"{item.id} is a {item.type}; {kind}s live on a {expect}")

    @staticmethod
    def _find(item: Item, kind: str, local_id: str) -> SubEntity:
        for s in item.subentities:
            if s.local_id == local_id:
                return s
        raise SquadsError(f"no {kind} {local_id} in {item.id}")
