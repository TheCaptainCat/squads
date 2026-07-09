"""Status values, badge enums, and their helpers.

The item-type vocabulary (the type enum, ``WORK_TYPES``, ``TYPE_ALIASES``, and the
reserved prefix/folder maps) has been deleted: the loaded workflow spec is now the sole type
authority (``spec.items`` / ``spec.work_types()``; prefix/folder resolve via
:func:`squads._models._vocab.prefix_for` and ``spec.items[t].folder`` respectively).
"""

from enum import StrEnum


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
