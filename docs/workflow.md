# squads workflow

The process squads coordinates has two layers: **who creates and links what** (the team workflow)
and **how each item moves through its states** (the status lifecycle). `sq workflow` prints a short
version of the first; this is the full reference. The rules are enforced — at `create`/`ref add`/
`status` time and by `sq check`.

---

## Team workflow

```
        product owner                         tech lead
            │                                    │
            ▼                                    ▼
   ┌──────────────────┐  parent   ┌───────────────────────────┐
   │ FEATURE          │◀──────────│ TASK                       │
   │  + user stories  │           │  parent = the feature      │
   │    USn, USm, …   │◀╌╌╌╌╌╌╌╌╌╌│  subtask STn (→ USn) …     │
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

- `task.parent` must be a **feature**; `feature.parent` must be an **epic** — each type declares
  which parent it accepts, so an override changes these along with the vocabulary.
  Bugs/reviews attach as refs, **not** as a task's parent.
- A subtask's `(→ USn)` must exist in the task's parent feature.
- `sq check` flags violations (bad parent type, dangling subtask→US, dangling refs).

### Commands at a glance

```bash
# product owner  (--author is required on every create, and must name a registered role)
sq create feature "User authentication" --author product-owner --parent EPIC-<n>
sq feature 2 add-story "As a user, I want to log in"

# tech lead
sq create task "Validate token" --author tech-lead --parent FEAT-<n>
sq task 3 add-subtask "Check expiry" --story USn
sq task 3 ref add BUG-<n> --kind fixes        # or REV-… --kind addresses

# everyone
sq task 3 status InProgress
sq task 3 comment --as reviewer -m "@qa please verify the redirect"
sq inbox qa

# humans (operators) are participants too
sq operator add "Alice Tester"                # → op-alice
sq task 3 update --assignee op-alice           # assign a manual step to a person
sq task 3 comment --as op-alice -m "approved"  # record the human's own words
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

## Inspecting the workflow spec

`sq workflow` and its subcommands print the team-workflow cheatsheet and inspect the active workflow
specification:

```bash
sq workflow                    # print the team-workflow cheatsheet (who writes what, how items link)
sq workflow show               # same (explicit version)
sq workflow types              # every declared item type in the active spec
sq workflow subentity-kinds    # every declared sub-entity kind: its fields, plural, local-id prefix
sq workflow collections        # every declared badge collection (priority, severity, or custom)
sq workflow statuses           # every declared status, with the role each resolves to
sq workflow roles              # every declared status role: settled / hidden / colour / live
sq workflow lifecycles         # every declared lifecycle: initial state, states, transitions
sq workflow lint               # validate the workflow override — collects all errors; exit 0 if OK
```

The **catalog** subcommands (`types`, `subentity-kinds`, `collections`, `statuses`, `roles`,
`lifecycles`) each take `--json` and emit a bare JSON array — that is the surface to read instead
of hardcoding a type or status name, and the shapes are covered by the [stability
contract](stability.md). Every row carries every key, `null` for absent rather than omitted, so a
client can index a key without testing for its presence.

### Joining the catalogs

A catalog row never inlines a copy of another row; it names one, using the same key name the target
catalog uses as its identity. Follow the name to the other catalog:

| From | Key | Joins to | Identity key |
|---|---|---|---|
| `types` row | `fields[].collection` | `collections` | `collection` |
| `subentity-kinds` row | `fields[].collection` | `collections` | `collection` |
| `types` row | `subentity_kind` | `subentity-kinds` | `subentity_kind` |
| `statuses` row | `role` | `roles` | `role` |
| `types` row | `lifecycle` | `lifecycles` | `lifecycle` |
| `subentity-kinds` row | `lifecycle` | `lifecycles` | `lifecycle` |

**Resolving a sub-entity's field label.** A sub-entity in `sq <type> <n> show --json` carries no
kind of its own — you are holding the parent item's `type`, so the kind comes from the type
catalog. The chain is `item.type` → the type row's `subentity_kind` → the kind row's `fields[]`,
matched on the code the sub-entity's own `badges` map already gives you:

```
item.type "review" → type row subentity_kind "finding" → kind row fields[] {severity: "Severity"}
                   → the sub-entity's badges {"severity": "high"} renders as   Severity: high
```

That is how you get the *declared* label rather than a hardcoded one, which matters as soon as a
project relabels the field or declares its own. The same row also carries `local_prefix` (the `US`
/ `ST` / `F` in a local id), `plural` (the CLI list verb, and the container-marker name in the
file), `container_heading` (the `## …` heading sq writes — read it rather than title-casing
`plural`, which gives "Stories" where sq writes "User Stories"), `completion` (the status a "mark
done" action should target, instead of assuming `Done`), and `maps_parent_story` (whether this kind
carries the extra story column in its roll-up table).

**Resolving a type's or a kind's state machine.** The type row and the kind row each carry the name
of the state machine they bind — equal values mean two entries bind the same machine (`epic`,
`feature` and `task` all read `work`; `story` and `subtask` both read `subentity`). Join that name
into `sq workflow lifecycles --json`'s own `lifecycle` identity key to resolve it:

```
type row lifecycle "work" → lifecycles row {initial: "Draft", states: [...], transitions: [...]}
```

`initial` is the starting status. `states` is every status the machine declares — its `initial`
plus every source and target in its transition map — listed in breadth-first discovery order from
`initial`: a documented, deterministic order that stays the same across runs, but **not** the
prettier happy-path-then-side-states order `sq workflow show`'s own diagrams use for a human
reader. Declared and reachable are the same set, because a lifecycle that declares a status it
cannot reach from `initial` is refused when the spec loads. `transitions` is every allowed move,
one `{from, to}` object per edge, sourced in that same `states` order. A client builds a status
quick-pick or a "what can this become" prompt directly from this row — no filtering of its own, and
without scraping a diagram or driving a deliberately invalid transition to read the refusal text.

`--raw` (plain markdown instead of Rich rendering) applies to the cheatsheet — `sq workflow` and
`sq workflow show`. `sq workflow lint` reports through its exit code: 0 when the spec is clean, 1
when any error is present.

---

## Status lifecycles

Every item type has its own state machine. `sq <type> <n> status <Status>` only allows a transition
the machine permits; `--force` overrides. New items start at the machine's initial state.

```
work items (epic · feature · task)
    Draft ──▶ Ready ──▶ InProgress ──▶ InReview ──▶ Done ┄┄▶ (reopen) InProgress
                          ▲                └──────────┘ rework
    Blocked  ⇄  Ready / InProgress / InReview          Cancelled ◀── any open state

bug              Open ──▶ InProgress ──▶ Fixed ──▶ Verified ┄┄▶ (reopen) InProgress
                 (InProgress ⇄ Blocked ; Open / InProgress / Blocked ─▶ WontFix, Cancelled)

ADR (decision)   Proposed ──▶ Accepted ──▶ Superseded     (Proposed ─▶ Rejected ; Accepted ─▶ Deprecated)
review           Requested ─▶ InReview ─▶ Approved        (InReview ⇄ ChangesRequested ; any ─▶ Rejected)
guide            Draft ──▶ Published ──▶ Deprecated        (⇄ both directions)

roster entries (role · skill · operator)
    Active ⇄ Archived

  ─▶ allowed transition   ⇄ both ways   ┄▶ escape hatch
```

**A bug does not use the work-item machine.** It starts at `Open`, not `Draft`, and `Ready`,
`InReview` and `Done` are not in its vocabulary at all — `sq bug <n> status Done` is refused as
out-of-vocabulary, not as a bad transition.

| Type | Initial | Transitions |
|------|---------|-------------|
| epic / feature / task | `Draft` | Draft→{Ready, InProgress, Cancelled}; Ready→{InProgress, Blocked, Cancelled}; InProgress→{InReview, Blocked, Done, Cancelled}; InReview→{InProgress, Done, Blocked, Cancelled}; Blocked→{Ready, InProgress, Cancelled}; Done→{InProgress}; Cancelled→{Draft} |
| bug | `Open` | Open→{InProgress, WontFix, Cancelled}; InProgress→{Fixed, Blocked, WontFix, Cancelled}; Fixed→{Verified, InProgress}; Verified→{InProgress}; Blocked→{InProgress, WontFix, Cancelled}; WontFix→{Open}; Cancelled→{Open} |
| decision (ADR) | `Proposed` | Proposed→{Accepted, Rejected}; Accepted→{Superseded, Deprecated}; Rejected→{Proposed} |
| review | `Requested` | Requested→{InReview, Rejected}; InReview→{ChangesRequested, Approved, Rejected}; ChangesRequested→{InReview, Rejected} |
| guide | `Draft` | Draft→{Published}; Published→{Deprecated, Draft}; Deprecated→{Published} |
| role / skill / operator | `Active` | Active→{Archived}; Archived→{Active} |

**Settled states.** A status is *settled* — a resting state — because the **role** it resolves to
says so, never because of its name and never because it is a dead end. Most settled states here
*do* have an outgoing edge: that is how reopening works (`Done→InProgress`, `Verified→InProgress`,
`Archived→Active`). Read `settled` off `sq workflow roles`, and never hardcode a status name to
decide whether work is finished.

With the bundled vocabulary the settled statuses are `Accepted`, `Approved`, `Archived`,
`Cancelled`, `Deprecated`, `Done`, `Published`, `Rejected`, `Superseded`, `Verified` and `WontFix`.
`sq inbox` surfaces only **open** (non-settled) items. Hiding in `sq list` / `sq tree` is a
*separate* axis (`hidden` on the same role) — bundled `Accepted` and `Published` are settled without
being hidden.

**Roster entries carry extra rules.** A role, skill or operator lifecycle must declare:

- at least one **live** status — the statuses whose entries are presented to an agent host — so an
  entry can always be presented;
- a settled status that is not live and is reachable from a live one, so an entry can always *stop*
  being presented;
- and, when the lifecycle's `initial` is not itself live, exactly one live status — so the entry
  squads scaffolds for itself has an unambiguous target. This is what lets you declare a
  parked-then-activated roster lifecycle: name a non-live `initial` plus a single live status, and
  your own entries start parked until you move them. When `initial` is itself live there is nothing
  to disambiguate and any number of further live statuses is fine.

Retiring an entry (moving it to a status that is not live) withdraws it from your generated agent
config, and can be **refused** where the config could not survive the withdrawal; `--force` does not
override that refusal. See
[roles.md § "Retiring a roster entry"](roles.md#retiring-a-roster-entry).

> Status is stored in the `.md` frontmatter *and* mirrored in the index. The dated discussion
> entries (`sq <type> <n> comment`) are what record the *history* of a transition — see
> [adoption.md](adoption.md) for replaying that history with `--at`.

## Sub-entities: subtasks, user stories, findings

The sub-entities (subtasks/stories/findings) are tracked by `sq` too — each has its own status, and
the parent shows an **sq-managed summary table** that rolls them up (regenerated on every change).
Their state (status/assignee/severity/story) lives in the parent item's **frontmatter** (so the index
sees them); the block in the body holds only the prose and a derived badge header. The block's **body
is sq-managed too** — set it with `sq <type> <n> <kind> <k> body -m
"…"` (or `--file body.md` / `--file -`) and read the whole block with `sq <type> <n> <kind> <k> show`;
no manual markdown editing. `body` **replaces** the block's prose, so it refuses once something has
been written there rather than discarding it — add to it with `--append`, or pass `--force` to
replace it on purpose.

| Sub-entity | Lives on | Add / transition | Lifecycle |
|------------|----------|------------------|-----------|
| **subtask** | task | `sq task <n> add-subtask "…" [--story USn]` · `sq task <n> subtask <k> update --status <S>` | `Todo → InProgress → Done` (+ Blocked, Cancelled) |
| **user story** | feature | `sq feature <n> add-story "…"` · `sq feature <n> story <k> update --status <S>` | `Todo → InProgress → Done` (+ Blocked, Cancelled) |
| **finding** | review | `sq review <n> add-finding "…" --severity high` · `sq review <n> finding <k> update --status <S>` | `Open → Fixed → Verified` (+ WontFix) |

`sq <type> <n> <kind> <k> update` is the one metadata entry point for a sub-entity — `--title`,
`--status` (+`--force`), `--assignee`/`--clear-assignee`, plus a subtask's `--story`/`--no-story` and
a finding's `--severity`. Findings carry a **severity** value from the bundled `severity` collection
(by default: 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info), set at `add` time and changeable
with `update --severity`. The severity collection is fully customizable via `.overrides/workflow.toml`;
you can relabel badges, change emoji, add/remove values, or define a custom collection for your
findings. Transitions are validated by the sub-entity machines; `--force` overrides.

---

## Operation reflog (`sq reflog`)

Every mutating `sq` command appends one JSON line to `squads/.reflog.jsonl` — an append-only
**operation log**. The reflog is **advisory**: the index
(`.squads.json`) and the markdown files remain the source of truth. `sq repair`, `sq check`, and
every other read path never consult it.

### Line shape

Each line is a JSON object with these fields:

| Field | Type | Meaning |
|-------|------|---------|
| `v` | `string` | Schema version the line was written under — tracks the index schema, forward-compatible by addition |
| `ts` | `string` | ISO-8601 UTC timestamp of the operation |
| `actor` | `string` | Role slug (`python-dev`, `system`, `op-alice`, …) performing the write |
| `op` | `string` | Operation name (see table below) |
| `target` | `string` | Primary item ID affected (empty `""` for squad-level ops) |
| `delta` | `object` | Free-form before/after detail — shape varies by `op` |
| `session_id` | `string?` | Optional. Omitted from the file when absent |
| `parent_session_id` | `string?` | Optional. Omitted from the file when absent |

The two session fields are **best-effort, untrusted, and for observability only**: squads reads
them from its own invocation environment and records them as given. It never mints or verifies one,
so a forged or copied id is indistinguishable from a real one — never make a trust decision on
them. Only the immediate parent is stored; walk `parent_session_id` edges to reconstruct a chain
(`sq reflog --tree` does exactly that). Lines written without them read back with both absent.

**Op names.** The vocabulary is closed — these sixteen and no others, and the same sixteen
`sq reflog --op` accepts. Both this table and that option's help come from one declared list, so
they cannot drift apart. An `op` you meet that isn't here came from a squads version other than the
one this guide ships with; your reflog is not corrupt.

| `op` | Triggered by |
|------|-------------|
| `create` | `sq create …` |
| `status` | `sq <type> <n> status …` |
| `update` | `sq <type> <n> update …` — including a re-parent via `--parent` |
| `body` | `sq <type> <n> body …` |
| `comment` | `sq <type> <n> comment …`, on an item or a sub-entity |
| `subentity` | `add-story` / `add-subtask` / `add-finding`, and a sub-entity's `update` / `body` / `remove`. The specific change is in `delta.op` |
| `ref` | `sq <type> <n> ref add` / `ref rm`, and refs severed by a forced `remove` |
| `link` | An item's parent set or cleared through the service's own link path. **No CLI verb reaches this today** — from the CLI, a parent change arrives as `update` |
| `retype` | `sq <type> <n> retype …` |
| `default_role` | `sq role <addr> set-default` |
| `remove` | `sq <type> <n> remove …` (the `delta` carries the gone-item snapshot) |
| `repair` | `sq repair`, with or without `--renumber` |
| `renumber` | `sq renumber` — the distinct verb that shifts a range of sequence numbers |
| `migrate` | `sq migrate up`, and `sq migrate repad` (which sets `delta.op` to `repad`) |
| `rename-type` | `sq migrate rename-type` — **one line per item moved**, not one line for the run |
| `rename-status` | `sq migrate rename-status` — likewise, one line per item moved |

`repair`, `renumber` and `migrate` are squad-level: they carry an empty `target`. Every other op
names the item it touched.

### Reading the reflog

```bash
sq reflog                          # last 50 entries (default)
sq reflog --tail 0                 # all entries
sq reflog --item TASK-<n>          # filter to one item
sq reflog --actor python-dev       # filter by actor slug
sq reflog --op status              # filter by operation
sq reflog --since 2026-06-01       # since a date (ISO 8601)
sq reflog --tree                   # group by declared session lineage
sq reflog --json                   # machine-readable JSON array
```

Filters are AND-ed. `--json` emits a JSON array of the fields above, with one difference from the
file: `session_id` and `parent_session_id` are always **present**, `null` when absent, rather than
omitted — so a client can key on them unconditionally.

`--tree` renders the declared spawn lineage. Missing intermediate sessions degrade to several roots
rather than an error, and the same untrusted-input caveat applies: it shows what was declared, not
what can be proven.

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

By default, squads uses a built-in set of item types, statuses, and state machines. If your project needs custom vocabulary — for example, an `incident` type for on-call workflows — you write a project-level **workflow override** in TOML. The override composes over the built-in spec: it can **add** new types, statuses and lifecycles, **shadow** a built-in one field by field, and **drop** one you don't want. This page is the field reference for each kind of declaration; how your file combines with the bundled one is in [overrides.md § "The override grammar"](overrides.md#the-override-grammar-shadow-append-and-drop).

### Creating an override

To scaffold a starter override file:

```bash
sq override scaffold workflow
```

This creates `.overrides/workflow.toml` in your squad directory (next to `.squads.json`) with a commented-out worked example. Edit this file to add your custom types, statuses, and state machines.

### Override format

The override file is standard TOML with four sections: `[items.*]`, `[statuses.*]`, `[lifecycles.*]`,
and `[collections.*]`.

#### Lifecycles

A lifecycle defines the allowed state transitions for an item type or sub-entity kind. Each lifecycle must specify:
- `initial` — the starting status when a new item is created
- `transitions` — a map of allowed transitions (source status → list of target statuses)

Every status the map mentions must be reachable from `initial` — a lifecycle carrying a state
nothing reaches is refused, naming that state — and at least one reachable status must be a settled
one, or items on the lifecycle could never close.

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
- `role` — the name of a status role (from the role catalog) that governs this status's
  terminal/hidden/color attributes. Squads derives terminal-ness, visibility, and color from
  the role. See **Status roles** (below) for the full catalog.

Optional:
- `badge` — emoji displayed in sub-entity roll-up tables (used only for sub-entities)

```toml
[statuses.Triage]
role = "attention"

[statuses.Mitigating]
role = "active"

[statuses.Resolved]
role = "done"
```

All statuses you define in a custom lifecycle must be declared in the `[statuses.*]` section.

#### Status roles: terminal/hidden/color governance

Every status references a **role**, which is a catalog entry governing four attributes:

- **`settled`** — boolean; `true` means the status is terminal (work is done; hidden from `sq inbox`
  by default).
- **`hidden`** — boolean; `true` means the status is hidden from default list views (show only with
  `--all` flag).
- **`color`** — semantic color intent for display (positive/danger/warning/muted/neutral/info).
  This is mapped to concrete, theme-aware colors across clients.
- **`live`** — boolean, defaults `false`; the materialisation axis for roster (role/skill/
  operator) entries. It is deliberately narrower than "not settled" — `attention`, `blocked`,
  and `pending` are all non-settled without being live, because "not at rest" and "on offer"
  are different questions. A roster entry whose status resolves to a live role is on offer to be
  spawned, loaded, cited, and assigned — it is what gets written into an agent host's generated
  config. The default is deliberately fail-safe-withheld: wrongly withholding an entry is
  recoverable, wrongly treating one as live writes an agent into a host's config.

Squads ships with a bundled role catalog. In your override, you can reference built-in roles or
define new ones. Every status must declare a role; if omitted, it defaults to `pending`.

**Bundled roles:**

| Role | `settled` | `hidden` | `color` | `live` | Typical use |
|------|-----------|----------|---------|-----------|------------|
| `pending` | `false` | `false` | `neutral` | `false` | Draft, Proposed, Requested — awaiting action |
| `active` | `false` | `false` | `positive` | `true` | InProgress, InReview, ChangesRequested — actively being worked |
| `attention` | `false` | `false` | `danger` | `false` | Open issues, failing tests, urgent needs |
| `blocked` | `false` | `false` | `danger` | `false` | Blocked — stopped by a dependency |
| `in_force` | `true` | `false` | `info` | `false` | Accepted, Published — in effect, terminal but shown |
| `done` | `true` | `true` | `positive` | `false` | Done, Verified, Approved — complete and hidden by default |
| `retired` | `true` | `true` | `muted` | `false` | Cancelled, Deprecated, Rejected — terminal and hidden |
| `superseded` | `true` | `true` | `muted` | `false` | Superseded — replaced by a newer item, terminal and hidden |

**Defining a custom role:**

```toml
[roles.in_queue]
settled = false
hidden = false
color = "warning"

[statuses.Queued]
role = "in_queue"
```

**Viewing the role catalog:**

```bash
sq workflow roles           # list all available roles in your spec
sq workflow roles --json    # machine-readable output
```

#### Item types

An item type declaration specifies how a custom type appears in `sq` and which lifecycle it uses. Each type definition must specify:
- `prefix` — the uppercase letter prefix for the type's ID (e.g. `INC` for incidents)
- `folder` — the subdirectory under `squads/` where items of this type are stored
- `lifecycle` — the lifecycle name (built-in or custom) governing transitions

Optional:
- `category` — the item's category: `"work"` (default, for task-like items that flow through
  a lifecycle) or `"records"` (for durable reference items like ADRs or guides). See
  **Records-category item types** (below) for details.
- `parents` — list of allowed parent item types (e.g. `["epic"]`); empty list means unconstrained
- `aliases` — list of short command aliases (e.g. `["inc"]` allows `sq inc <n>` as shorthand for `sq incident <n>`)

```toml
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident"
```

#### Records-category item types

Squads recognizes two item categories:

- **`"work"`** (default) — ephemeral items flowing towards completion: epics, features, tasks,
  bugs, reviews. Work items can be parents/children in a hierarchy, appear in `sq inbox`, and
  are tracked as effort.
- **`"records"`** — durable reference documents: decisions/ADRs, guides, contracts, standards,
  postmortems. Records have no parents, no hierarchy, and exist for reference, not active tracking.

The bundled `decision` and `guide` types are both records. When you define a custom records type,
squads treats it like a decision: it takes no parent, lives in its own folder, and never appears
in `sq inbox` (it's always available for reference, not active work).

**When to use records category:**

Use `category = "records"` for items that are:
- **Durable** — meant to last and be maintained, not disposable work
- **Free-standing** — no parent or child relationships
- **Reference material** — RFC, postmortem, runbook, SLA, policy, etc.

**Example: custom postmortem type**

```toml
[items.postmortem]
prefix = "PM"
folder = "postmortems"
category = "records"
lifecycle = "guide"              # reuse the guide lifecycle or define your own
```

This creates items like `PM-1`, `PM-2`, etc., stored in `squads/postmortems/`. Records never
have parents, so the `parents` field is ignored for records-category types. Use `sq list -t postmortem`
to view all postmortems (they're shown at all times, unlike work items filtered by `sq inbox`).

#### Collections

A collection is a reusable set of badge options (like priority or severity) that can be applied to
items or sub-entities. Collections are ordered or unordered; ordered collections support filtering
and sorting by rank.

```toml
[collections.impact]
label = "Impact"
ordered = true
default = "medium"
badges = [
  { code = "high",   label = "High impact",   emoji = "🔴" },
  { code = "medium", label = "Medium impact", emoji = "🟡" },
  { code = "low",    label = "Low impact",    emoji = "🔵" },
]
```

`label` is required; `ordered` defaults to `false`, and an ordered collection ranks by declaration
order, **strongest first**. `default` is the code used when no value is set.

The bundled default collections are `priority` (urgent, high, medium, low) and `severity`
(critical, high, medium, low, info). A collection is a library — a type carries it by declaring a
`fields` entry bound to it:

```toml
[items.incident]
fields = [{ code = "impact", label = "Impact", collection = "impact" }]
```

Values are set with `sq <type> <n> update --set impact=high` and filtered with `sq list --badge
impact=high` / `--min-badge` / `--sort`. The bundled priority axis additionally has `--priority`
and `--min-priority` sugar.

Removing a badge code from a collection is refused while live items still carry that code; the
refusal lists the affected IDs.

### What the override may and may not change

The override may add a new item type, status, lifecycle, collection or status role; shadow a
built-in one, field by field; and drop a built-in by listing the survivors in a top-level
`[selected]` table. The full grammar — deep merge, arrays as leaves, splat-refs and `[selected]` —
is in [overrides.md § "The override grammar"](overrides.md#the-override-grammar-shadow-append-and-drop).

The refusals you are most likely to meet — the grammar-level ones (a malformed splat-ref, a
token-shaped key, an exceeded nesting bound) are catalogued in
[overrides.md](overrides.md#the-override-grammar-shadow-append-and-drop):

- **The roster type keys `role`, `skill` and `operator` must exist**, and cannot be renamed, dropped
  or added to; `category = "roster"` cannot move into or out of those three. Everything else about
  them, `lifecycle` included, is an ordinary field merge.
- **A type's `prefix` or `folder` cannot change while that type has live items** — those two fields
  are how squads finds the type's files on disk. The change is refused with the affected IDs listed;
  revert the field, or make the change while the type has no items.
- **A drop that strands live items** — a type or status the squad's own items still carry. `sq` hard-stops
  with the affected IDs listed. Restore the key, or move the items first.

Unrecognised top-level keys — a mistyped section name being the usual case — are rejected by name at
load time, so the spec is fail-closed rather than silently doing nothing.

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
┌────────────────────────────────────┬──────────────────────────────────┬──────────────────────────┐
│ location                           │ error                            │ fix hint                 │
├────────────────────────────────────┼──────────────────────────────────┼──────────────────────────┤
│ .overrides/workflow.toml           │ Invalid workflow spec: lifecy-   │ Fix the TOML at          │
│                                    │ cle 'incident' not found         │ .overrides/workflow.toml │
│                                    │ (referenced in items.incident)   │ and re-run `sq workflow  │
│                                    │                                  │ lint`.                   │
└────────────────────────────────────┴──────────────────────────────────┴──────────────────────────┘
```

### Worked example: incident type

Here's a complete, runnable example of adding an `incident` item type with a three-state lifecycle
and custom statuses with roles:

```toml
# Define custom roles for the incident lifecycle
[roles.triage_needed]
settled = false
hidden = false
color = "danger"

[roles.in_mitigation]
settled = false
hidden = false
color = "warning"

# Define the incident lifecycle
[lifecycles.incident]
initial = "Triage"

[lifecycles.incident.transitions]
Triage = ["Mitigating", "Resolved"]
Mitigating = ["Resolved", "Triage"]
Resolved = ["Triage"]

# Define custom statuses for the lifecycle with roles
[statuses.Triage]
role = "triage_needed"

[statuses.Mitigating]
role = "in_mitigation"

[statuses.Resolved]
role = "done"              # reuse the bundled "done" role for terminal status

# Declare the incident type (work category by default)
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident"
```

Once the override is defined and validated with `sq workflow lint`, the custom type gets the full
`sq <type> <n> …` surface, exactly like a bundled type:

```bash
sq create incident "Auth outage" --author manager   # → INC-1
sq list -t incident                                 # list all incidents
sq incident 1 show                                  # addressed show/update/status/body/comment/…
```

### Checking the override state

To see how your override differs from the bundled default:

```bash
sq override diff workflow
```

Δ-mine is your override against the current bundled spec, so it shows everything you have added
*and* everything you have shadowed. If you upgrade squads, use:

```bash
sq override update workflow
```

to update the version stamp in the override file.

### Hard stops and error recovery

If a workflow spec becomes invalid (e.g. because you edited `.overrides/workflow.toml` directly and introduced a syntax error), any `sq` command will hard-stop with a pointer to `sq workflow lint`. Always run `sq workflow lint` to diagnose and fix the issue before proceeding.

---

## Renaming existing types and statuses

The workflow override changes your **vocabulary**; it does not rewrite items already filed under the
old one. A type's `prefix` and `folder` in particular are refused outright while that type has live
items, because they are how squads finds those items on disk. To move an existing corpus onto
different vocabulary, use the on-demand **data migration commands**:

- **`sq migrate rename-type OLD_TYPE NEW_TYPE`** — bulk-rename every item of type `OLD_TYPE` to
  `NEW_TYPE`. Both types must already exist in the active spec (as non-roster types). The command
  rewrites every affected item's ID, folder, and all references (parent, refs, inline mentions) to
  use the new prefix and location. Logged to the reflog; run `sq check` after.

  ```bash
  sq migrate rename-type task job         # every TASK-<n> becomes JOB-<n> (if both exist in the spec)
  ```

- **`sq migrate rename-status TYPE OLD_STATUS NEW_STATUS`** — bulk-move every item of `TYPE` at
  `OLD_STATUS` to `NEW_STATUS`. This is a relabel, not a workflow transition — items simply change
  their status value without moving through the state machine. `NEW_STATUS` must already be a member
  of `TYPE`'s lifecycle. Scoped per-type. Logged to the reflog; run `sq check` after.

  ```bash
  sq migrate rename-status task Blocked Waiting   # every task at Blocked → Waiting
  ```

These are **audited data rewrites** — atomic per type, designed to preserve referential integrity,
and audited item by item: each writes **one reflog line per item moved**, not one line for the run,
so `sq reflog --op rename-type` reconstructs exactly which items a past rename touched. Always
verify with `sq check` after.

**Use case:** You released your squad with the built-in `task` type but later realize you want to call
them `job` instead. Declare a `job` type in your workflow override, then run `sq migrate rename-type
task job` to move all existing tasks across. Both types must exist in the spec while the rename runs;
once `task` has no items left, you can drop it from a `[selected]` list if you want it gone.
