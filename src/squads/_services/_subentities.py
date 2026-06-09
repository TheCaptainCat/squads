"""Sub-entities: user stories, subtasks, and review findings (scaffold + status machine).

Their machine state (status/assignee/severity/story) lives in the parent item's frontmatter as
``Item.subentities``; this layer mutates that model (atomically, via the index transaction) and
re-renders the body's presentation regions (``:head`` per block, the parent's ``:summary`` table).
Each sub-entity's prose (``:body`` + ``:discussion``) stays marker-owned in the body.
"""

from pathlib import Path

from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._models import _markers as markers
from squads._models._enums import DEFAULT_SEVERITY, ItemType, Severity, Status
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._services._base import (
    SUBENTITY_CONTAINER,
    SUBENTITY_KIND,
    SUBENTITY_PARENT,
    ServiceCore,
)
from squads._services._results import BlockResult, SubentityDetail
from squads._workflow import subentity_can_transition, subentity_initial


class SubentitiesMixin(ServiceCore):
    def add_story(
        self,
        feature_id: str,
        title: str = "",
        *,
        assignee: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        return self._add_block(feature_id, "story", title, assignee=assignee, body=body)

    def add_subtask(
        self,
        task_id: str,
        title: str = "",
        *,
        story: str | None = None,
        assignee: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        return self._add_block(task_id, "subtask", title, story=story, assignee=assignee, body=body)

    def add_finding(
        self,
        review_id: str,
        title: str = "",
        *,
        severity: Severity = DEFAULT_SEVERITY,
        assignee: str | None = None,
        body: str | None = None,
    ) -> BlockResult:
        return self._add_block(
            review_id, "finding", title, severity=severity, assignee=assignee, body=body
        )

    def _add_block(
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
        if body is not None:
            self._reject_markers(body)
        with self.store.transaction() as db:
            item = self._require_parent(db, item_id, kind, expect)
            self._check_assignee(db, assignee)
            if kind == "subtask" and story:
                self._validate_subtask_story(db, item, story)
            path = item_file(self.paths, item)
            text = path.read_text(encoding="utf-8")
            if not sections.has_section(text, container):
                raise SquadsError(f"no {container} section in {item_id}")
            local_id = discussion.next_local_id(item.subentities, kind)
            sub = SubEntity(
                local_id=local_id,
                title=title,
                status=subentity_initial(kind),
                assignee=assignee,
                severity=severity,
                story=story,
            )
            item.subentities.append(sub)
            item.updated_at = clock.now()
            block = discussion.build_block(kind, local_id, title, body=body)
            text = sections.append_to_section(text, container, block)
            self._write_block_file(db, item, path, text=text, head_for=sub)
        btag = discussion.body_tag(kind, local_id)
        span = sections.region_lines(path.read_text(encoding="utf-8"), btag)
        return BlockResult(
            local_id=local_id,
            path=path,
            body_tag=btag,
            start_line=span[0] if span else None,
            end_line=span[1] if span else None,
        )

    def list_stories(self, feature_id: str) -> list[SubEntity]:
        return self._list_blocks(feature_id, "story")

    def list_subtasks(self, task_id: str) -> list[SubEntity]:
        return self._list_blocks(task_id, "subtask")

    def list_findings(self, review_id: str) -> list[SubEntity]:
        return self._list_blocks(review_id, "finding")

    def _list_blocks(self, parent_id: str, kind: str) -> list[SubEntity]:
        item = self.get(parent_id)
        self._check_type(item, kind)
        return item.subentities

    def set_subtask_status(self, task_id: str, local_id: str, status: Status, **kw: bool) -> None:
        self._set_block_status(task_id, "subtask", local_id, status, **kw)

    def set_story_status(self, feature_id: str, local_id: str, status: Status, **kw: bool) -> None:
        self._set_block_status(feature_id, "story", local_id, status, **kw)

    def set_finding_status(self, review_id: str, local_id: str, status: Status, **kw: bool) -> None:
        self._set_block_status(review_id, "finding", local_id, status, **kw)

    def set_subtask_done(self, task_id: str, local_id: str, *, done: bool = True) -> None:
        # convenience toggle (forces past intermediate states, like the old checkbox)
        self._set_block_status(
            task_id, "subtask", local_id, Status.DONE if done else Status.TODO, force=True
        )

    def set_subtask_assignee(self, task_id: str, local_id: str, assignee: str | None) -> None:
        self._set_block_assignee(task_id, "subtask", local_id, assignee)

    def set_story_assignee(self, feature_id: str, local_id: str, assignee: str | None) -> None:
        self._set_block_assignee(feature_id, "story", local_id, assignee)

    def set_finding_assignee(self, review_id: str, local_id: str, assignee: str | None) -> None:
        self._set_block_assignee(review_id, "finding", local_id, assignee)

    def set_subtask_body(
        self, task_id: str, local_id: str, body: str, *, append: bool = False
    ) -> None:
        self._set_block_body(task_id, "subtask", local_id, body, append=append)

    def set_story_body(
        self, feature_id: str, local_id: str, body: str, *, append: bool = False
    ) -> None:
        self._set_block_body(feature_id, "story", local_id, body, append=append)

    def set_finding_body(
        self, review_id: str, local_id: str, body: str, *, append: bool = False
    ) -> None:
        self._set_block_body(review_id, "finding", local_id, body, append=append)

    def update_story(
        self,
        feature_id: str,
        local_id: str,
        *,
        title: str | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: Status | None = None,
        force: bool = False,
    ) -> None:
        self._update_block(
            feature_id,
            "story",
            local_id,
            title=title,
            assignee=assignee,
            clear_assignee=clear_assignee,
            status=status,
            force=force,
        )

    def update_subtask(  # noqa: PLR0913 — full metadata entry point for a subtask
        self,
        task_id: str,
        local_id: str,
        *,
        title: str | None = None,
        story: str | None = None,
        clear_story: bool = False,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: Status | None = None,
        force: bool = False,
    ) -> None:
        self._update_block(
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

    def update_finding(
        self,
        review_id: str,
        local_id: str,
        *,
        title: str | None = None,
        severity: Severity | None = None,
        assignee: str | None = None,
        clear_assignee: bool = False,
        status: Status | None = None,
        force: bool = False,
    ) -> None:
        self._update_block(
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

    def get_subtask(self, task_id: str, local_id: str) -> SubentityDetail:
        return self._get_block(task_id, "subtask", local_id)

    def get_story(self, feature_id: str, local_id: str) -> SubentityDetail:
        return self._get_block(feature_id, "story", local_id)

    def get_finding(self, review_id: str, local_id: str) -> SubentityDetail:
        return self._get_block(review_id, "finding", local_id)

    # ------------------------------------------------------------------ helpers
    def _set_block_status(
        self, parent_id: str, kind: str, local_id: str, status: Status, *, force: bool = False
    ) -> None:
        with self.store.transaction() as db:
            item = self._require_parent(db, parent_id, kind, SUBENTITY_PARENT[kind])
            sub = self._find(item, kind, local_id)
            self._apply_subentity_status(kind, sub, status, force=force)
            item.updated_at = clock.now()
            self._write_block_file(db, item, item_file(self.paths, item), head_for=sub)

    @staticmethod
    def _apply_subentity_status(kind: str, sub: SubEntity, status: Status, *, force: bool) -> None:
        current = sub.status
        if not force and current != status and not subentity_can_transition(kind, current, status):
            raise InvalidTransitionError(
                f"{kind} {sub.local_id} cannot move {current.value} → {status.value}"
                " (use --force to override)"
            )
        sub.status = status

    def _set_block_assignee(
        self, parent_id: str, kind: str, local_id: str, assignee: str | None
    ) -> None:
        with self.store.transaction() as db:
            self._check_assignee(db, assignee)
            item = self._require_parent(db, parent_id, kind, SUBENTITY_PARENT[kind])
            sub = self._find(item, kind, local_id)
            sub.assignee = assignee
            item.updated_at = clock.now()
            self._write_block_file(db, item, item_file(self.paths, item), head_for=sub)

    def _update_block(  # noqa: PLR0913 — the sub-entity metadata entry point, like item `update`
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
        status: Status | None = None,
        force: bool = False,
    ) -> None:
        with self.store.transaction() as db:
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
            self._write_block_file(db, item, item_file(self.paths, item), head_for=sub)

    def _set_block_body(
        self, parent_id: str, kind: str, local_id: str, body: str, *, append: bool
    ) -> None:
        self._reject_markers(body)
        item = self.get(parent_id)
        self._check_type(item, kind)
        self._find(item, kind, local_id)  # ensure it exists
        path = item_file(self.paths, item)
        text = path.read_text(encoding="utf-8")
        btag = discussion.body_tag(kind, local_id)
        if append:
            current = (sections.get_section(text, btag) or "").strip("\n")
            if current and current.strip() != discussion.body_placeholder(kind):
                body = f"{current}\n\n{body}"
        path.write_text(sections.replace_section(text, btag, body), encoding="utf-8")
        self._bump(parent_id)

    def _get_block(self, parent_id: str, kind: str, local_id: str) -> SubentityDetail:
        item = self.get(parent_id)
        self._check_type(item, kind)
        sub = self._find(item, kind, local_id)
        text = item_file(self.paths, item).read_text(encoding="utf-8")
        body = (sections.get_section(text, discussion.body_tag(kind, local_id)) or "").strip("\n")
        disc = (
            sections.get_section(text, markers.discussion_tag(f"{kind}:{local_id}")) or ""
        ).strip("\n")
        return SubentityDetail(info=sub, body=body, discussion=disc)

    def _write_block_file(
        self, db: SquadsDB, item: Item, path: Path, *, text: str | None = None, head_for: SubEntity
    ) -> None:
        """Persist the item's frontmatter from the model + re-render its block's head + summary."""
        kind, container = SUBENTITY_KIND[item.type], SUBENTITY_CONTAINER[SUBENTITY_KIND[item.type]]
        text = path.read_text(encoding="utf-8") if text is None else text
        text = sections.replace_frontmatter(text, item.to_frontmatter_dict())
        text = discussion.set_heading(text, kind, head_for.local_id, head_for.title)
        text = self._refresh_head(text, db, item, kind, head_for)
        text = discussion.ensure_summary(text, kind, container, item.subentities)
        path.write_text(text, encoding="utf-8")

    def _refresh_head(self, text: str, db: SquadsDB, item: Item, kind: str, sub: SubEntity) -> str:
        """Re-render the block's ``:head`` from its current state (resolving slugs/story titles)."""
        return discussion.set_head(
            text,
            kind,
            sub.local_id,
            status=sub.status.value,
            severity=sub.severity.value if sub.severity else None,
            story=self._story_label(db, item, sub.story),
            assignee_name=self.author(sub.assignee) if sub.assignee else None,
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
        if parent is None or parent.type is not ItemType.FEATURE:
            kind = parent.type.value if parent else "missing parent"
            raise SquadsError(f"{task.id}'s parent is a {kind}, not a feature")
        if story not in {s.local_id for s in parent.subentities}:
            raise SquadsError(f"user story {story} not found in {parent.id}")

    def _require_parent(self, db: SquadsDB, parent_id: str, kind: str, expect: ItemType) -> Item:
        item = require_item(db, parent_id)
        if item.type is not expect:
            raise SquadsError(
                f"{parent_id} is a {item.type.value}; {kind}s live on a {expect.value}"
            )
        return item

    @staticmethod
    def _check_type(item: Item, kind: str) -> None:
        expect = SUBENTITY_PARENT[kind]
        if item.type is not expect:
            raise SquadsError(f"{item.id} is a {item.type.value}; {kind}s live on a {expect.value}")

    @staticmethod
    def _find(item: Item, kind: str, local_id: str) -> SubEntity:
        for s in item.subentities:
            if s.local_id == local_id:
                return s
        raise SquadsError(f"no {kind} {local_id} in {item.id}")

    @staticmethod
    def _reject_markers(body: str) -> None:
        if sections.find_markers(body):
            raise SquadsError("body must not contain sq marker comments (<!-- sq:… -->)")
