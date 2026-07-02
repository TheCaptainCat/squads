"""Item types, status values, and the enum/badge helpers.

Vocabulary tables (prefix, folder, alias, type-by-prefix) have been centralised in
:mod:`squads._models._vocab` (ADR-000266 / TASK-000267).  Import from there for any
call site that needs prefix or folder resolution; the enums here delegate to that module.
"""

from enum import StrEnum

from squads._models._vocab import RESERVED_FOLDER, RESERVED_PREFIX


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
        """The authoritative ID prefix for this built-in type (e.g. ``"TASK"``)."""
        return RESERVED_PREFIX[self]

    @property
    def folder(self) -> str:
        """The squad-folder-relative subfolder for this built-in type (e.g. ``"tasks"``)."""
        return RESERVED_FOLDER[self]


#: The 7 work-item types that can be retyped; excludes agent/operator meta-types.
WORK_TYPES: tuple[ItemType, ...] = (
    ItemType.EPIC,
    ItemType.FEATURE,
    ItemType.TASK,
    ItemType.BUG,
    ItemType.DECISION,
    ItemType.REVIEW,
    ItemType.GUIDE,
)


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
