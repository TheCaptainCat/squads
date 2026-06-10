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
    OPERATOR = "operator"

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
    ItemType.OPERATOR: "OP",
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
    ItemType.OPERATOR: "operators",
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
    # sub-entities (subtasks / user stories)
    TODO = "Todo"
    # review findings
    OPEN = "Open"
    FIXED = "Fixed"
    VERIFIED = "Verified"
    WONT_FIX = "WontFix"


class Priority(StrEnum):
    """An item's priority, rendered as a colored badge in lists and `show`."""

    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


PRIORITY_EMOJI: dict[Priority, str] = {
    Priority.URGENT: "🔴",
    Priority.HIGH: "🟠",
    Priority.MEDIUM: "🟡",
    Priority.LOW: "🟢",
}


class Severity(StrEnum):
    """A review finding's severity, rendered as a colored circle in summaries."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


SEVERITY_EMOJI: dict[Severity, str] = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🟢",
    Severity.INFO: "🔵",
}

DEFAULT_SEVERITY = Severity.MEDIUM

#: Colored badge per sub-entity status, for the human-readable block header.
STATUS_EMOJI: dict[Status, str] = {
    Status.TODO: "⚪",
    Status.IN_PROGRESS: "🟡",
    Status.BLOCKED: "🔴",
    Status.DONE: "🟢",
    Status.CANCELLED: "⚫",
    Status.OPEN: "🔴",
    Status.FIXED: "🟡",
    Status.VERIFIED: "🟢",
    Status.WONT_FIX: "⚫",
}
