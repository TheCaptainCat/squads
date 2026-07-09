"""Badge enums and their helpers.

Both closed-set vocabulary enums that used to back this module are gone: the item-type
enum (``WORK_TYPES``, ``TYPE_ALIASES``, and the reserved prefix/folder maps) and the
``Status`` enum. The loaded workflow spec is now the sole authority for both axes —
``spec.items`` / ``spec.work_types()`` for types (prefix/folder resolve via
:func:`squads._models._vocab.prefix_for` and ``spec.items[t].folder``), and
``spec.statuses`` / ``spec.workflow_for(type).states`` for statuses. The few status names
the engine still binds by literal name (the agent lifecycle) live as validated string
constants in :mod:`squads._workflow._models` (``STATUS_DRAFT``/``STATUS_ACTIVE``/
``STATUS_ARCHIVED``), mirroring the meta-type name constants there.
"""

from enum import StrEnum


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
