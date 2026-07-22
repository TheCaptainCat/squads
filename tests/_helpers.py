"""Shared test-only constants and helpers with no production analogue.

Kept separate from `conftest.py` (fixtures/autouse hooks) since these are plain importable
values, not pytest fixtures.
"""

import re

_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Drop ANSI SGR codes so width/flag assertions survive a color-forcing help console."""
    return _ANSI_SGR.sub("", text)


#: The exact badge glyph for each of the 9 built-in sub-entity statuses (subtask/story:
#: Todo/InProgress/Blocked/Done/Cancelled; review finding: Open/Fixed/Verified/WontFix).
#:
#: This is the test-layer's own golden reference — it has no production counterpart. Production
#: badge resolution is spec-driven (`WorkflowSpec.status_badge`, backed by the workflow TOML's
#: per-status `badge` field), which also covers custom statuses with a graceful default. This
#: dict exists purely so tests can pin the 9 built-in glyphs and catch accidental drift in the
#: spec's declared badges; update it deliberately if a built-in badge is ever meant to change.
EXPECTED_BUILTIN_STATUS_BADGES: dict[str, str] = {
    "Todo": "⚪",
    "InProgress": "🟡",
    "Blocked": "🔴",
    "Done": "🟢",
    "Cancelled": "⚫",
    "Open": "🔴",
    "Fixed": "🟡",
    "Verified": "🟢",
    "WontFix": "⚫",
}

#: Built-in type -> ID prefix, mirroring the bundled ``default_workflow.toml`` exactly.
#:
#: Test-only (no production analogue): production resolves this from the loaded
#: ``WorkflowSpec`` alone (the ``ItemType`` enum + reserved prefix map it used to
#: read this from are deleted). Tests that need a literal prefix — constructing an ``Item``
#: directly, or calling ``SquadsDB.allocate_id``/``format_id`` with an explicit prefix — use
#: this shared dict instead of each hardcoding their own copy.
BUILTIN_PREFIX: dict[str, str] = {
    "epic": "EPIC",
    "feature": "FEAT",
    "task": "TASK",
    "bug": "BUG",
    "decision": "ADR",
    "review": "REV",
    "guide": "GUIDE",
    "role": "ROLE",
    "skill": "SKILL",
    "operator": "OP",
}

#: Built-in type -> squad-folder-relative subfolder, mirroring ``default_workflow.toml``.
#: Test-only — see :data:`BUILTIN_PREFIX`.
BUILTIN_FOLDER: dict[str, str] = {
    "epic": "epics",
    "feature": "features",
    "task": "tasks",
    "bug": "bugs",
    "decision": "adrs",
    "review": "reviews",
    "guide": "guides",
    "role": "agents/roles",
    "skill": "agents/skills",
    "operator": "operators",
}

#: All 10 built-in type names, in the same order as :data:`BUILTIN_PREFIX`.
BUILTIN_TYPES: tuple[str, ...] = tuple(BUILTIN_PREFIX)

#: The 7 work-item types — excludes the 3 roster types (role/skill/operator).
WORK_TYPES: tuple[str, ...] = ("epic", "feature", "task", "bug", "decision", "review", "guide")

#: The 3 roster types the engine binds by name.
ROSTER_TYPES: tuple[str, ...] = ("role", "skill", "operator")

#: All 23 built-in status names across every lifecycle (work/adr/review/bug/guide/agent +
#: sub-entity/finding), mirroring the bundled ``default_workflow.toml`` exactly.
#:
#: Test-only (no production analogue): production resolves the status vocabulary from the
#: loaded ``WorkflowSpec`` alone (the ``Status`` enum this used to enumerate is
#: deleted). Tests that need "every built-in status" (golden-lock set equality, terminal/
#: badge iteration) use this shared tuple instead of each hardcoding its own copy.
BUILTIN_STATUSES: tuple[str, ...] = (
    # work items
    "Draft",
    "Ready",
    "InProgress",
    "InReview",
    "Done",
    "Blocked",
    "Cancelled",
    # ADR / decision
    "Proposed",
    "Accepted",
    "Superseded",
    "Rejected",
    "Deprecated",
    # code review
    "Requested",
    "ChangesRequested",
    "Approved",
    # guide
    "Published",
    # role / skill / operator (agent lifecycle)
    "Active",
    "Archived",
    # sub-entities (subtasks / user stories)
    "Todo",
    # review findings
    "Open",
    "Fixed",
    "Verified",
    "WontFix",
)

#: The agent-lifecycle statuses — the only status-axis floor.
FLOOR_STATUSES: tuple[str, ...] = ("Draft", "Active", "Archived")

#: The sub-entity/finding statuses that left the floor and became ordinary spec vocabulary —
#: bound by machine role (start state / per-kind completion target) instead of by name.
FORMER_FLOOR_STATUSES: tuple[str, ...] = (
    "Todo",
    "InProgress",
    "Blocked",
    "Done",
    "Cancelled",
    "Open",
    "Fixed",
    "Verified",
    "WontFix",
)
