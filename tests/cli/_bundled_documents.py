"""The JSON documents the bundled vocabulary listings (`sq workflow <listing> --json`) and the
migration registry (`sq migrate help --json`) print, written out in full."""

TYPES = [
    {
        "type": "epic",
        "order": 10.0,
        "prefix": "EPIC",
        "reserved": False,
        "category": "work",
        "subentity_kind": None,
        "lifecycle": "work",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {},
        "labels": {
            "singular": "Epic",
            "plural": "Epics",
            "singular_lower": "epic",
            "plural_lower": "epics",
        },
    },
    {
        "type": "feature",
        "order": 20.0,
        "prefix": "FEAT",
        "reserved": False,
        "category": "work",
        "subentity_kind": "story",
        "lifecycle": "work",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {},
        "labels": {
            "singular": "Feature",
            "plural": "Features",
            "singular_lower": "feature",
            "plural_lower": "features",
        },
    },
    {
        "type": "task",
        "order": 30.0,
        "prefix": "TASK",
        "reserved": False,
        "category": "work",
        "subentity_kind": "subtask",
        "lifecycle": "work",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {},
        "labels": {
            "singular": "Task",
            "plural": "Tasks",
            "singular_lower": "task",
            "plural_lower": "tasks",
        },
    },
    {
        "type": "bug",
        "order": 40.0,
        "prefix": "BUG",
        "reserved": False,
        "category": "work",
        "subentity_kind": None,
        "lifecycle": "bug",
        "fields": [
            {"code": "priority", "label": "Priority", "collection": "priority"},
            {"code": "severity", "label": "Severity", "collection": "severity"},
        ],
        "attributes": {},
        "labels": {
            "singular": "Bug",
            "plural": "Bugs",
            "singular_lower": "bug",
            "plural_lower": "bugs",
        },
    },
    {
        "type": "decision",
        "order": 50.0,
        "prefix": "ADR",
        "reserved": False,
        "category": "records",
        "subentity_kind": None,
        "lifecycle": "adr",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {},
        "labels": {
            "singular": "Decision",
            "plural": "Decisions",
            "singular_lower": "decision",
            "plural_lower": "decisions",
        },
    },
    {
        "type": "contract",
        "order": 55.0,
        "prefix": "PRD",
        "reserved": False,
        "category": "records",
        "subentity_kind": None,
        "lifecycle": "contract",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {},
        "labels": {
            "singular": "Contract",
            "plural": "Contracts",
            "singular_lower": "contract",
            "plural_lower": "contracts",
        },
    },
    {
        "type": "milestone",
        "order": 57.0,
        "prefix": "MILE",
        "reserved": False,
        "category": "records",
        "subentity_kind": None,
        "lifecycle": "milestone",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {
            "target_date": {
                "kind": "date",
                "required": False,
                "settable": True,
                "label": "target date",
            }
        },
        "labels": {
            "singular": "Milestone",
            "plural": "Milestones",
            "singular_lower": "milestone",
            "plural_lower": "milestones",
        },
    },
    {
        "type": "review",
        "order": 60.0,
        "prefix": "REV",
        "reserved": False,
        "category": "work",
        "subentity_kind": "finding",
        "lifecycle": "review",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {
            "target_ref": {"kind": "str", "required": False, "settable": True, "label": None}
        },
        "labels": {
            "singular": "Review",
            "plural": "Reviews",
            "singular_lower": "review",
            "plural_lower": "reviews",
        },
    },
    {
        "type": "guide",
        "order": 70.0,
        "prefix": "GUIDE",
        "reserved": False,
        "category": "records",
        "subentity_kind": None,
        "lifecycle": "guide",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {
            "tags": {"kind": "list", "required": False, "settable": True, "label": None},
            "tech": {"kind": "str", "required": False, "settable": True, "label": None},
        },
        "labels": {
            "singular": "Guide",
            "plural": "Guides",
            "singular_lower": "guide",
            "plural_lower": "guides",
        },
    },
    {
        "type": "role",
        "order": 80.0,
        "prefix": "ROLE",
        "reserved": True,
        "category": "roster",
        "subentity_kind": None,
        "lifecycle": "agent",
        "fields": [],
        "attributes": {
            "agreements": {"kind": "list", "required": False, "settable": False, "label": None},
            "can_spawn": {"kind": "bool", "required": False, "settable": False, "label": None},
            "capabilities": {"kind": "list", "required": False, "settable": False, "label": None},
            "color": {"kind": "str", "required": False, "settable": False, "label": None},
            "is_default": {"kind": "bool", "required": False, "settable": False, "label": None},
            "job_title": {"kind": "str", "required": False, "settable": False, "label": None},
            "mission": {"kind": "str", "required": False, "settable": False, "label": None},
            "model": {"kind": "str", "required": False, "settable": True, "label": None},
            "origin": {"kind": "str", "required": True, "settable": False, "label": None},
            "pronouns": {"kind": "str", "required": False, "settable": False, "label": None},
            "responsibilities": {
                "kind": "list",
                "required": False,
                "settable": False,
                "label": None,
            },
            "tech": {"kind": "str", "required": False, "settable": False, "label": None},
            "template": {"kind": "str", "required": False, "settable": False, "label": None},
        },
        "labels": {
            "singular": "Role",
            "plural": "Roles",
            "singular_lower": "role",
            "plural_lower": "roles",
        },
    },
    {
        "type": "skill",
        "order": 90.0,
        "prefix": "SKILL",
        "reserved": True,
        "category": "roster",
        "subentity_kind": None,
        "lifecycle": "agent",
        "fields": [],
        "attributes": {
            "allowed_tools": {"kind": "str", "required": False, "settable": True, "label": None},
            "model": {"kind": "str", "required": False, "settable": True, "label": None},
            "operator_invocable": {
                "kind": "bool",
                "required": False,
                "settable": False,
                "label": None,
            },
            "origin": {"kind": "str", "required": True, "settable": False, "label": None},
            "when_to_use": {"kind": "str", "required": False, "settable": True, "label": None},
        },
        "labels": {
            "singular": "Skill",
            "plural": "Skills",
            "singular_lower": "skill",
            "plural_lower": "skills",
        },
    },
    {
        "type": "operator",
        "order": 100.0,
        "prefix": "OP",
        "reserved": True,
        "category": "roster",
        "subentity_kind": None,
        "lifecycle": "agent",
        "fields": [],
        "attributes": {
            "pronouns": {"kind": "str", "required": False, "settable": False, "label": None}
        },
        "labels": {
            "singular": "Operator",
            "plural": "Operators",
            "singular_lower": "operator",
            "plural_lower": "operators",
        },
    },
]


SUBENTITY_KINDS = [
    {
        "subentity_kind": "finding",
        "lifecycle": "finding",
        "plural": "findings",
        "local_prefix": "F",
        "container_heading": "Findings",
        "completion": "Fixed",
        "maps_to_parent": False,
        "fields": [{"code": "severity", "label": "Severity", "collection": "severity"}],
    },
    {
        "subentity_kind": "story",
        "lifecycle": "subentity",
        "plural": "stories",
        "local_prefix": "US",
        "container_heading": "User Stories",
        "completion": "Done",
        "maps_to_parent": False,
        "fields": [],
    },
    {
        "subentity_kind": "subtask",
        "lifecycle": "subentity",
        "plural": "subtasks",
        "local_prefix": "ST",
        "container_heading": "Subtasks",
        "completion": "Done",
        "maps_to_parent": True,
        "fields": [],
    },
]


LIFECYCLES = [
    {
        "lifecycle": "adr",
        "initial": "Proposed",
        "states": ["Proposed", "Accepted", "Rejected", "Superseded", "Deprecated"],
        "transitions": [
            {"from": "Proposed", "to": "Accepted"},
            {"from": "Proposed", "to": "Rejected"},
            {"from": "Accepted", "to": "Superseded"},
            {"from": "Accepted", "to": "Deprecated"},
            {"from": "Rejected", "to": "Proposed"},
        ],
    },
    {
        "lifecycle": "agent",
        "initial": "Active",
        "states": ["Active", "Archived"],
        "transitions": [{"from": "Active", "to": "Archived"}, {"from": "Archived", "to": "Active"}],
    },
    {
        "lifecycle": "bug",
        "initial": "Open",
        "states": ["Open", "InProgress", "WontFix", "Cancelled", "Fixed", "Blocked", "Verified"],
        "transitions": [
            {"from": "Open", "to": "InProgress"},
            {"from": "Open", "to": "WontFix"},
            {"from": "Open", "to": "Cancelled"},
            {"from": "InProgress", "to": "Fixed"},
            {"from": "InProgress", "to": "Blocked"},
            {"from": "InProgress", "to": "WontFix"},
            {"from": "InProgress", "to": "Cancelled"},
            {"from": "WontFix", "to": "Open"},
            {"from": "Cancelled", "to": "Open"},
            {"from": "Fixed", "to": "Verified"},
            {"from": "Fixed", "to": "InProgress"},
            {"from": "Blocked", "to": "InProgress"},
            {"from": "Blocked", "to": "WontFix"},
            {"from": "Blocked", "to": "Cancelled"},
            {"from": "Verified", "to": "InProgress"},
        ],
    },
    {
        "lifecycle": "contract",
        "initial": "Draft",
        "states": ["Draft", "Active", "Superseded", "Deprecated"],
        "transitions": [
            {"from": "Draft", "to": "Active"},
            {"from": "Active", "to": "Superseded"},
            {"from": "Active", "to": "Deprecated"},
            {"from": "Deprecated", "to": "Active"},
        ],
    },
    {
        "lifecycle": "finding",
        "initial": "Open",
        "states": ["Open", "Fixed", "WontFix", "Noted", "Deferred", "Verified"],
        "transitions": [
            {"from": "Open", "to": "Fixed"},
            {"from": "Open", "to": "WontFix"},
            {"from": "Open", "to": "Noted"},
            {"from": "Open", "to": "Deferred"},
            {"from": "Fixed", "to": "Verified"},
            {"from": "Fixed", "to": "Open"},
            {"from": "WontFix", "to": "Open"},
            {"from": "Noted", "to": "Deferred"},
        ],
    },
    {
        "lifecycle": "guide",
        "initial": "Draft",
        "states": ["Draft", "Published", "Deprecated"],
        "transitions": [
            {"from": "Draft", "to": "Published"},
            {"from": "Published", "to": "Deprecated"},
            {"from": "Published", "to": "Draft"},
            {"from": "Deprecated", "to": "Published"},
        ],
    },
    {
        "lifecycle": "milestone",
        "initial": "Draft",
        "states": ["Draft", "InProgress", "Cancelled", "Done"],
        "transitions": [
            {"from": "Draft", "to": "InProgress"},
            {"from": "Draft", "to": "Cancelled"},
            {"from": "InProgress", "to": "Done"},
            {"from": "InProgress", "to": "Cancelled"},
            {"from": "Cancelled", "to": "Draft"},
            {"from": "Done", "to": "InProgress"},
        ],
    },
    {
        "lifecycle": "review",
        "initial": "Requested",
        "states": ["Requested", "InReview", "Rejected", "ChangesRequested", "Approved"],
        "transitions": [
            {"from": "Requested", "to": "InReview"},
            {"from": "Requested", "to": "Rejected"},
            {"from": "InReview", "to": "ChangesRequested"},
            {"from": "InReview", "to": "Approved"},
            {"from": "InReview", "to": "Rejected"},
            {"from": "ChangesRequested", "to": "InReview"},
            {"from": "ChangesRequested", "to": "Approved"},
            {"from": "ChangesRequested", "to": "Rejected"},
        ],
    },
    {
        "lifecycle": "subentity",
        "initial": "Todo",
        "states": ["Todo", "InProgress", "Blocked", "Cancelled", "Done"],
        "transitions": [
            {"from": "Todo", "to": "InProgress"},
            {"from": "Todo", "to": "Blocked"},
            {"from": "Todo", "to": "Cancelled"},
            {"from": "Todo", "to": "Done"},
            {"from": "InProgress", "to": "Done"},
            {"from": "InProgress", "to": "Blocked"},
            {"from": "InProgress", "to": "Cancelled"},
            {"from": "Blocked", "to": "InProgress"},
            {"from": "Blocked", "to": "Cancelled"},
            {"from": "Cancelled", "to": "Todo"},
            {"from": "Done", "to": "InProgress"},
        ],
    },
    {
        "lifecycle": "work",
        "initial": "Draft",
        "states": ["Draft", "Ready", "InProgress", "Cancelled", "Blocked", "InReview", "Done"],
        "transitions": [
            {"from": "Draft", "to": "Ready"},
            {"from": "Draft", "to": "InProgress"},
            {"from": "Draft", "to": "Cancelled"},
            {"from": "Ready", "to": "InProgress"},
            {"from": "Ready", "to": "Blocked"},
            {"from": "Ready", "to": "Cancelled"},
            {"from": "InProgress", "to": "InReview"},
            {"from": "InProgress", "to": "Blocked"},
            {"from": "InProgress", "to": "Done"},
            {"from": "InProgress", "to": "Cancelled"},
            {"from": "Cancelled", "to": "Draft"},
            {"from": "Blocked", "to": "Ready"},
            {"from": "Blocked", "to": "InProgress"},
            {"from": "Blocked", "to": "Cancelled"},
            {"from": "InReview", "to": "InProgress"},
            {"from": "InReview", "to": "Done"},
            {"from": "InReview", "to": "Blocked"},
            {"from": "InReview", "to": "Cancelled"},
            {"from": "Done", "to": "InProgress"},
        ],
    },
]


COLLECTIONS = [
    {
        "collection": "priority",
        "label": "Priority",
        "ordered": True,
        "default": None,
        "badges": [
            {"code": "urgent", "label": "Urgent", "emoji": "🔴"},
            {"code": "high", "label": "High", "emoji": "🟠"},
            {"code": "medium", "label": "Medium", "emoji": "🟡"},
            {"code": "low", "label": "Low", "emoji": "🟢"},
        ],
    },
    {
        "collection": "severity",
        "label": "Severity",
        "ordered": True,
        "default": "medium",
        "badges": [
            {"code": "critical", "label": "Critical", "emoji": "🔴"},
            {"code": "high", "label": "High", "emoji": "🟠"},
            {"code": "medium", "label": "Medium", "emoji": "🟡"},
            {"code": "low", "label": "Low", "emoji": "🟢"},
            {"code": "info", "label": "Info", "emoji": "🔵"},
        ],
    },
]


STATUSES = [
    {"status": "Accepted", "role": "in_force", "badge": None, "display": {"intent": "info"}},
    {"status": "Active", "role": "active", "badge": None, "display": {"intent": "positive"}},
    {"status": "Approved", "role": "done", "badge": None, "display": {"intent": "positive"}},
    {"status": "Archived", "role": "retired", "badge": None, "display": {"intent": "muted"}},
    {"status": "Blocked", "role": "blocked", "badge": "🔴", "display": {"intent": "danger"}},
    {"status": "Cancelled", "role": "retired", "badge": "⚫", "display": {"intent": "muted"}},
    {
        "status": "ChangesRequested",
        "role": "active",
        "badge": None,
        "display": {"intent": "positive"},
    },
    {"status": "Deferred", "role": "deferred", "badge": "🟣", "display": {"intent": "info"}},
    {"status": "Deprecated", "role": "retired", "badge": None, "display": {"intent": "muted"}},
    {"status": "Done", "role": "done", "badge": "🟢", "display": {"intent": "positive"}},
    {"status": "Draft", "role": "pending", "badge": None, "display": {"intent": "neutral"}},
    {"status": "Fixed", "role": "active", "badge": "🟡", "display": {"intent": "positive"}},
    {"status": "InProgress", "role": "active", "badge": "🟡", "display": {"intent": "positive"}},
    {"status": "InReview", "role": "active", "badge": None, "display": {"intent": "positive"}},
    {"status": "Noted", "role": "done", "badge": "🔵", "display": {"intent": "positive"}},
    {"status": "Open", "role": "attention", "badge": "🔴", "display": {"intent": "danger"}},
    {"status": "Proposed", "role": "pending", "badge": None, "display": {"intent": "neutral"}},
    {"status": "Published", "role": "in_force", "badge": None, "display": {"intent": "info"}},
    {"status": "Ready", "role": "pending", "badge": None, "display": {"intent": "neutral"}},
    {"status": "Rejected", "role": "retired", "badge": None, "display": {"intent": "muted"}},
    {"status": "Requested", "role": "pending", "badge": None, "display": {"intent": "neutral"}},
    {"status": "Superseded", "role": "superseded", "badge": None, "display": {"intent": "muted"}},
    {"status": "Todo", "role": "pending", "badge": "⚪", "display": {"intent": "neutral"}},
    {"status": "Verified", "role": "done", "badge": "🟢", "display": {"intent": "positive"}},
    {"status": "WontFix", "role": "retired", "badge": "⚫", "display": {"intent": "muted"}},
]


ROLES = [
    {
        "role": "active",
        "settled": False,
        "hidden": False,
        "color": "positive",
        "live": True,
        "blocked": False,
        "deferred": False,
    },
    {
        "role": "attention",
        "settled": False,
        "hidden": False,
        "color": "danger",
        "live": False,
        "blocked": False,
        "deferred": False,
    },
    {
        "role": "blocked",
        "settled": False,
        "hidden": False,
        "color": "danger",
        "live": False,
        "blocked": True,
        "deferred": False,
    },
    {
        "role": "deferred",
        "settled": True,
        "hidden": True,
        "color": "info",
        "live": False,
        "blocked": False,
        "deferred": True,
    },
    {
        "role": "done",
        "settled": True,
        "hidden": True,
        "color": "positive",
        "live": False,
        "blocked": False,
        "deferred": False,
    },
    {
        "role": "in_force",
        "settled": True,
        "hidden": False,
        "color": "info",
        "live": False,
        "blocked": False,
        "deferred": False,
    },
    {
        "role": "pending",
        "settled": False,
        "hidden": False,
        "color": "neutral",
        "live": False,
        "blocked": False,
        "deferred": False,
    },
    {
        "role": "retired",
        "settled": True,
        "hidden": True,
        "color": "muted",
        "live": False,
        "blocked": False,
        "deferred": False,
    },
    {
        "role": "superseded",
        "settled": True,
        "hidden": True,
        "color": "muted",
        "live": False,
        "blocked": False,
        "deferred": False,
    },
]


REF_KINDS = [
    {
        "kind": "addresses",
        "label": "Addresses",
        "hint": "A (the resolving work) addresses or follows up on B (feedback, a review)",
        "role": None,
        "direction": None,
    },
    {
        "kind": "blocks",
        "label": "Blocks",
        "hint": "A is blocking B; B cannot proceed while A is open",
        "role": "dependency",
        "direction": "blocker",
    },
    {
        "kind": "depends-on",
        "label": "Depends on",
        "hint": "A depends on B; A cannot proceed while B is open",
        "role": "dependency",
        "direction": "dependent",
    },
    {
        "kind": "duplicates",
        "label": "Duplicates",
        "hint": "A (a later filing) duplicates B (the original)",
        "role": None,
        "direction": None,
    },
    {
        "kind": "fixes",
        "label": "Fixes",
        "hint": "A (the resolving work) fixes the problem tracked by B",
        "role": None,
        "direction": None,
    },
    {
        "kind": "implements",
        "label": "Implements",
        "hint": "A implements the requirement or spec described by B",
        "role": None,
        "direction": None,
    },
    {
        "kind": "related",
        "label": "Related",
        "hint": "Generic cross-reference (default)",
        "role": "default",
        "direction": None,
    },
    {
        "kind": "scopes",
        "label": "Scopes",
        "hint": "A (a skill) is scoped to role B; B's generated pointer preloads A",
        "role": "preload",
        "direction": None,
    },
    {
        "kind": "supersedes",
        "label": "Supersedes",
        "hint": "A (a newer decision) supersedes B (an older one)",
        "role": "supersession",
        "direction": None,
    },
    {
        "kind": "targets",
        "label": "Targets",
        "hint": "A targets B — a navigational membership edge with no engine binding; its "
        "meaning is whatever reads it",
        "role": None,
        "direction": None,
    },
]


VIEWS = [
    {"view": "greeting_skill", "source_kind": "self", "source_name": None, "transform": None},
    {"view": "item_skill", "source_kind": "playbook", "source_name": None, "transform": None},
    {"view": "memory_skill", "source_kind": "self", "source_name": None, "transform": None},
    {
        "view": "milestone_rollup",
        "source_kind": "ref",
        "source_name": "targets",
        "transform": {"module": "squads._view_transforms", "function": "status_rollup"},
    },
    {"view": "role_definition", "source_kind": "role", "source_name": None, "transform": None},
    {"view": "squads_skill", "source_kind": "playbook", "source_name": None, "transform": None},
]


MIGRATIONS = {
    "migrations": [
        {
            "version": "0.2.0",
            "from_schema": "0.1",
            "to_schema": "0.2",
            "summary": "Inline ref kinds; subtask/story/finding status machines; sq-managed "
            "summaries.",
            "manual": "**Restructure each review's free-form findings into tracked "
            "findings.** `sq migrate up` gives every\n"
            "legacy review an empty findings container, but a pre-2 review's "
            "findings are free-form prose (a\n"
            "`## Findings` section and/or a Summary table) that can't be parsed "
            "automatically. For each review\n"
            "review `<n>`, drive an agent with:\n"
            "\n"
            "1. For every prose finding, run\n"
            '   `sq review <n> add-finding "<one-line title>" --severity '
            "critical|high|medium|low|info`,\n"
            '   set its detail with `sq review <n> finding <k> body -m "…"`, and '
            "its state if known\n"
            "   (`sq review <n> finding <k> update --status "
            "Fixed|Verified|WontFix`).\n"
            "2. Map severities from the old legend (🔴 critical · 🟠 high · 🟡 medium "
            "· 🟢 low · 🔵 info);\n"
            "   default to `medium` when a finding had none.\n"
            "3. One finding per real prose entry — do **not** invent; leave a "
            "missing detail as `TODO`.\n"
            "4. Once all are recreated, delete the old `## Findings` prose / "
            "Summary table from the body.\n"
            "5. Verify: `sq review <n> findings` shows them all and `sq check` is "
            "clean.\n",
        },
        {
            "version": "0.3.0",
            "from_schema": "0.2",
            "to_schema": "0.3",
            "summary": "Backfill the human-readable :head region "
            "(status/assignee/severity/story badges).",
            "manual": "## Schema 0.2 → 0.3 — a carried-forward sub-entity status your "
            "lifecycle no longer declares\n"
            "\n"
            "No manual steps are required — `sq migrate up` runs automatically.\n"
            "\n"
            "If a workflow override changed a story/subtask/finding lifecycle "
            "before this ran, a lifted\n"
            "sub-entity's legacy status may no longer be one of that lifecycle's "
            "states. Its status value is\n"
            "carried forward unchanged (never rewritten); run `sq check` after "
            "migrating — it already reports\n"
            "a mismatch as `invalid status` against the item, with a non-zero exit "
            "— then remap by hand:\n"
            "\n"
            "```\n"
            "sq <type> <n> <kind> <k> update --status "
            "<a-valid-status-for-your-lifecycle>\n"
            "```\n",
        },
        {
            "version": "0.5.0",
            "from_schema": "0.3",
            "to_schema": "0.4",
            "summary": "Additive session lineage fields: optional "
            "session_id/parent_session_id on reflog lines and "
            "created_session/modified_session on item frontmatter. Best-effort, "
            "untrusted, observability-only — no file rewrite required.",
            "manual": "## Schema 0.3 → 0.4 — additive session lineage fields\n"
            "\n"
            "No manual steps are required for existing squads.  The new fields are "
            "entirely\n"
            "optional and additive; all existing item files and reflog lines "
            "remain valid\n"
            "without any rewrite.\n"
            "\n"
            "**What the upgrade gives you (once your orchestrator skills propagate "
            "the env\n"
            "vars):**\n"
            "\n"
            "- Set `SQUADS_SESSION_ID` in the environment before calling `sq` "
            "commands to\n"
            "  have every mutating operation record that session id on the reflog "
            "line and on\n"
            "  the item's frontmatter (`created_session` / `modified_session`).\n"
            "- Set `SQUADS_PARENT_SESSION_ID` to record the immediate parent "
            "session (the\n"
            "  session that spawned the current one).\n"
            "- `sq reflog --json` now surfaces `session_id` and "
            "`parent_session_id` fields\n"
            "  on each entry when they were set at write time; absent on legacy "
            "lines.\n"
            "\n"
            "**Important — guarantee framing (read before exposing these fields in "
            "a UI or\n"
            "check):**\n"
            "  squads is a passive tool, never in the spawn path.  It reads "
            "optional env vars\n"
            "  from its own invocation and records them.  The result is "
            "best-effort,\n"
            "  untrusted, observability-only — not tamper-evident, not signed.  A "
            "forged,\n"
            "  copied, or absent session id is indistinguishable from a real one.  "
            "Never use\n"
            "  these fields as an authorisation input.\n",
        },
        {
            "version": "0.5.0",
            "from_schema": "0.4",
            "to_schema": "0.5",
            "summary": "SKILL ids for bundled skills: stamp SKILL-… frontmatter onto every "
            "existing agents/skills/*.md body file in lexical-by-slug order.",
            "manual": "## Schema 0.4 → 0.5 — SKILL ids and filename convention for existing "
            "squads\n"
            "\n"
            "No manual steps are required.  ``sq migrate up`` automatically:\n"
            "\n"
            "1. Stamps every bundled skill body file under ``agents/skills/`` with "
            "a unique\n"
            "   ``SKILL-…`` id (if not already stamped).\n"
            "2. Renames legacy ``<slug>.md`` files to the standard\n"
            "   ``SKILL-<NNNNNN>-<slug>.md`` convention (like "
            "``ROLE-000001-manager.md``).\n"
            "3. Rewrites each ``.claude/skills/<slug>/SKILL.md`` pointer to "
            "reference the\n"
            "   renamed body path.\n"
            "4. Runs ``sq repair`` to rebuild the index.\n"
            "\n"
            "**Verify with:**\n"
            "\n"
            "```\n"
            "sq list -t skill          # all bundled skills should appear with "
            "SKILL-… ids\n"
            "sq skill <n> show         # check a specific skill's frontmatter + "
            "body\n"
            "sq check                  # should be clean\n"
            "```\n"
            "\n"
            "**If any skill body file is missing** (e.g. the squad was initialised "
            "before\n"
            "``sq sync`` wrote the skill files), run ``sq sync`` first and then\n"
            "``sq migrate up`` again.\n",
        },
        {
            "version": "0.7.0",
            "from_schema": "0.5",
            "to_schema": "0.7",
            "summary": "Unpadded display IDs: rewrite every frontmatter id/ref/parent and "
            "body-prose ID mention to the unpadded form; filenames stay padded, "
            "untouched.",
            "manual": "## Schema 0.5 → 0.7 — unpadded display IDs\n"
            "\n"
            "No manual steps are required for the structural rewrite — `sq migrate "
            "up` automatically:\n"
            "\n"
            "1. Reformats every item's frontmatter `id:` to the unpadded form "
            "(`PREFIX-nnn` rather than\n"
            "   `PREFIX-000nnn`), driven by its stored `sequence_id`.\n"
            "2. Unpads every `refs:` entry and `parent:` field.\n"
            "3. Rewrites padded-ID mentions in body prose and sub-entity titles to "
            "their unpadded form,\n"
            "   skipping fenced code blocks and inline code (a literal example ID "
            "there is left as written)\n"
            "   and skipping a padded id that is the stem of an on-disk filename "
            "reference (`PREFIX-000nnn-\n"
            "   slug.md` stays exactly as written — filenames are never "
            "unpadded).\n"
            "4. Runs `sq repair` to rebuild the index.\n"
            "\n"
            "**Filenames are not touched** — they stay padded on disk; only "
            "content changes.\n"
            "\n"
            "**The prose rewrite is best-effort.** It only catches the exact "
            "padded strings this migration\n"
            "already knows about (each item's own prior frontmatter `id:`), "
            "whole-word matched. A body that\n"
            "mentions an ID some other unusual way, or a mention-heavy body, is "
            "worth an eyeball after\n"
            "migrating — run `sq <type> <n> show --full` on a few high-traffic "
            "items and confirm the prose\n"
            "reads as expected.\n"
            "\n"
            "**Custom (spec-declared) item types are not covered.** This runner "
            "only walks the built-in\n"
            "item-type folders "
            "(role/skill/operator/epic/feature/task/bug/decision/review/guide) — a "
            "squad\n"
            "with config-driven custom types (`.squads.toml` item specs) has those "
            "files, their refs, and\n"
            "any prose mentions of their ids left entirely untouched by this "
            "migration. If your squad\n"
            "declares custom types, give them a manual eyeball/pass after `sq "
            "migrate up`: unpad their\n"
            "frontmatter `id`/`refs`/`parent` by hand (or re-`sq create`/re-derive "
            "as appropriate) and check\n"
            "any built-in item's prose that mentions one of their (now "
            "stale-padded) ids.\n"
            "\n"
            "**Verify with:**\n"
            "\n"
            "```\n"
            "sq check                  # should be clean\n"
            "sq list                   # ids render unpadded\n"
            "sq tree PREFIX-n           # resolves and renders unpadded (any valid "
            "epic id works)\n"
            "```\n",
        },
        {
            "version": "0.8.0",
            "from_schema": "0.7",
            "to_schema": "0.8",
            "summary": "Bug severity moves from extra[severity] to a top-level severity: "
            "key; the extra copy is dropped.",
            "manual": "## Schema 0.7 → 0.8 — bug severity moves from `extra` to a top-level "
            "key\n"
            "\n"
            "No manual steps are required — `sq migrate up` automatically, for "
            "every existing bug file that\n"
            "still carries a legacy `extra.severity` entry:\n"
            "\n"
            "1. Lifts the value onto a top-level `severity:` frontmatter key "
            "(skipped if one is already set).\n"
            "2. Drops the `extra` entry, and the whole `extra:` map if severity "
            "was its only member.\n"
            "3. Runs `sq repair` to rebuild the index.\n"
            "\n"
            "Priority (already top-level) and finding severity (already stored on "
            "the sub-entity block) are\n"
            "untouched. If you hand-edited a bug file's `extra` block yourself, "
            "re-run `sq migrate up` after —\n"
            "the relocation is idempotent and safe to repeat.\n"
            "\n"
            "**Verify with:**\n"
            "\n"
            "```\n"
            "sq check                  # should be clean\n"
            "sq bug <n> show --full    # severity badge renders as before\n"
            "```\n",
        },
        {
            "version": "0.10.0",
            "from_schema": "0.8",
            "to_schema": "0.10",
            "summary": "sq-memory becomes a tracked SKILL item: stamp a SKILL-… id onto the "
            "legacy agents/skills/sq-memory.md and move it to the "
            "SKILL-<NNNNNN>-sq-memory.md convention filename, like every other "
            "bundled skill.",
            "manual": "## Schema 0.8 → 0.10 — `sq-memory` becomes a tracked SKILL item\n"
            "\n"
            "No manual steps are required. `sq migrate up` automatically:\n"
            "\n"
            "1. Stamps `agents/skills/sq-memory.md` with a unique `SKILL-…` id (if "
            "not already stamped).\n"
            "2. Renames it to the standard `SKILL-<NNNNNN>-sq-memory.md` "
            "convention (like every other\n"
            "   bundled skill, e.g. `SKILL-000001-squads.md`).\n"
            "3. Rewrites the `.claude/skills/sq-memory/SKILL.md` pointer to "
            "reference the renamed body path.\n"
            "4. Runs `sq repair` to rebuild the index.\n"
            "\n"
            "A fresh `sq init`/`sq sync` on a squad that never had `sq-memory` "
            "already writes it tracked —\n"
            "this migration only matters for squads that predate that fix.\n"
            "\n"
            "**Verify with:**\n"
            "\n"
            "```\n"
            "sq list -t skill          # sq-memory should appear with a SKILL-… "
            "id\n"
            "sq skill <n> show         # check its frontmatter + body\n"
            "sq check                  # should be clean\n"
            "```\n",
        },
        {
            "version": "0.11.0",
            "from_schema": "0.10",
            "to_schema": "0.11",
            "summary": "Schema-stamp-only gate for the new `scopes` ref kind (custom-skill "
            "role scoping); no frontmatter shape change, no file rewrite.",
            "manual": "",
        },
        {
            "version": "0.14.0",
            "from_schema": "0.11",
            "to_schema": "0.14",
            "summary": "Two new bundled item types, contract (PRD) and milestone (MILE): "
            "create their folders on an existing squad and regenerate the managed "
            "skills, pointers and compiled CLAUDE.md/AGENTS.md regions so both "
            "appear.",
            "manual": "## Schema 0.11 → 0.14 — two new item types\n"
            "\n"
            "Two item types are now available:\n"
            "\n"
            "- **contract** (`PRD`) — the living functional contract: what the "
            "product does for a user,\n"
            "  right now, kept current in place as the product evolves.\n"
            "- **milestone** (`MILE`) — a named target for a set of work (a "
            "release, a cycle, anything work\n"
            "  can be aimed at); a work item joins one by carrying a `targets` ref "
            "to it.\n"
            "\n"
            "Run `sq sync` next. Any existing role that interacts with either type "
            "— the bundled playbook\n"
            "covers `architect`, `product-owner`, `tech-lead` and every "
            "`<tech>-dev` — still carries its\n"
            "pre-0.14 preload list in its own `.claude/agents/<slug>.md` pointer "
            "until then; `sq check` will\n"
            "flag it in the meantime. Optionally, seed a first item of either type "
            "for your squad's current\n"
            "capabilities:\n"
            "\n"
            "```\n"
            "sq sync\n"
            "sq create contract\n"
            "sq create milestone\n"
            "```\n"
            "\n"
            "## Stored regions and role metadata are removed from your item files\n"
            "\n"
            "This happens in the **index rebuild at the end of `sq migrate up`**, "
            "not in the step above.\n"
            "`sq repair`, `sq adopt` and `sq renumber` all reach the same rebuild "
            "and perform the same\n"
            "removal. Expect a content diff across your corpus; review it before "
            "committing, and prefer a\n"
            "clean working tree when you run any of them, since none can separate "
            "its changes from yours.\n"
            "All four print one line counting the item files they rewrote, and "
            "name those items in the\n"
            "reflog — `sq renumber` under its own entry, by their post-shift ids. "
            "That is a count and a list\n"
            "of ids, not the change itself, so read `git diff` for what actually "
            "moved.\n"
            "\n"
            "What goes, and what answers for it now:\n"
            "\n"
            "- **The sub-entity roll-up table and each block's badge line**, from "
            "any item file that carries\n"
            "  them. Both were snapshots of state that lives in the item's "
            "frontmatter, rewritten on every\n"
            "  change and stale the moment two branches touched the same item. `sq "
            "<type> <n> show` renders\n"
            "  both from the frontmatter on every read, so nothing is lost and "
            "nothing can disagree any more.\n"
            "- **A role's stored body**, which was a rendered copy of its "
            "definition. `sq role <slug> show`\n"
            "  renders that definition fresh on every call, from the role catalog "
            "and your own role\n"
            "  overrides. If you defined a role yourself, check its "
            "`.overrides/roles/<slug>.toml` is in\n"
            "  place first: a role item that resolves against neither the catalog "
            "nor an override has nothing\n"
            "  left to render from once the stored copy is gone.\n"
            "- **The `extra` keys a role item mirrored from that same definition** "
            "— `full_name`, `title`,\n"
            "  `mission`, `responsibilities`, `agreements`, `color`, `can_spawn`, "
            "`description` and the\n"
            "  `skills` cache. Nothing writes any of them any more.\n"
            "\n"
            "A role's body is emptied, never deleted: the marker pair stays and "
            "only its contents go.\n"
            "\n"
            "**What a role keeps:** its `slug`, its default-role designation if it "
            "holds one, and — on a\n"
            "developer role — its `model`, `is_dev` and `tech`, since `sq dev add` "
            "and `sq role set-default`\n"
            "still write those. A non-developer role's stored `model` is removed "
            "with the rest. A role's own\n"
            "top-level `title`, `status`, `author`, timestamps and refs are "
            "untouched, so `sq role list` and\n"
            "`sq role <slug> show` still name every role exactly as before.\n"
            "\n"
            "**No skill body is touched.** A **custom** skill — one you created "
            "with `sq skill add` — is\n"
            "authored storage, is byte-identical afterwards, and keeps rendering "
            "from what you wrote,\n"
            "including one whose slug happens to start with `sq-`. A "
            "**template-owned** skill's stored body\n"
            "is left alone too: whether a slug is template-owned is a question "
            "about today's vocabulary and\n"
            "a stored body was written under an earlier one, so on disk the two "
            "are indistinguishable. What\n"
            "a bundled or `sq-<type>` skill still stores is simply inert — `sq "
            "skill <slug> show` renders\n"
            "that definition from its template on every call and never reads it.\n"
            "\n"
            "Untouched as well: every sub-entity's body and discussion, every item "
            "body other than a role's,\n"
            "every operator item, and every frontmatter field on anything that is "
            "not a role.\n"
            "\n"
            "One behaviour changes with the bytes: text that lived only in a "
            "removed region is no longer\n"
            "matched by `sq search`. Read a role's mission and responsibilities "
            "through `sq role <slug> show`\n"
            "and a sub-entity's status through `sq <type> <n> show` or `sq "
            "list`.\n",
        },
        {
            "version": "0.15.0",
            "from_schema": "0.14",
            "to_schema": "0.15",
            "summary": "The milestone roll-up moves off its type attachment onto a "
            "sq:view:milestone_rollup body tag: seed the tag on every existing "
            "milestone lacking one, through the tool's own marker-safe placement "
            "primitive. Also reclaims a pre-0.14 "
            "role/permanently-system-skill/sq-<type>-skill body still carrying a "
            "legacy plain-prose rendering onto its own tag.",
            "manual": "## Schema 0.14 → 0.15 — views are positioned, disabled rather than "
            "removed\n"
            "\n"
            "The milestone roll-up (`sq milestone <n> show`) used to be a "
            "type-attached view\n"
            "(`items.milestone.views`); it is now placed by a "
            "`sq:view:milestone_rollup` tag inside the\n"
            "milestone's own `sq:body` region — the same mechanism a role's own "
            "definition, and each\n"
            "system/per-item-type skill's text, already render through.\n"
            "\n"
            "This migration inserts that tag into every existing milestone body "
            "that does not already carry\n"
            "one, through the tool's own marker-safe placement routine (never a "
            "bespoke write into authored\n"
            "prose) — so **every milestone body in your corpus gains one line**. "
            "`sq migrate up` reports how\n"
            "many; review the diff before committing, the same posture every "
            "migration that touches your\n"
            "corpus asks for. A milestone whose body you had already hand-edited "
            "to carry the tag, or that\n"
            "carries no `sq:body` region at all, is left exactly as it was.\n"
            "\n"
            "A milestone this migration cannot safely place the tag on is "
            "**skipped, not aborted**: the run\n"
            "still completes and the rest of your corpus is still migrated. `sq "
            "migrate up` names every\n"
            "skipped item by id, and `sq check` (reachable again once the run "
            "completes) reports what it\n"
            "still needs — a body with no `sq:body` region needs one added by "
            "hand. Once that item's own\n"
            "problem is fixed, place the tag with `sq milestone <n> view add "
            "milestone_rollup`.\n"
            "\n"
            "A milestone whose tag you had already moved outside `sq:body` by hand "
            "is skipped too, for a\n"
            "different reason: it already carries the tag, so this migration "
            "leaves it exactly as it was\n"
            "rather than insert a second, in-region copy alongside it (which would "
            "duplicate it, not\n"
            "recognise it). That out-of-region placement is not a shape to leave, "
            "though — every body write\n"
            "now re-inserts any seeded tag missing from inside `sq:body`, so the "
            "next one (a plain `body`\n"
            "call, `--append`, or this same `view add`) plants a second, in-region "
            "copy next to the\n"
            "out-of-region one, and `sq check` then reports `duplicate "
            "sq:view:milestone_rollup tag`. Fix it\n"
            "before that happens: delete the out-of-region line from the file by "
            "hand, then run\n"
            "`sq milestone <n> view add milestone_rollup` to place it back inside "
            "`sq:body`, where every\n"
            "other milestone's already is.\n"
            "\n"
            "No other item type is touched by this step: only a type whose "
            "*creation template* currently\n"
            "seeds a view tag is in scope, and today that is milestone alone.\n"
            "\n"
            "## The same step also reclaims pre-0.14 role/skill bodies\n"
            "\n"
            "A role's own definition, each permanently-system skill's (`squads`, "
            "`greeting`, `sq-memory`)\n"
            "text, and each per-item-type `sq-<type>` skill's guidance has "
            "rendered off a\n"
            "`sq:view:<name>` tag since 0.14. Before that, every one of those "
            "writers rendered the resolved\n"
            "text straight into the body instead. If your corpus still carries one "
            "of those pre-0.14\n"
            "renderings — plain prose, no marker of any kind — this step converges "
            "it onto its own tag the\n"
            "same marker-safe way, and reports how many bodies it changed.\n"
            "\n"
            "An empty body and an already-tagged one are both left exactly as they "
            "are — this step only\n"
            "ever touches the legacy shape named above, on a document whose "
            "current roster classification\n"
            "names a declared view. Every other marker-free, non-empty body this "
            "step reaches is overwritten\n"
            "onto its tag unconditionally, whatever it holds: before 1.0, this "
            "step does not try to tell a\n"
            "genuine pre-0.14 rendering apart from an author's own runbook that "
            "happens to share a\n"
            "per-item-type skill's slug. A custom skill matching no declared type "
            "is never touched, because\n"
            "it carries no such tag to begin with.\n"
            "\n"
            "A body carrying marker-shaped content this step doesn't recognise is "
            "skipped the same way,\n"
            "named by id, with nothing written; `sq check` (reachable once the "
            "schema stamp lands) names the\n"
            "finding. `sq repair`'s own convergence sweep does not touch it either "
            "— it converges only a\n"
            "genuinely empty region. Once you have taken the marker-shaped content "
            "out by hand, the document\n"
            'is in exactly the "prose beside a missing tag" shape an adopted '
            "pre-0.14 corpus reaches too —\n"
            "`sq check` then names the same four-step remedy either way, the only "
            "one that converges to a\n"
            "single live rendering: (1) drop `<name>` from `[selected]` in "
            "`.overrides/workflow.toml` — this\n"
            "makes the host briefly not roster-classified, which is what lifts its "
            "body write refusal long\n"
            'enough for step 2; (2) clear the text — `sq skill <slug> body -m "" '
            "--force` for a skill, or,\n"
            "for a role (which has no `body` verb at all), a single-event bulk "
            "import against its own id,\n"
            "piped over stdin: `echo "
            '\'{"op":"body","target":"<id>","body":"","force":true}\' | sq import '
            "-`;\n"
            "(3) restore `<name>` to `[selected]`; (4) `sq role|skill <slug> view "
            "add <name>`. `view disable\n"
            "<name>` alone does not achieve this: it renders nothing, but the "
            "legacy prose it leaves beside\n"
            "the disabled tag can never be cleared afterward — the roster write "
            "refusal has no\n"
            "`[selected]`-dropped window open once the tag (disabled or not) is "
            "back in place, so this\n"
            "stranded prose becomes permanent. Reach for `view disable` only when "
            "you genuinely want the\n"
            "document to render nothing (the escape the roster refusal's own "
            "message already names), never\n"
            "as a stand-in for the four-step remedy above.\n",
        },
        {
            "version": "0.16.0",
            "from_schema": "0.15",
            "to_schema": "0.16",
            "summary": "Comment headers name the author's permanent slug. Item frontmatter "
            "is flat: the extra block is lifted to top-level keys. The developer "
            "marker is dropped from role items, and roles named -dev that declare "
            "no capability are reported. Every role and skill records whether it "
            "is system or project. Every skill file has a discussion region.",
            "manual": "This step checks every part before it writes any file: if any part "
            "finds a problem, this step\n"
            "writes nothing, the schema stamp stays as it is and the command lists "
            "every problem at once.\n"
            "\n"
            "On a squad still behind the package, `sq migrate up`, `sq migrate "
            "help`, `sq migrate chlog`,\n"
            "`sq override list`, `sq override diff` and `sq override update` run; "
            "every other command is\n"
            "refused. The purge steps below use `rm --purge`, which both the 0.15 "
            "tool and 0.16 accept (0.16\n"
            "also accepts `remove`).\n"
            "\n"
            "### Comment headers name the author's slug\n"
            "\n"
            "Every comment header changes from `- [<timestamp>] <name>:` to\n"
            "`` - [<timestamp>] `<slug>` <name>: ``. `sq migrate up` rewrites the "
            "header line of every\n"
            "comment, in each item's discussion and in each story's, subtask's and "
            "finding's, and nothing\n"
            "else in a discussion: a comment's own lines stay byte for byte. It "
            "reports how many headers it\n"
            "rewrote and in how many files. The next section changes the "
            "frontmatter. Review the diff before\n"
            "you commit it.\n"
            "\n"
            "The slug is found from the name. Each name is looked up among the "
            "squad's roles and operators,\n"
            "retired ones included, and the two names sq writes itself (`Operator` "
            "and `squads`). A role is\n"
            "known by its name (the `Name` column of `sq role list`); an operator "
            "by the full name its file\n"
            "stores under `extra:`, or by its slug when it stores none, which is "
            "what the earlier release\n"
            "wrote in its comments. The next section then makes that full name the "
            "operator's `title`.\n"
            "Every name is\n"
            "resolved before any file is written. If one cannot be, this step "
            "writes nothing, the schema stamp\n"
            "is unchanged and the command exits 1 with one line per header, then a "
            "count, then one line per\n"
            "distinct name:\n"
            "\n"
            "    tasks/TASK-NNNNNN-add-login.md:41: 'Hugo Ops' matches no roster "
            "entry\n"
            "    tasks/TASK-NNNNNN-add-login.md:57: 'Sam Lee' matches 2 entries: "
            "op-sam, qa\n"
            "    bugs/BUG-NNNNNN-crash.md:33: '2026-06-07 10:00' is not a "
            "timestamp sq writes\n"
            "    3 problem(s) found.\n"
            "      'Hugo Ops': 1 header(s) in 1 file(s)\n"
            "      'Sam Lee': 1 header(s) in 1 file(s)\n"
            "\n"
            "What to do for each, before running `sq migrate up` again:\n"
            "\n"
            "- **A name that matches no entry.** The role or operator that wrote "
            "those comments is no longer\n"
            "  in the squad. Add it back under that name with the earlier release: "
            "`sq role activate <slug>\n"
            '  --name "<name>"` for a role (`sq role catalog` lists the slugs), '
            "`sq dev add --tech <tech>\n"
            '  --name "<name>"` for a developer role, `sq operator add "<name>" '
            "--slug <old-slug>` for an\n"
            "  operator. A retired entry counts, so it can be retired again "
            "afterwards. If the entry is still\n"
            "  there under a newer name, both names cannot resolve at once: "
            "replace the older name in those\n"
            "  header lines by hand.\n"
            "- **A name that matches several entries.** Two entries share that "
            "name, and every header with it\n"
            "  will belong to one of them. Give the other a distinct name for the "
            "run by editing its file:\n"
            "  `title:` for a role, `full_name:` under `extra:` for an operator "
            "(the file still has the\n"
            "  earlier shape). The run keeps a role's `title:` and makes the "
            "operator's `full_name` its\n"
            "  `title:`, so the name typed for the run stays until you edit the "
            "`title:` line back to the real\n"
            "  name and run `sq repair`.\n"
            "- **A timestamp sq does not write.** The line starts at the left "
            "margin inside a discussion and\n"
            "  looks like a header. If it is text that was pasted there, indent it "
            "under its comment. If it\n"
            "  is a header, correct its timestamp to the form "
            "`2026-06-07T10:00:00Z`.\n"
            "- **A discussion that is never closed.** Its closing marker line is "
            "missing. Restore it.\n"
            "- **A discussion marker that shares its line with text, or is not "
            "spelled as sq writes it.** Put\n"
            "  each `sq:` marker on a line of its own, spelled as sq writes it "
            "(the tag between `<!--` and\n"
            "  `-->`, one space on each side).\n"
            "\n"
            "Changes to the roster are made with a squads release that reads the "
            "squad's schema; the refusal\n"
            "names one. Until the migration completes, this release runs nothing "
            "on the squad but\n"
            "`sq migrate up`, `sq migrate help` and `sq migrate chlog`. On a squad "
            "stamped below 0.15, run\n"
            "`sq migrate up` with 0.15.0 first, then change the roster with it. "
            "There is no option that maps\n"
            "a name to a slug by hand.\n"
            "\n"
            "A header already in the new form is left as it is, so the command can "
            "be run again safely.\n"
            "\n"
            "### A role or operator whose slug breaks the rules refuses the run\n"
            "\n"
            "Before it resolves any header, the step checks every role and "
            "operator, retired ones included.\n"
            "An operator's slug is `op-` followed by lowercase letters, digits and "
            "hyphens. A role's slug is\n"
            "lowercase letters, digits and hyphens, and is neither `operator` nor "
            "`squads` nor anything that\n"
            "starts with `op-`. No slug is held by two entries. An entry that "
            "breaks a rule refuses the run\n"
            "like an unresolvable header: nothing is written, the schema stamp is "
            "unchanged and the command\n"
            "exits 1, with one line for the entry, naming its file, its slug, the "
            "rule and the other holders:\n"
            "\n"
            "    operators/OP-000012-qa.md: operator slug 'qa' does not start with "
            "'op-'; also held by ROLE-5\n"
            "\n"
            "It is refused, and not only reported, because this is the last point "
            "where the slug can change.\n"
            "Once the headers carry it no later step rewrites them, so a reserved "
            "slug would turn comments\n"
            "into system entries, `operator` would make them anonymous, and a slug "
            "shared with a role would\n"
            "make them editable by whoever holds it.\n"
            "\n"
            "What to do for each, with the release the squad is stamped for, "
            "before running `sq migrate up`\n"
            "again:\n"
            "\n"
            "- **An operator.** Run `sq operator <id> rm --purge`, using the ID in "
            "the line, then\n"
            '  `sq operator add "<the same full name>"`, which takes `op-` and the '
            "first name unless you pass\n"
            "  a compliant `--slug`. The purge is required: a plain `rm` drops the "
            "entry from the index but\n"
            "  keeps its file, and the next run reads that file again. The "
            "comments that named the operator\n"
            "  then resolve to the new slug. Reassign the open items assigned to "
            "the old slug with\n"
            "  `sq <type> <n> update --assignee <new slug>`. An item's `author` "
            "keeps the old slug, and\n"
            "  `sq check` reports it as not registered.\n"
            "- **A role.** Give the role's project definition a compliant slug "
            "(the file under\n"
            "  `<squad folder>/.overrides/roles/`, renamed, and its `slug` line "
            "with it), run\n"
            "  `sq role activate <new slug>`, then `sq role <id> rm --purge` for "
            "the old entry.\n"
            "- **A slug held by two entries.** Both entries are listed, each "
            "naming the other. Replace the one\n"
            "  that breaks a rule above, or the one you can spare, the same way.\n"
            "\n"
            "### The frontmatter is flat\n"
            "\n"
            "An item file keeps its fields as top-level keys; the nested `extra:` "
            "block is gone. `sq migrate\n"
            "up` lifts each key of `extra:` to the top level with its value "
            "unchanged, in every item file, and\n"
            "rewrites nothing in the file but its frontmatter. The exceptions:\n"
            "\n"
            "- `slug` becomes the top-level `slug`, written on every role, skill "
            "and operator file. A roster\n"
            "  file that stores none (an operator an earlier importer created) "
            "gets the slug its file name\n"
            "  spells.\n"
            "- A skill's `description` under `extra:` is dropped when its "
            "top-level `description` is not\n"
            "  empty, and otherwise becomes the `description` unless it is the "
            "skill's title.\n"
            "- An operator's `full_name` is dropped. The operator's `title` takes "
            "its value when the two\n"
            "  differ, because that is the name every operator surface showed; the "
            "run lists those files.\n"
            "- A role's mirrored definition keys (`title`, `mission`, "
            "`responsibilities`, `agreements`,\n"
            "  `color`, `can_spawn`, `description`, `full_name`, `skills`) are "
            "dropped: the role catalog answers\n"
            "  them.\n"
            "- `ref_kinds` is folded into the item's refs and `severity` becomes "
            "the top-level `severity`\n"
            "  when that is absent.\n"
            "- The top-level `path:` key that an old release wrote on skill files "
            "is removed.\n"
            "\n"
            "Every other key, one this squad's spec declares or one an adopter "
            "added, is kept as written, and\n"
            "the `extra:` key is removed. A file that needs nothing is not "
            "touched, so a second run changes\n"
            "nothing. The run reports how many files it flattened, how many keys "
            "it lifted per key, how many\n"
            "skill descriptions and `path:` keys it removed and which operators it "
            "retitled. When a dropped\n"
            "skill description differed from the one kept, the run also lists "
            "those files.\n"
            "\n"
            "A role keeps the name it stores, whatever the configuration says: the "
            "step changes no name, and\n"
            "`sq sync` never renames a role. A new role takes its name from "
            "`--name`, else from the\n"
            "configuration, when it is created.\n"
            "\n"
            "Like the comment headers, the flattening is checked before anything "
            "is written. These make the\n"
            "step write nothing, leave the schema stamp as it is and exit 1, one "
            "line per file:\n"
            "\n"
            "    tasks/TASK-NNNNNN-add-login.md: extra is not a mapping\n"
            "    guides/GUIDE-NNNNNN-notes.md: extra.tech and the top-level tech "
            "hold different values\n"
            "    agents/roles/ROLE-NNNNNN-qa.md: extra.slug 'quality' differs from "
            "the file name's slug 'qa'\n"
            "    guides/GUIDE-NNNNNN-notes.md: extra.path would become the item's "
            "own 'path'; move it out by hand\n"
            "\n"
            "Edit the file so the two places agree (drop the one you do not want), "
            "then run `sq migrate up`\n"
            "again.\n"
            "\n"
            "### A developer is a role that declares a capability\n"
            "\n"
            "A developer is now a role whose role file declares a capability the "
            "`[dev]` table of the role\n"
            "catalog also declares (the bundled catalog declares `dev`). The "
            "stored `is_dev` marker is gone.\n"
            "`sq migrate up` removes it from developer items and changes nothing "
            "else in them: the name,\n"
            "`tech` and `model` stay as they were.\n"
            "\n"
            "- A role the run reports keeps working as an ordinary role. It "
            "regains the developer guidance\n"
            "  when its role file declares the capability and `sq sync` runs; "
            "there is no automatic fix.\n"
            "- An override file written for a developer that was not added yet is "
            "now reported by `sq check`;\n"
            "  the ways out are `sq dev add` or removing the file.\n"
            "- An existing developer picks up a project `[dev]` colour on the next "
            "`sq sync` and keeps the\n"
            "  model and the name it was created with.\n"
            "- A stamped catalog, playbook, workflow or per-slug role override "
            'reports "may be stale" because\n'
            "  the bundled documents changed: run `sq override diff`, then `sq "
            "override update`.\n"
            "\n"
            "### Every role and skill records its origin\n"
            "\n"
            "Each role and skill file stores `origin: system` or `origin: "
            "project`. `sq migrate up` adds it\n"
            "to every role and skill that stores none, and reports how many of "
            "each it stamped. A role or\n"
            "skill the bundled catalog or the spec's generated skills name is "
            "`system`, and so is a templated\n"
            "developer (a role that stores `tech`); everything else, a declared "
            "developer included, is\n"
            "`project`. A bundled role the project overrides stays `system`. A "
            "file that already stores an\n"
            "`origin` is left as it is, so a second run changes nothing.\n"
            "\n"
            "### Every skill has a discussion\n"
            "\n"
            "Each skill file now carries a `## Discussion` heading and an empty "
            "discussion region after its\n"
            "body region, as role and operator files do, so a skill takes "
            "comments. `sq migrate up` appends\n"
            "them to every skill file that has none, byte for byte and in the "
            "file's own line endings, and\n"
            "leaves a file that already has one as it is, so a second run changes "
            "nothing.\n",
        },
        {
            "version": "0.17.0",
            "from_schema": "0.16",
            "to_schema": "0.17",
            "summary": "Roles take their base into the item: developers store their "
            "template, custom roles their definition.",
            "manual": "Rename a `[dev]` table in `.overrides/roles.toml` to "
            "`[templates.dev]` before upgrading: `sq migrate up` refuses a squad "
            "whose role catalog still carries `[dev]`, and changes nothing. A role "
            "defined only by a per-slug file takes that definition into its own "
            "item; the file then layers over it, and `sq check` warns until you "
            "delete the file.",
        },
    ]
}
