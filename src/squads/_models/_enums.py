"""Item types, status values, and the prefix/folder mappings that tie an ID to its place on disk."""

from enum import StrEnum


class ItemType(StrEnum):
    EPIC = "epic"
    FEATURE = "feature"
    TASK = "task"
    BUG = "bug"
    DECISION = "decision"
    REVIEW = "review"
    GUIDE = "guide"
    ROLE = "role"
    SKILL = "skill"

    @property
    def prefix(self) -> str:
        return PREFIX_BY_TYPE[self]

    @property
    def folder(self) -> str:
        return FOLDER_BY_TYPE[self]


# ID prefix per type. One global counter feeds the number; the prefix only marks the type.
PREFIX_BY_TYPE: dict[ItemType, str] = {
    ItemType.EPIC: "EPIC",
    ItemType.FEATURE: "FEAT",
    ItemType.TASK: "TASK",
    ItemType.BUG: "BUG",
    ItemType.DECISION: "ADR",
    ItemType.REVIEW: "REV",
    ItemType.GUIDE: "GUIDE",
    ItemType.ROLE: "ROLE",
    ItemType.SKILL: "SKILL",
}

TYPE_BY_PREFIX: dict[str, ItemType] = {v: k for k, v in PREFIX_BY_TYPE.items()}

# Squad-folder-relative subfolder that holds each type's markdown files.
FOLDER_BY_TYPE: dict[ItemType, str] = {
    ItemType.EPIC: "epics",
    ItemType.FEATURE: "features",
    ItemType.TASK: "tasks",
    ItemType.BUG: "bugs",
    ItemType.DECISION: "adrs",
    ItemType.REVIEW: "reviews",
    ItemType.GUIDE: "guides",
    ItemType.ROLE: "agents/roles",
    ItemType.SKILL: "agents/skills",
}


class Status(StrEnum):
    # work items
    DRAFT = "Draft"
    READY = "Ready"
    IN_PROGRESS = "InProgress"
    IN_REVIEW = "InReview"
    DONE = "Done"
    BLOCKED = "Blocked"
    CANCELLED = "Cancelled"
    # ADR / decision
    PROPOSED = "Proposed"
    ACCEPTED = "Accepted"
    SUPERSEDED = "Superseded"
    REJECTED = "Rejected"
    DEPRECATED = "Deprecated"
    # code review
    REQUESTED = "Requested"
    CHANGES_REQUESTED = "ChangesRequested"
    APPROVED = "Approved"
    # guide
    PUBLISHED = "Published"
    # role / skill
    ACTIVE = "Active"
    ARCHIVED = "Archived"
