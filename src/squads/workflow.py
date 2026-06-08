"""Per-type status workflows and transition validation."""

from dataclasses import dataclass

from squads.models.enums import ItemType, Status

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
    }
)


def is_open(status: Status) -> bool:
    return status not in TERMINAL


def workflow_for(item_type: ItemType) -> Workflow:
    return WORKFLOWS[item_type]


def initial_status(item_type: ItemType) -> Status:
    return WORKFLOWS[item_type].initial


def can_transition(item_type: ItemType, src: Status, dst: Status) -> bool:
    return WORKFLOWS[item_type].can_transition(src, dst)
