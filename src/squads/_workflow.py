"""Per-type status workflows and transition validation."""

from dataclasses import dataclass

from squads._models._enums import ItemType, Status

S = Status


@dataclass(frozen=True)
class Workflow:
    initial: Status
    transitions: dict[Status, tuple[Status, ...]]

    @property
    def states(self) -> set[Status]:
        seen: set[Status] = {self.initial}
        for src, dsts in self.transitions.items():
            seen.add(src)
            seen.update(dsts)
        return seen

    def can_transition(self, src: Status, dst: Status) -> bool:
        return dst in self.transitions.get(src, ())


# Work items: Draft -> Ready -> InProgress -> InReview -> Done (+ Blocked, Cancelled)
_WORK = Workflow(
    initial=S.DRAFT,
    transitions={
        S.DRAFT: (S.READY, S.IN_PROGRESS, S.CANCELLED),
        S.READY: (S.IN_PROGRESS, S.BLOCKED, S.CANCELLED),
        S.IN_PROGRESS: (S.IN_REVIEW, S.BLOCKED, S.DONE, S.CANCELLED),
        S.IN_REVIEW: (S.IN_PROGRESS, S.DONE, S.BLOCKED, S.CANCELLED),
        S.BLOCKED: (S.READY, S.IN_PROGRESS, S.CANCELLED),
        S.DONE: (S.IN_PROGRESS,),
        S.CANCELLED: (S.DRAFT,),
    },
)

# ADR: Proposed -> Accepted -> Superseded (+ Rejected, Deprecated)
_ADR = Workflow(
    initial=S.PROPOSED,
    transitions={
        S.PROPOSED: (S.ACCEPTED, S.REJECTED),
        S.ACCEPTED: (S.SUPERSEDED, S.DEPRECATED),
        S.REJECTED: (S.PROPOSED,),
        S.SUPERSEDED: (),
        S.DEPRECATED: (),
    },
)

# Code review: Requested -> InReview -> ChangesRequested -> Approved (+ Rejected)
_REVIEW = Workflow(
    initial=S.REQUESTED,
    transitions={
        S.REQUESTED: (S.IN_REVIEW, S.REJECTED),
        S.IN_REVIEW: (S.CHANGES_REQUESTED, S.APPROVED, S.REJECTED),
        S.CHANGES_REQUESTED: (S.IN_REVIEW, S.REJECTED),
        S.APPROVED: (),
        S.REJECTED: (),
    },
)

# Guide: Draft -> Published -> Deprecated
_GUIDE = Workflow(
    initial=S.DRAFT,
    transitions={
        S.DRAFT: (S.PUBLISHED,),
        S.PUBLISHED: (S.DEPRECATED, S.DRAFT),
        S.DEPRECATED: (S.PUBLISHED,),
    },
)

# Role / Skill: Draft -> Active -> Archived
_AGENT = Workflow(
    initial=S.DRAFT,
    transitions={
        S.DRAFT: (S.ACTIVE,),
        S.ACTIVE: (S.ARCHIVED,),
        S.ARCHIVED: (S.ACTIVE,),
    },
)

WORKFLOWS: dict[ItemType, Workflow] = {
    ItemType.EPIC: _WORK,
    ItemType.FEATURE: _WORK,
    ItemType.TASK: _WORK,
    ItemType.BUG: _WORK,
    ItemType.DECISION: _ADR,
    ItemType.REVIEW: _REVIEW,
    ItemType.GUIDE: _GUIDE,
    ItemType.ROLE: _AGENT,
    ItemType.SKILL: _AGENT,
    ItemType.OPERATOR: _AGENT,
}


# Sub-entities (subtasks / user stories): a light shared machine.
_SUBENTITY = Workflow(
    initial=S.TODO,
    transitions={
        S.TODO: (S.IN_PROGRESS, S.BLOCKED, S.CANCELLED),
        S.IN_PROGRESS: (S.DONE, S.BLOCKED, S.CANCELLED),
        S.BLOCKED: (S.IN_PROGRESS, S.CANCELLED),
        S.DONE: (S.IN_PROGRESS,),
        S.CANCELLED: (S.TODO,),
    },
)

# Review findings: Open -> Fixed -> Verified (+ WontFix).
_FINDING = Workflow(
    initial=S.OPEN,
    transitions={
        S.OPEN: (S.FIXED, S.WONT_FIX),
        S.FIXED: (S.VERIFIED, S.OPEN),
        S.VERIFIED: (),
        S.WONT_FIX: (S.OPEN,),
    },
)

#: Status machines for body-local sub-entities, keyed by kind (`_discussion` kinds).
SUBENTITY_WORKFLOWS: dict[str, Workflow] = {
    "subtask": _SUBENTITY,
    "story": _SUBENTITY,
    "finding": _FINDING,
}


#: Statuses that mean "no further work expected" — used to scope the inbox to open items.
TERMINAL: frozenset[Status] = frozenset(
    {
        S.DONE,
        S.CANCELLED,
        S.REJECTED,
        S.SUPERSEDED,
        S.DEPRECATED,
        S.ARCHIVED,
        S.APPROVED,
        S.VERIFIED,
        S.WONT_FIX,
    }
)


def is_open(status: Status) -> bool:
    return status not in TERMINAL


#: Allowed parent types per child type (the workflow spine). Types absent here are unconstrained;
#: a ``None`` parent is always allowed.
ALLOWED_PARENTS: dict[ItemType, set[ItemType]] = {
    ItemType.TASK: {ItemType.FEATURE},
    ItemType.FEATURE: {ItemType.EPIC},
}


def parent_allowed(child: ItemType, parent: ItemType) -> bool:
    allowed = ALLOWED_PARENTS.get(child)
    return allowed is None or parent in allowed


def parent_hint(child: ItemType) -> str:
    """Human guidance for an invalid parent (used in error messages)."""
    allowed = ALLOWED_PARENTS.get(child, set())
    names = " or ".join(sorted(t.value for t in allowed)) or "none"
    msg = f"a {child.value}'s parent must be of type {names}"
    if child is ItemType.TASK:
        msg += "; link a bug or review with `sq ref add <task> <id> --kind fixes|addresses`"
    return msg


def workflow_for(item_type: ItemType) -> Workflow:
    return WORKFLOWS[item_type]


def initial_status(item_type: ItemType) -> Status:
    return WORKFLOWS[item_type].initial


def can_transition(item_type: ItemType, src: Status, dst: Status) -> bool:
    return WORKFLOWS[item_type].can_transition(src, dst)


def subentity_workflow(kind: str) -> Workflow:
    return SUBENTITY_WORKFLOWS[kind]


def subentity_initial(kind: str) -> Status:
    return SUBENTITY_WORKFLOWS[kind].initial


def subentity_can_transition(kind: str, src: Status, dst: Status) -> bool:
    return SUBENTITY_WORKFLOWS[kind].can_transition(src, dst)
