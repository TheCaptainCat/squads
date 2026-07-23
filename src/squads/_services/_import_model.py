"""JSONL event model for bulk import (``sq import``): one line, one mutation.

Parsing is line-scoped and permissive at this layer — a malformed line (bad JSON, an unknown
``op``, a field that fails its type) becomes an :class:`ImportIssue` (never a raised exception),
so the validate-first pre-pass can collect every problem in one pass instead of stopping at the
first bad line. ``at``/``as`` inheritance (an event with neither carries the *effective* value
forward from the previous event, or the file-level default) is resolved here too, over the
parsed line stream — pure model bookkeeping shared by both the dry-run pre-pass and apply.

The three ergonomic fronts (``add-story``/``add-subtask``/``add-finding``) parse and stay as
their own event classes (so per-op counts reflect what the file actually wrote); the engine
calls :func:`generic_add_sub` at dispatch time to fold them to the generic :class:`AddSubEvent`
shape it actually simulates/applies against.
"""

import json
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from squads import _clock as clock
from squads._models._item import DEFAULT_KIND
from squads._services._results import ImportIssue


class _EventBase(BaseModel):
    """Fields common to every event: the op verb plus the optional per-event ``at``/``as``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    at: str | None = None
    as_: str | None = Field(default=None, alias="as")


class CreateEvent(_EventBase):
    op: Literal["create"] = "create"
    type: str
    title: str
    description: str = ""
    parent: str | None = None
    labels: list[str] = []
    refs: list[str] = []
    assignee: str | None = None
    fields: dict[str, str] = {}
    status: str | None = None
    slug: str | None = None
    body: str | None = None
    handle: str | None = None


class StatusEvent(_EventBase):
    op: Literal["status"] = "status"
    target: str
    status: str
    force: bool = False


class BodyEvent(_EventBase):
    op: Literal["body"] = "body"
    target: str
    body: str
    append: bool = False


class CommentEvent(_EventBase):
    op: Literal["comment"] = "comment"
    target: str
    messages: list[str] = []
    message: str | None = None
    story: str | None = None
    subtask: str | None = None
    finding: str | None = None
    sub: tuple[str, str] | None = None

    def all_messages(self) -> list[str]:
        """``messages`` with a single ``message`` folded in, in that order."""
        return [*self.messages, *([self.message] if self.message else [])]


class RefEvent(_EventBase):
    op: Literal["ref"] = "ref"
    target: str
    to: str
    kind: str = DEFAULT_KIND


class AddSubEvent(_EventBase):
    """The generic sub-entity-scaffold op — what every ergonomic front normalizes to."""

    op: Literal["add-sub"] = "add-sub"
    target: str
    kind: str
    title: str = ""
    story: str | None = None
    fields: dict[str, str] = {}
    assignee: str | None = None
    status: str | None = None
    body: str | None = None
    handle: str | None = None


class AddStoryEvent(_EventBase):
    op: Literal["add-story"] = "add-story"
    target: str
    title: str = ""
    assignee: str | None = None
    status: str | None = None
    body: str | None = None
    handle: str | None = None

    def as_generic(self) -> AddSubEvent:
        generic = AddSubEvent(
            target=self.target,
            kind="story",
            title=self.title,
            assignee=self.assignee,
            status=self.status,
            body=self.body,
            handle=self.handle,
        )
        generic.at, generic.as_ = self.at, self.as_
        return generic


class AddSubtaskEvent(_EventBase):
    op: Literal["add-subtask"] = "add-subtask"
    target: str
    title: str = ""
    story: str | None = None
    assignee: str | None = None
    status: str | None = None
    body: str | None = None
    handle: str | None = None

    def as_generic(self) -> AddSubEvent:
        generic = AddSubEvent(
            target=self.target,
            kind="subtask",
            title=self.title,
            story=self.story,
            assignee=self.assignee,
            status=self.status,
            body=self.body,
            handle=self.handle,
        )
        generic.at, generic.as_ = self.at, self.as_
        return generic


class AddFindingEvent(_EventBase):
    op: Literal["add-finding"] = "add-finding"
    target: str
    title: str = ""
    severity: str | None = None
    assignee: str | None = None
    status: str | None = None
    body: str | None = None
    handle: str | None = None

    def as_generic(self) -> AddSubEvent:
        generic = AddSubEvent(
            target=self.target,
            kind="finding",
            title=self.title,
            fields={"severity": self.severity} if self.severity else {},
            assignee=self.assignee,
            status=self.status,
            body=self.body,
            handle=self.handle,
        )
        generic.at, generic.as_ = self.at, self.as_
        return generic


class SubStatusEvent(_EventBase):
    op: Literal["sub-status"] = "sub-status"
    target: str
    kind: str
    local: str
    status: str
    force: bool = False


class SubBodyEvent(_EventBase):
    op: Literal["sub-body"] = "sub-body"
    target: str
    kind: str
    local: str
    body: str
    append: bool = False


class AssignEvent(_EventBase):
    op: Literal["assign"] = "assign"
    target: str
    assignee: str | None = None
    kind: str | None = None
    local: str | None = None


class UpdateEvent(_EventBase):
    op: Literal["update"] = "update"
    target: str
    title: str | None = None
    description: str | None = None
    assignee: str | None = None
    add_labels: list[str] = []
    rm_labels: list[str] = []
    parent: str | None = None
    clear_parent: bool = False
    status: str | None = None
    force: bool = False
    fields: dict[str, str] = {}
    unset_fields: list[str] = []


#: The v1 op set, as a discriminated union on ``op`` — the closed vocabulary the JSONL
#: parser accepts. The ergonomic fronts normalize to :class:`AddSubEvent` immediately after
#: parsing (see :func:`parse_events`), so downstream code dispatches on this union's members.
type ImportEvent = (
    CreateEvent
    | StatusEvent
    | BodyEvent
    | CommentEvent
    | RefEvent
    | AddSubEvent
    | AddStoryEvent
    | AddSubtaskEvent
    | AddFindingEvent
    | SubStatusEvent
    | SubBodyEvent
    | AssignEvent
    | UpdateEvent
)

_EVENT_ADAPTER: TypeAdapter[
    Annotated[
        CreateEvent
        | StatusEvent
        | BodyEvent
        | CommentEvent
        | RefEvent
        | AddSubEvent
        | AddStoryEvent
        | AddSubtaskEvent
        | AddFindingEvent
        | SubStatusEvent
        | SubBodyEvent
        | AssignEvent
        | UpdateEvent,
        Field(discriminator="op"),
    ]
] = TypeAdapter(
    Annotated[
        CreateEvent
        | StatusEvent
        | BodyEvent
        | CommentEvent
        | RefEvent
        | AddSubEvent
        | AddStoryEvent
        | AddSubtaskEvent
        | AddFindingEvent
        | SubStatusEvent
        | SubBodyEvent
        | AssignEvent
        | UpdateEvent,
        Field(discriminator="op"),
    ]
)


class ResolvedEvent(BaseModel):
    """One parsed event with its ``at``/``as`` inheritance resolved and any ergonomic front
    normalized to its generic form. ``line`` is the 1-based JSONL line number (for error
    reporting) — never part of the JSON itself."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    line: int
    event: ImportEvent
    at: datetime
    actor: str


def generic_add_sub(ev: ImportEvent) -> AddSubEvent:
    """The event as a generic :class:`AddSubEvent` — the ergonomic fronts normalize via
    :meth:`as_generic`; an already-generic ``add-sub`` passes through unchanged.

    Kept separate from parsing: :class:`ResolvedEvent` keeps the ORIGINAL event shape (so
    per-op counts reflect what the file actually wrote — ``"add-story"``, not a normalized
    ``"add-sub"``); the engine calls this at dispatch time instead.
    """
    if isinstance(ev, AddStoryEvent | AddSubtaskEvent | AddFindingEvent):
        return ev.as_generic()
    if isinstance(ev, AddSubEvent):
        return ev
    raise TypeError(f"{ev.op!r} is not an add-sub-shaped event")


def parse_events(
    text: str, *, default_at: datetime, default_as: str
) -> tuple[list[ResolvedEvent], list[ImportIssue]]:
    """Parse a JSONL event stream into resolved events, collecting every problem seen.

    File order is authoritative — never reordered by ``at``. A line that fails to parse (bad
    JSON, an unrecognised ``op``, a field of the wrong shape) becomes one :class:`ImportIssue`
    and is skipped; it does not interrupt ``at``/``as`` inheritance for the lines around it,
    which continues to track only successfully parsed events.
    """
    events: list[ResolvedEvent] = []
    issues: list[ImportIssue] = []
    current_at = default_at
    current_actor = default_as

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            issues.append(ImportIssue(line=line_no, message=f"invalid JSON: {exc.msg}"))
            continue
        if not isinstance(data, dict):
            issues.append(ImportIssue(line=line_no, message="event must be a JSON object"))
            continue
        try:
            parsed = _EVENT_ADAPTER.validate_python(data)
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = ".".join(str(p) for p in first["loc"])
            issues.append(ImportIssue(line=line_no, message=f"{loc}: {first['msg']}"))
            continue

        event = parsed
        if event.at is not None:
            try:
                current_at = clock.parse_iso(event.at)
            except ValueError:
                issues.append(
                    ImportIssue(line=line_no, message=f"invalid 'at' value: {event.at!r}")
                )
        if event.as_ is not None:
            current_actor = event.as_

        events.append(ResolvedEvent(line=line_no, event=event, at=current_at, actor=current_actor))

    return events, issues


def utc_now_floor() -> datetime:
    """A safe file-level ``at`` default when the caller supplies none (e.g. a unit test)."""
    return datetime.now(UTC).replace(microsecond=0)
