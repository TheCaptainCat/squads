# squads workflow

The process squads coordinates has two layers: **who creates and links what** (the team workflow)
and **how each item moves through its states** (the status lifecycle). `sq workflow` prints a short
version of the first; this is the full reference. The rules are enforced — at `create`/`link`/`status`
time and by `sq check`.

---

## Team workflow

```
        product owner                         tech lead
            │                                    │
            ▼                                    ▼
   ┌──────────────────┐  parent   ┌───────────────────────────┐
   │ FEATURE          │◀──────────│ TASK                       │
   │  + user stories  │           │  parent = the feature      │
   │    US1, US2, …   │◀╌╌╌╌╌╌╌╌╌╌│  subtask ST1 (→ US1) …     │
   └──────────────────┘  maps to  └───────────┬───────────────┘
            ▲ parent                          │ refs
   ┌────────┴────────┐              ┌─────────┴───────────┐
   │ EPIC            │              │ BUG  (--kind fixes) │
   │ (groups feats)  │              │ REVIEW (--kind addresses)
   └─────────────────┘              └─────────────────────┘
```

- The **product owner** authors **features** (`sq create feature`) and their **user stories**
  (`sq feature <n> add-story`); defines acceptance criteria.
- The **tech lead** authors **tasks** (`sq create task`) and breaks them down:
  - a task's **parent is the feature** it implements (`--parent FEAT-…`);
  - each **subtask maps to one user story** of that feature (`sq task <n> add-subtask … --story USn`);
  - a task that fixes a bug or follows up a review links it as a **ref**
    (`sq task <n> ref add <id> --kind fixes|addresses`);
  - a purely-technical task has no feature parent and no such ref.
- The hierarchy spine is **epic → feature → task**, with **subtasks → user stories**.
- Other roles read these to do their work: **QA** derives tests from user stories; the **reviewer**
  drives review items; the **architect** records **ADRs** and authors **guides**.

### Enforced rules

- `task.parent` must be a **feature**; `feature.parent` must be an **epic** (`ALLOWED_PARENTS`).
  Bugs/reviews attach as refs, **not** as a task's parent.
- A subtask's `(→ USn)` must exist in the task's parent feature.
- `sq check` flags violations (bad parent type, dangling subtask→US, dangling refs).

### Commands at a glance

```bash
# product owner
sq create feature "User authentication" --parent EPIC-000001
sq feature 2 add-story "As a user, I want to log in"

# tech lead
sq create task "Validate token" --parent FEAT-000002
sq task 3 add-subtask "Check expiry" --story US1
sq task 3 ref add BUG-000009 --kind fixes        # or REV-… --kind addresses

# everyone
sq task 3 status InProgress
sq task 3 comment --as reviewer -m "@qa please verify the redirect"
sq inbox qa

# humans (operators) are participants too
sq operator add "Pierre Chat"                 # → op-pierre
sq task 3 update --assignee op-pierre          # assign a manual step to a person
sq task 3 comment --as op-pierre -m "approved" # record the human's own words
```

---

## Type-command aliases

Short and single-letter aliases for the item-type commands provide input sugar for faster typing. They are hidden from the root `--help` listing but fully equivalent: every alias accepts everything the canonical type command does, including sub-entity chains (e.g., `sq f 26 story 4 show` ≡ `sq feature 26 story 4 show`). Output and errors always use the canonical type names and full IDs, regardless of the alias used.

| Canonical | Aliases | Example |
|---|---|---|
| `epic` | `e` | `sq e <n> show` |
| `feature` | `feat`, `f` | `sq f <n> show` |
| `task` | `t` | `sq t <n> show` |
| `bug` | `b` | `sq b <n> show` |
| `decision` | `dec`, `d` | `sq d <n> show` |
| `review` | `rev`, `r` | `sq r <n> show` |
| `guide` | `g` | `sq g <n> show` |

**Evolution rule (see the [stability contract](stability.md)):** adding an alias is additive and allowed; removing or repurposing an alias is a breaking change and is not permitted after 1.0. The alias table is frozen grammar in the same stability tier as the canonical command names.

---

## Status lifecycles

Every item type has its own state machine. `sq status <ID> <Status>` only allows a transition the
machine permits; `--force` overrides. New items start at the machine's initial state.

```
work items (epic · feature · task · bug)
    Draft ──▶ Ready ──▶ InProgress ──▶ InReview ──▶ Done ┄┄▶ (reopen) InProgress
                          ▲                └──────────┘ rework
    Blocked  ⇄  Ready / InProgress / InReview          Cancelled ◀── any non-terminal

ADR (decision)   Proposed ──▶ Accepted ──▶ Superseded     (Proposed ─▶ Rejected ; Accepted ─▶ Deprecated)
review           Requested ─▶ InReview ─▶ Approved        (InReview ⇄ ChangesRequested ; any ─▶ Rejected)
guide            Draft ──▶ Published ──▶ Deprecated        (⇄ both directions)
role · skill     Draft ──▶ Active ⇄ Archived

  ─▶ allowed transition   ⇄ both ways   ┄▶ escape hatch   terminal states have no outgoing edge
```

| Type | Initial | Transitions |
|------|---------|-------------|
| epic / feature / task / bug | `Draft` | Draft→{Ready, InProgress, Cancelled}; Ready→{InProgress, Blocked, Cancelled}; InProgress→{InReview, Blocked, Done, Cancelled}; InReview→{InProgress, Done, Blocked, Cancelled}; Blocked→{Ready, InProgress, Cancelled}; Done→{InProgress}; Cancelled→{Draft} |
| decision (ADR) | `Proposed` | Proposed→{Accepted, Rejected}; Accepted→{Superseded, Deprecated}; Rejected→{Proposed} |
| review | `Requested` | Requested→{InReview, Rejected}; InReview→{ChangesRequested, Approved, Rejected}; ChangesRequested→{InReview, Rejected} |
| guide | `Draft` | Draft→{Published}; Published→{Deprecated, Draft}; Deprecated→{Published} |
| role / skill | `Draft` | Draft→{Active}; Active→{Archived}; Archived→{Active} |

**Terminal states** (no outgoing transitions) are `Done`, `Cancelled`, `Rejected`, `Superseded`,
`Deprecated`, `Archived`, `Approved`, `Verified`, `WontFix`. `sq inbox` only surfaces **open**
(non-terminal) items.

> Status is stored in the `.md` frontmatter *and* mirrored in the index. The dated discussion
> entries (`sq comment`) are what record the *history* of a transition — see
> [adoption.md](adoption.md) for replaying that history with `--at`.

The machines themselves live in `squads._workflow` (`WORKFLOWS`, `can_transition`, `TERMINAL`,
`ALLOWED_PARENTS`); see [internals.md](internals.md) for how they're wired in.

## Sub-entities: subtasks, user stories, findings

The sub-entities (subtasks/stories/findings) are tracked by `sq` too — each has its own status, and
the parent shows an **sq-managed summary table** that rolls them up (regenerated on every change).
Their state (status/assignee/severity/story) lives in the parent item's **frontmatter** (so the index
sees them); the block in the body holds only the prose and a derived badge header. The block's **body
is sq-managed too** — set it with `sq <type> <n> <kind> <k> body -m
"…"` (or `--file body.md` / `--file -`) and read the whole block with `sq <type> <n> <kind> <k> show`;
no manual markdown editing.

| Sub-entity | Lives on | Add / transition | Lifecycle |
|------------|----------|------------------|-----------|
| **subtask** | task | `sq task <n> add-subtask "…" [--story US1]` · `sq task <n> subtask <k> update --status <S>` | `Todo → InProgress → Done` (+ Blocked, Cancelled) |
| **user story** | feature | `sq feature <n> add-story "…"` · `sq feature <n> story <k> update --status <S>` | `Todo → InProgress → Done` (+ Blocked, Cancelled) |
| **finding** | review | `sq review <n> add-finding "…" --severity high` · `sq review <n> finding <k> update --status <S>` | `Open → Fixed → Verified` (+ WontFix) |

`sq <type> <n> <kind> <k> update` is the one metadata entry point for a sub-entity — `--title`,
`--status` (+`--force`), `--assignee`/`--clear-assignee`, plus a subtask's `--story`/`--no-story` and
a finding's `--severity`. Findings carry a **severity** (🔴 critical · 🟠 high · 🟡 medium · 🟢 low ·
🔵 info), set at `add` time and changeable with `update --severity`. Transitions are validated by the
sub-entity machines (`squads._workflow.SUBENTITY_WORKFLOWS`); `--force` overrides.

---

## Operation reflog (`sq reflog`)

Every mutating `sq` command appends one JSON line to `squads/.reflog.jsonl` — an append-only
**operation log**. The reflog is **advisory**: the index
(`.squads.json`) and the markdown files remain the source of truth. `sq repair`, `sq check`, and
`sq load` never read it.

### Line shape

Each line is a JSON object with these fields:

| Field | Type | Meaning |
|-------|------|---------|
| `v` | `string` | Schema version (`"0.3"` — forward-compatible by addition) |
| `ts` | `string` | ISO-8601 UTC timestamp of the operation |
| `actor` | `string` | Role slug (`python-dev`, `system`, `op-pierre`, …) performing the write |
| `op` | `string` | Operation name (see table below) |
| `target` | `string` | Primary item ID affected (empty `""` for squad-level ops) |
| `delta` | `object` | Free-form before/after detail — shape varies by `op` |

**Op names:**

| `op` | Triggered by |
|------|-------------|
| `create` | `sq create …` |
| `status` | `sq <type> <n> status …` |
| `update` | `sq <type> <n> update …` |
| `body` | `sq <type> <n> body …` |
| `comment` | `sq <type> <n> comment …` |
| `subentity` | add-subtask / add-story / add-finding / sub-entity update/body |
| `ref` | `sq <type> <n> ref add|rm …` |
| `link` | `sq link` / `sq unlink` |
| `remove` | `sq remove …` |
| `retype` | `sq <type> <n> retype …` |
| `repair` | `sq repair` |
| `migrate` | `sq migrate up` / `sq migrate repad` |

### Reading the reflog

```bash
sq reflog                          # last 50 entries (default)
sq reflog --tail 0                 # all entries
sq reflog --item TASK-000042       # filter to one item
sq reflog --actor python-dev       # filter by actor slug
sq reflog --op status              # filter by operation
sq reflog --since 2026-06-01       # since a date (ISO 8601)
sq reflog --json                   # machine-readable JSON array
```

Filters are AND-ed. `--json` emits a JSON array of `ReflogEntry` objects matching the line shape.

### Durability and ordering guarantees

- Each line is appended **after** the index `os.replace` commit while still holding the file lock.
  Applied-without-logged is possible (crash between commit and append); logged-without-applied is
  designed out.
- The file is opened with `O_APPEND` — a single `write()` call is atomic on POSIX for the line
  sizes used; no per-line `fsync`.
- A missing or truncated reflog is always tolerated — never an error. Back-compat with pre-1.0
  squads is guaranteed: squads without a reflog simply show empty results.

> The `delta` sub-field keys are additive and may grow across releases. A full stability contract
> for `delta` shapes is deferred to the 1.0 freeze.

---

## Project workflow overrides

By default, squads uses a built-in set of item types, statuses, and state machines. If your project needs custom vocabulary — for example, an `incident` type for on-call workflows — you can extend the built-in spec by writing a project-level **workflow override** in TOML. The override is **additive-only**: you can add new types and statuses, but cannot modify or remove built-in ones.

### Creating an override

To scaffold a starter override file:

```bash
sq override scaffold workflow
```

This creates `.overrides/workflow.toml` in your squad directory (next to `.squads.json`) with a commented-out worked example. Edit this file to add your custom types, statuses, and state machines.

### Override format

The override file is standard TOML with three sections: `[lifecycles.*]`, `[statuses.*]`, and `[items.*]`.

#### Lifecycles

A lifecycle defines the allowed state transitions for an item type or sub-entity kind. Each lifecycle must specify:
- `initial` — the starting status when a new item is created
- `transitions` — a map of allowed transitions (source status → list of target statuses)

```toml
[lifecycles.incident]
initial = "Triage"

[lifecycles.incident.transitions]
Triage = ["Mitigating", "Resolved"]
Mitigating = ["Resolved", "Triage"]
Resolved = ["Triage"]
```

Lifecycles are identified by name. You may reference a built-in lifecycle (e.g. `lifecycle = "work"`) in your custom item types, or define entirely new ones.

#### Statuses

A status is a valid state in a lifecycle. Each status definition must specify:
- `terminal` — boolean indicating whether items at this status are considered "done" (terminal statuses do not appear in `sq inbox`)

Optional:
- `badge` — emoji displayed in sub-entity roll-up tables (used only for sub-entities)
- `role` — special marker for specific statuses (used only for ADRs; e.g. `role = "superseded"`)

```toml
[statuses.Triage]
terminal = false

[statuses.Mitigating]
terminal = false

[statuses.Resolved]
terminal = true
```

All statuses you define in a custom lifecycle must be declared in the `[statuses.*]` section.

#### Item types

An item type declaration specifies how a custom type appears in `sq` and which lifecycle it uses. Each type definition must specify:
- `prefix` — the uppercase letter prefix for the type's ID (e.g. `INC` for incidents)
- `folder` — the subdirectory under `squads/` where items of this type are stored
- `lifecycle` — the lifecycle name (built-in or custom) governing transitions

Optional:
- `parents` — list of allowed parent item types (e.g. `["epic"]`); empty list means unconstrained
- `aliases` — list of short command aliases (e.g. `["inc"]` allows `sq inc <n>` as shorthand for `sq incident <n>`)

```toml
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident"
```

### Additive-only rules

The override can **only add** new item types, statuses, and lifecycles. It **cannot redefine or remove** built-in ones. Attempting to shadow a built-in will raise an error at load time:

```
workflow override may not redefine built-in status 'Done'
(additive-only; you may add new statuses but not change built-ins)
```

If you remove a custom status from the override that is still in use by live items in the squad, `sq` will hard-stop with an error listing the affected items. Fix the items (e.g. `sq incident 5 status Mitigating`) or restore the status to the override.

Unknown TOML keys (typos) are rejected at load time, so the spec is fail-closed.

### Authoring and validation

After editing `.overrides/workflow.toml`, validate your changes with:

```bash
sq workflow lint
```

This command checks:
- **Syntax**: the TOML file is well-formed
- **Structure**: all lifecycles, statuses, and item types are correctly defined
- **References**: all status names used in transitions are declared; all lifecycle names are defined
- **Liveness**: any types or statuses still referenced by items in the squad are not removed

If valid, the output is:

```
workflow spec OK — no errors or warnings.
```

If there are errors, `sq workflow lint` prints each one with context and a fix hint:

```
                          workflow spec errors                          
┌────────────────────────────────────┬──────────────────────────────────┐
│ location                           │ error                            │
├────────────────────────────────────┼──────────────────────────────────┤
│ .overrides/workflow.toml:15        │ lifecycle 'incident' not found   │
│                                    │ (referenced in items.incident)   │
└────────────────────────────────────┴──────────────────────────────────┘
```

### Worked example: incident type

Here's a complete, runnable example of adding an `incident` item type with a three-state lifecycle:

```toml
# Define the incident lifecycle
[lifecycles.incident]
initial = "Triage"

[lifecycles.incident.transitions]
Triage = ["Mitigating", "Resolved"]
Mitigating = ["Resolved", "Triage"]
Resolved = ["Triage"]

# Define custom statuses for the lifecycle
[statuses.Triage]
terminal = false

[statuses.Mitigating]
terminal = false

[statuses.Resolved]
terminal = true

# Declare the incident type
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident"
```

With this override in place, you can now:

```bash
# Create an incident
sq create incident "Database connection timeout"

# List all incidents
sq list -t incident

# Transition through the lifecycle
sq incident 1 status Mitigating
sq incident 1 status Resolved

# Use the full ID in commands
sq incident 1 show
sq incident 1 comment -m "@qa please verify the fix"
```

The incident's ID will be `INC-000001`, stored in the `squads/incidents/` folder, and fully integrated with the team workflow — you can assign it, comment on it, and check its status just like any built-in item type.

### Checking the override state

To see how your override differs from the bundled default:

```bash
sq override diff workflow
```

This shows what you've added (delta-mine) compared to an empty starting point. If you upgrade squads, use:

```bash
sq override update workflow
```

to update the version stamp in the override file.

### Hard stops and error recovery

If a workflow spec becomes invalid (e.g. because you edited `.overrides/workflow.toml` directly and introduced a syntax error), any `sq` command will hard-stop with a pointer to `sq workflow lint`:

```
workflow spec is incompatible with the live index — run `sq workflow lint` to see details
```

Always run `sq workflow lint` to diagnose and fix the issue before proceeding.
