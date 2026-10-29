"""JSONL event model for bulk import (``sq import``): one line, one mutation. A malformed line
becomes an :class:`ImportIssue`, not an exception, so the pre-pass collects every problem at once,
and ``at``/``as`` inheritance is resolved here. ``add-<kind>`` for each kind the active spec
declares is :class:`AddSubEvent` with its kind set, the kind's fields and mapping key at the top
level, and a comment selects a sub-entity by naming its kind; both are folded to the generic shape
at parse time, and the event keeps the op name the file wrote for the per-op counts.
"""

import json
from datetime import datetime
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator
from pydantic_core import ErrorDetails

from squads import _clock as clock
from squads._services._results import ImportIssue
from squads._workflow._models import WorkflowSpec


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
    #: Replacing an already-written body is refused without this, exactly as on the CLI — an
    #: import replayed onto a squad whose items already carry prose must not silently erase it.
    #: The whole apply is one transaction, so the refusal aborts the run rather than half-applying.
    force: bool = False


class CommentEvent(_EventBase):
    op: Literal["comment"] = "comment"
    target: str
    messages: list[str] = []
    message: str | None = None
    sub: tuple[str, str] | None = None

    def all_messages(self) -> list[str]:
        """``messages`` with a single ``message`` folded in, in that order."""
        return [*self.messages, *([self.message] if self.message else [])]


class RefEvent(_EventBase):
    op: Literal["ref"] = "ref"
    target: str
    to: str
    #: ``""`` (unspelled) resolves to the active spec's declared default kind — the same
    #: sentinel ``RefsMixin.add_ref``/``_add_ref_model`` resolve.
    kind: str = ""


class AddSubEvent(_EventBase):
    """The generic sub-entity-scaffold op — what every ergonomic front normalizes to."""

    op: Literal["add-sub"] = "add-sub"
    target: str
    kind: str
    title: str
    maps_to: str | None = None
    fields: dict[str, str] = {}
    assignee: str | None = None
    status: str | None = None
    deferred_to: str | None = None
    body: str | None = None
    handle: str | None = None


class SubStatusEvent(_EventBase):
    op: Literal["sub-status"] = "sub-status"
    target: str
    kind: str
    local: str
    status: str
    deferred_to: str | None = None
    force: bool = False


class SubBodyEvent(_EventBase):
    op: Literal["sub-body"] = "sub-body"
    target: str
    kind: str
    local: str
    body: str
    append: bool = False
    #: See :attr:`BodyEvent.force`.
    force: bool = False


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
    clear_assignee: bool = False
    add_labels: list[str] = []
    rm_labels: list[str] = []
    parent: str | None = None
    clear_parent: bool = False
    status: str | None = None
    force: bool = False
    fields: dict[str, str] = {}
    unset_fields: list[str] = []

    @model_validator(mode="after")
    def _update_names_a_valid_change(self) -> UpdateEvent:
        if self.assignee is not None and not self.assignee.strip():
            raise ValueError("assignee is empty; use clear_assignee to remove the assignee")
        if self.assignee is not None and self.clear_assignee:
            raise ValueError("use assignee or clear_assignee, not both")
        if not (self.clear_assignee or self._other_changes()):
            raise ValueError("nothing to update: the event names no field")
        return self

    def _other_changes(self) -> bool:
        """Whether the event asks for any change besides removing the assignee."""
        return bool(
            self.title is not None
            or self.description is not None
            or self.assignee is not None
            or self.add_labels
            or self.rm_labels
            or self.parent
            or self.clear_parent
            or self.status is not None
            or self.fields
            or self.unset_fields
        )

    def only_clears_assignee(self) -> bool:
        """Whether the event asks for nothing but removing the assignee."""
        return self.clear_assignee and not self._other_changes()


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
        | SubStatusEvent
        | SubBodyEvent
        | AssignEvent
        | UpdateEvent,
        Field(discriminator="op"),
    ]
)


class ResolvedEvent(BaseModel):
    """One parsed event with its ``at``/``as`` inheritance resolved. ``op_name`` is the op the
    file wrote (``add-outcome`` where ``event`` is the generic ``add-sub``); ``line`` is the
    1-based JSONL line number (for error reporting) — never part of the JSON itself."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    line: int
    event: ImportEvent
    op_name: str
    at: datetime
    actor: str


#: The op that adds a sub-entity of any kind; ``add-<kind>`` is the same op with the kind set.
ADD_SUB_OP = "add-sub"

#: The ``add-<kind>`` op prefix.
_ADD_PREFIX = "add-"


def _static_ops() -> list[str]:
    """The ops the event union accepts, in declaration order."""
    choices = cast(dict[str, Any], _EVENT_ADAPTER.core_schema)["choices"]
    return [str(op) for op in choices]


def _valid_ops(spec: WorkflowSpec) -> str:
    """The import ops this spec accepts: the fixed ones, with ``add-<kind>`` for each declared
    kind after ``add-sub``."""
    ops: list[str] = []
    for op in _static_ops():
        ops.append(op)
        if op == ADD_SUB_OP:
            ops.extend(f"{_ADD_PREFIX}{kind}" for kind in spec.subentity_kinds)
    return ", ".join(ops)


def _validation_message(error: ErrorDetails, spec: WorkflowSpec) -> str:
    """One validation error as an issue message: squads' own words for an unknown ``op``."""
    if error["type"] == "union_tag_invalid":
        return f"unknown op {error.get('ctx', {}).get('tag')!r}; valid ops: {_valid_ops(spec)}"
    if error["type"] == "union_tag_not_found":
        return f"missing op; valid ops: {_valid_ops(spec)}"
    loc = ".".join(str(p) for p in error["loc"])
    return f"{loc}: {error['msg']}" if loc else str(error["msg"])


class _EventRefusal(Exception):
    """A line whose keys the active spec cannot give a meaning to."""


def _add_kind_data(data: dict[str, Any], kind: str, spec: WorkflowSpec) -> dict[str, Any]:
    """The ``add-sub`` form of an ``add-<kind>`` line: the kind set, each field the kind declares
    taken from its top-level key into ``fields``, and the target kind's name taken into
    ``maps_to``."""
    if "kind" in data:
        raise _EventRefusal(f"{data['op']}: the kind is in the op; drop the 'kind' key")
    out = {k: v for k, v in data.items() if k != "op"}
    out["op"] = ADD_SUB_OP
    out["kind"] = kind
    fields = dict(out.get("fields") or {})
    for field in spec.fields_for(kind):
        if field.code in out:
            if field.code in fields:
                raise _EventRefusal(f"{data['op']}: {field.code!r} is given twice")
            fields[field.code] = out.pop(field.code)
    if fields:
        out["fields"] = fields
    target = spec.mapping_target_kind(kind)
    if target is not None and target in out:
        if out.get("maps_to") is not None:
            raise _EventRefusal(f"{data['op']}: {target!r} and 'maps_to' name the same mapping")
        out["maps_to"] = out.pop(target)
    return out


def _comment_data(data: dict[str, Any], spec: WorkflowSpec) -> dict[str, Any]:
    """A comment line with its per-kind selector folded into the generic ``sub`` pair; naming
    more than one sub-entity is refused."""
    named = [(kind, data[kind]) for kind in spec.subentity_kinds if data.get(kind)]
    if data.get("sub") is not None:
        named.append(("sub", data["sub"]))
    if len(named) > 1:
        choices = " / ".join([*spec.subentity_kinds, "sub"])
        raise _EventRefusal(f"a comment event names at most one of {choices}")
    out = {k: v for k, v in data.items() if k not in spec.subentity_kinds}
    if named and named[0][0] != "sub":
        out["sub"] = list(named[0])
    return out


def _normalised(data: dict[str, Any], spec: WorkflowSpec) -> dict[str, Any]:
    """*data* with the per-kind fronts folded to the generic ops *spec* declares."""
    op = data.get("op")
    if op == "comment":
        return _comment_data(data, spec)
    if isinstance(op, str) and op.startswith(_ADD_PREFIX) and op != ADD_SUB_OP:
        kind = op.removeprefix(_ADD_PREFIX)
        if kind in spec.subentity_kinds:
            return _add_kind_data(data, kind, spec)
    return data


def parse_events(
    text: str, *, spec: WorkflowSpec, default_at: datetime, default_as: str | None = None
) -> tuple[list[ResolvedEvent], list[ImportIssue]]:
    """Parse a JSONL event stream into resolved events, collecting every problem. File order is
    authoritative, never reordered by ``at``. A line that fails to parse becomes one
    :class:`ImportIssue` and is skipped without interrupting ``at``/``as`` inheritance.
    ``default_as`` has no fallback: an event with no actor from any source becomes an issue naming
    the missing actor.
    """
    events: list[ResolvedEvent] = []
    issues: list[ImportIssue] = []
    current_at = default_at
    current_actor: str | None = default_as

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
        written = cast(dict[str, Any], data)
        try:
            parsed = _EVENT_ADAPTER.validate_python(_normalised(written, spec))
        except _EventRefusal as exc:
            issues.append(ImportIssue(line=line_no, message=str(exc)))
            continue
        except ValidationError as exc:
            first = exc.errors()[0]
            issues.append(ImportIssue(line=line_no, message=_validation_message(first, spec)))
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

        if current_actor is None:
            issues.append(ImportIssue(line=line_no, message="no actor: missing 'as'"))
            continue

        events.append(
            ResolvedEvent(
                line=line_no,
                event=event,
                op_name=str(written["op"]),
                at=current_at,
                actor=current_actor,
            )
        )

    return events, issues


def utc_now_floor() -> datetime:
    """A safe file-level ``at`` default when the caller supplies none (e.g. a unit test).

    Goes through the injectable clock rather than reading wall-clock time directly: an
    ``sq --at ...`` run forging a historical instant, and a frozen-time test, must both see
    their own instant here — a second, unhooked source of "now" silently ignores the override
    at whichever seam still reads it.
    """
    return clock.now()
