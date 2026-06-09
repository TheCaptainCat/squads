"""Sub-entities: user stories, subtasks, and review findings (scaffold + status machine)."""

from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError
from squads._index._resolver import item_file
from squads._models._enums import DEFAULT_SEVERITY, ItemType, Severity, Status
from squads._services._base import SUBENTITY_CONTAINER, SUBENTITY_PARENT, ServiceCore
from squads._services._results import BlockResult
from squads._workflow import subentity_can_transition, subentity_initial


class SubentitiesMixin(ServiceCore):
    def add_story(self, feature_id: str, title: str = "") -> BlockResult:
        return self._add_block(feature_id, "story", title)

    def add_subtask(
        self, task_id: str, title: str = "", *, story: str | None = None
    ) -> BlockResult:
        if story:
            self._validate_subtask_story(task_id, story)
        return self._add_block(task_id, "subtask", title, story=story)

    def add_finding(
        self, review_id: str, title: str = "", *, severity: Severity = DEFAULT_SEVERITY
    ) -> BlockResult:
        return self._add_block(review_id, "finding", title, severity=severity)

    def _validate_subtask_story(self, task_id: str, story: str) -> None:
        task = self.get(task_id)
        if not task.parent:
            raise SquadsError(
                f"{task_id} has no feature parent; set one before mapping a subtask to {story}"
            )
        parent = self.get(task.parent)
        if parent.type is not ItemType.FEATURE:
            raise SquadsError(f"{task_id}'s parent is a {parent.type.value}, not a feature")
        stories = {b.local_id for b in discussion.list_blocks(self._read(parent.id), "story")}
        if story not in stories:
            raise SquadsError(f"user story {story} not found in {parent.id}")

    def _add_block(
        self,
        item_id: str,
        kind: str,
        title: str,
        *,
        story: str | None = None,
        severity: Severity | None = None,
    ) -> BlockResult:
        expect, container = SUBENTITY_PARENT[kind], SUBENTITY_CONTAINER[kind]
        item = self.get(item_id)
        if item.type is not expect:
            raise SquadsError(f"{item_id} is a {item.type.value}; {kind}s live on a {expect.value}")
        path = item_file(self.paths, item)
        content = path.read_text(encoding="utf-8")
        if not sections.has_section(content, container):
            raise SquadsError(f"no {container} section in {item_id}")
        local_id = discussion.next_local_id(content, kind)
        block = discussion.build_block(
            kind, local_id, title, status=subentity_initial(kind), severity=severity, story=story
        )
        content = sections.append_to_section(content, container, block)
        content = discussion.ensure_summary(content, kind, container)
        path.write_text(content, encoding="utf-8")
        self._bump(item_id)
        btag = discussion.body_tag(kind, local_id)
        span = sections.region_lines(path.read_text(encoding="utf-8"), btag)
        return BlockResult(
            local_id=local_id,
            path=path,
            body_tag=btag,
            start_line=span[0] if span else None,
            end_line=span[1] if span else None,
        )

    def list_stories(self, feature_id: str) -> list[discussion.BlockInfo]:
        return discussion.list_blocks(self._read(feature_id), "story")

    def list_subtasks(self, task_id: str) -> list[discussion.BlockInfo]:
        return discussion.list_blocks(self._read(task_id), "subtask")

    def list_findings(self, review_id: str) -> list[discussion.BlockInfo]:
        return discussion.list_blocks(self._read(review_id), "finding")

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

    def _set_block_status(
        self, parent_id: str, kind: str, local_id: str, status: Status, *, force: bool = False
    ) -> None:
        item = self.get(parent_id)
        expect, container = SUBENTITY_PARENT[kind], SUBENTITY_CONTAINER[kind]
        if item.type is not expect:
            raise SquadsError(
                f"{parent_id} is a {item.type.value}; {kind}s live on a {expect.value}"
            )
        path = item_file(self.paths, item)
        text = path.read_text(encoding="utf-8")
        blocks = {b.local_id: b for b in discussion.list_blocks(text, kind)}
        if local_id not in blocks:
            raise SquadsError(f"no {kind} {local_id} in {parent_id}")
        current = Status(blocks[local_id].status)
        if not force and current != status and not subentity_can_transition(kind, current, status):
            raise InvalidTransitionError(
                f"{kind} {local_id} cannot move {current.value} → {status.value}"
                " (use --force to override)"
            )
        text = discussion.set_block_status(text, kind, local_id, status.value)
        text = discussion.ensure_summary(text, kind, container)
        path.write_text(text, encoding="utf-8")
        self._bump(parent_id)
