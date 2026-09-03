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
- The **product owner** also names **milestones** (`sq create milestone`) — the releases and cycles
  work is aimed at — and authors **contracts** (`sq create contract`), the living record of what the
  product does for a user. Neither sits in the epic → feature → task spine: work reaches a milestone
  or a contract by a ref, never by parentage.

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
| `contract` | `prd`, `c` | `sq c <n> show` |
| `milestone` | `mile`, `m` | `sq m <n> show` |
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
sq workflow ref-kinds          # every declared ref kind: its label, hint and semantic role
sq workflow views              # every declared derived view: its source, fields, grouping, ordering
sq workflow view <name> <id>   # resolve one declared view against one item
sq workflow lint               # validate the workflow override — collects all errors; exit 0 if OK
```

The **catalog** subcommands (`types`, `subentity-kinds`, `collections`, `statuses`, `roles`,
`lifecycles`, `ref-kinds`, `views`) each take `--json` and emit a bare JSON array — that is the surface to read instead
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
| `views` row | `source_name` | `ref-kinds` / `subentity-kinds` / `types` | per `source_kind` |

A `views` row's `source_name` keys into whichever catalog its own `source_kind` names: `"ref"`
keys into `sq workflow ref-kinds`, `"subentity"` into `sq workflow subentity-kinds`, and
`"subtree"` into `sq workflow types`. It is the one join above whose destination is decided by a
sibling field rather than fixed.

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
contract (PRD)   Draft ─────▶ Active ────▶ Superseded     (Active ─▶ Deprecated ─▶ Active)
milestone        Draft ─────▶ InProgress ─▶ Done          (Draft / InProgress ─▶ Cancelled ; Done ─▶ InProgress)
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
| contract (PRD) | `Draft` | Draft→{Active}; Active→{Superseded, Deprecated}; Deprecated→{Active} |
| milestone | `Draft` | Draft→{InProgress, Cancelled}; InProgress→{Done, Cancelled}; Done→{InProgress}; Cancelled→{Draft} |
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
no manual markdown editing, and no manual markdown reading either — the block on disk holds only the
prose, so opening the file shows you strictly less than `show` does. `body` **replaces** the block's prose, so it refuses once something has
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

## Derived views

A **derived view** is a declared, read-only projection over relationships an item already has: take
every item pointing here with a given ref kind, or this item's own sub-entities, or its descendants
of some type, keep a chosen set of fields, group and order them, and render the result. A view has
three parts and no fourth:

- **source** — the relation to project. One of three shapes: `ref` (every item carrying a forward
  ref of the named kind to this item, recovered by inverting stored edges), `subentity` (this item's
  own sub-entities of the named kind), or `subtree` (this item's descendants of the named type).
- **projection** — the `fields` to carry, an optional `group_by`, an optional `order_by`. It
  produces records and makes no presentation decision.
- **presentation** — a template over those records, resolved by the view's own name.

```bash
sq workflow views                       # every declared view: source, fields, grouping, ordering
sq workflow view <name> <id>            # resolve one view against one item, rendered
sq workflow view <name> <id> --json     # the projection instead: field metadata, grouping, records
```

**Every view is computed, every time.** Nothing is ever written into an item's file. There is no
sink to declare, no region to regenerate, no output to commit, and nothing to reconcile when two
branches touch the same item — the underlying frontmatter merges as ordinary data, and the next
read renders the merged result. A stored rendering would be a second answer to a question the
frontmatter already answers, and the two go out of step silently.

**`--json` gives the data, not the display.** It emits the projected records with the field metadata
and grouping key that travel alongside them, and skips presentation entirely. The shape is the same
for every view and every source, so a client can lay out a view it has never seen without
special-casing it. That is the supported way to build on a view; the CLI's own rendering is one
presentation over the records, never their source.

The bundled spec declares one view, `milestone_rollup` — see below. Declaring your own is a section
of the workflow override: [§ "Derived views"](#derived-views-declared-projections) has the field
reference.

---

## Milestones

A **milestone** is a named target a set of work is aimed at — a release, a cycle, a cutoff. It is a
records-type item: no parent, no children, no sub-entities, and its own small lifecycle
(`Draft → InProgress → Done`, plus `Cancelled`) that tracks whether the target is still being
pursued — never how much of its work is finished.

```bash
sq create milestone "1.0" --author product-owner
sq milestone <n> update --set target_date=2026-12-01
sq milestone <n> status InProgress
```

**Membership lives on the work item, not on the milestone.** A feature, task or bug joins a
milestone by carrying a forward `targets` ref to it:

```bash
sq task <n> ref add MILE-<n> --kind targets
```

The milestone file is not touched by that, and it holds no list of its members. There is no verb
that adds work to a milestone from the milestone's side, because there is nothing there to add it
to. Two things follow, and both are the point:

- **A milestone is cheap to change.** Re-aiming twenty items at a different release rewrites twenty
  work items and leaves the milestone byte-for-byte as it was, so it never becomes the file every
  branch touches.
- **The membership list is recovered, not stored.** It is the inversion of those forward edges, so
  it cannot disagree with them. `sq milestone <n> refs --in` lists the raw edges.

**The roll-up answers what is left.** `sq milestone <n> show` renders the bundled
`milestone_rollup` view under the milestone's body: its members split into delivered and
outstanding, each side counted. That split is read from each member's own **status role**, not from
a status name, so a milestone can hold items of several types whose lifecycles spell "finished"
differently and still group them correctly. Like every derived view it is computed on each request —
`--json` included — so it is current by construction and there is nothing to refresh.

```bash
sq milestone <n> show                            # the roll-up, rendered
sq workflow view milestone_rollup MILE-<n> --json  # the same members as records
```

squads has no estimation vocabulary, so a milestone reports items, not effort: counts of what is
delivered and what is outstanding. There is no burndown, no velocity and no sprint length here.

---

## Contracts

A **contract** is the living record of what the product does for a user, right now. It is the
functional twin of the ADR set: **a decision record is the technical contract, a contract is the
functional contract with the user.**

The distinction that makes it worth having a separate type:

- **A contract is living.** It is the accumulated current behaviour, rewritten in place as the
  product changes, written from the user's point of view. It has no "done".
- **Features and epics are historic.** Each is a point-in-time record — the change plus the
  reasoning behind it — that later work supersedes. To answer "what does this product do today" from
  features alone you have to replay all of them in order and apply every later override in your
  head. The contract is the result of that replay, kept written down.

Its lifecycle is `Draft → Active → Superseded` (plus `Deprecated`, which can be revived to
`Active`). There is no burn-down state, because a contract is not work.

**It is a collection, not a monolith.** Write one contract per capability or user-facing area, so a
change updates one slice and two teams working on different areas do not meet in the same file.
Where those boundaries fall is your editorial judgement, and **nothing enforces it**: too coarse and
contracts drift back into one document nobody owns, too fine and a single feature fans its links
across a dozen tiny items. Neither failure can be stated as a rule that would not also refuse
shapes that are perfectly reasonable, so squads does not try.

**A feature links the contract it shapes** with an `implements` ref — the same kind used elsewhere,
disambiguated by the target being a contract:

```bash
sq create contract "Search" --author product-owner
sq contract <n> status Active
sq feature <n> ref add PRD-<n> --kind implements   # from the feature
sq contract <n> refs --in                          # every feature that has shaped this contract
```

### The currency check

A living record that is not kept current lies, so `sq check` watches for the case it can see: a
feature that reaches a **delivered** status — one whose role is `done` — without linking any
contract. It reports a **warning**:

```
warn FEAT-<n>: settled with no implements ref to a contract — its functional contract slice may be stale
```

It is the delivered role specifically, not the broader "settled" property: a `Cancelled` feature
delivered nothing and is never asked about, and an `InReview` one has not landed yet.

**It warns and never blocks.** The transition goes through, and `sq check` still exits `0`
for a squad whose only findings are warnings. That is deliberate, not an oversight: plenty of
features touch no user-facing behaviour at all, and a hard gate would fire on every one of them. The
only way a team clears a gate like that is by adding a link that isn't true — which corrupts exactly
the edge the check reads. So the warning surfaces the question and leaves the answer with the person
who knows whether this feature really touches no contract.

**The check is inert until you author your first contract**, and this is worth understanding before
you conclude it is broken. While a squad holds no contract at all, the check evaluates nothing and
reports nothing, however many settled features it has — because the remedy it would name does not
exist yet, and a warning whose fix is unavailable is noise. The moment the first contract is
authored, the check becomes active for the whole corpus at once, features that settled long before
that contract existed included. Expect a batch of warnings on the day you start, name the slices
each of those features shaped, and the batch clears.

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

The override file is standard TOML. Its top level accepts eight sections — `[items.*]`,
`[statuses.*]`, `[lifecycles.*]`, `[collections.*]`, `[subentity_kinds.*]`, `[roles.*]`,
`[ref_kinds.*]` and `[views.*]` — plus the single `[selected]` table that drops built-ins. Anything
else at the top level is refused by name when the spec loads; `sq workflow lint` prints the accepted
set for the version you are running, which is the list to trust rather than this one.

The subsections below cover lifecycles, statuses, status roles, item types, collections, ref kinds
and derived views. Sub-entity kinds (`[subentity_kinds.*]`) are declarable but have no field
reference here; read one back with `sq workflow subentity-kinds --json` for its field shape.

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

The bundled records types are `decision` (ADR), `contract` (PRD), `milestone` and `guide`. When you
define a custom records type, squads treats it like a decision: it takes no parent, lives in its own
folder, and never appears in `sq inbox` (it's always available for reference, not active work).

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

#### Ref kinds

A ref kind is the label on a link between two items — the `--kind` in
`sq <type> <n> ref add <id> --kind <kind>`. The kinds are declared vocabulary like everything else
in this file, so a squad may add its own, relabel a bundled one, or drop one it doesn't use.

```toml
[ref_kinds.escalates]
label = "Escalates"
hint = "A escalates B to a wider audience"
```

The table key is the kind as it is spelled on disk. `label` is required; `hint` is the one-line
meaning, written about *A* (the item carrying the ref) and *B* (the item it points at). `role`
declares a semantic squads binds behaviour to, and `direction` (`"blocker"` or `"dependent"`)
accompanies `role = "dependency"`. **A kind that declares no `role` is navigational** — a real edge
that displays, links and traverses, but drives no engine behaviour — and that is what a kind you
declare gets unless you say otherwise.

The bundled set:

| Kind | Meaning | `role` |
|---|---|---|
| `related` | Generic cross-reference — what a bare `ref add <id>` writes when you pass no `--kind` | `default` |
| `blocks` | A is blocking B; B cannot proceed while A is open | `dependency` (`blocker`) |
| `depends-on` | A depends on B; A cannot proceed while B is open | `dependency` (`dependent`) |
| `implements` | A implements the requirement or spec described by B | — |
| `fixes` | A (the resolving work) fixes the problem tracked by B | — |
| `addresses` | A (the resolving work) addresses or follows up on B (feedback, a review) | — |
| `supersedes` | A (a newer record) supersedes B (an older one) | `supersession` |
| `duplicates` | A (a later filing) duplicates B (the original) | — |
| `scopes` | A (a skill) is scoped to role B; B's generated pointer preloads A | `preload` |
| `targets` | A targets B — a navigational membership edge with no engine binding; its meaning is whatever reads it | — |

The four `role` values are what the engine actually reads — the `dependency` pair feeds
`sq blocked`, `preload` drives which skills a role's generated pointer loads, `supersession` drives
`sq check`'s incoming-supersedes rule, and `default` is both the no-`--kind` fallback and the
on-disk encoding for it. Behaviour never keys off a kind's spelling, which is why renaming a bundled
kind keeps its behaviour. Read your own merged set back with `sq workflow ref-kinds`.

The full field reference — the floor a merged set must satisfy, the refusals, and a worked
adopter-declared kind — is in
[overrides.md § "Ref kinds"](overrides.md#ref-kinds-the-labelled-edges-between-items).

**A convention about `duplicates`, which nothing enforces.** When a later filing turns out to
duplicate an existing item, the usual handling is to close the later one rather than delete it — at
`Cancelled` under squads' bundled lifecycles, or whatever your own spec calls its equivalent
dropped state — and to leave the `duplicates` edge on that later filing, so the original stays
reachable from it. This is a working convention, not an engine binding: `duplicates` declares no
`role` and nothing in squads checks any of it. It is deliberately not written into the kind's
declared semantics, because doing so would hardcode a status name your own spec is free to rename or
drop.

#### Derived views: declared projections

`[views]` declares the derived views described in [§ "Derived views"](#derived-views) above. A view
is a section of this document like any other: it merges, it shadows field by field, and it drops
through `[selected]`.

```toml
[views.open_incidents]
source = { kind = "ref", name = "escalates" }
group_by = "status"
order_by = ["id"]
fields = [
  { code = "id",     label = "Incident" },
  { code = "status", label = "Status" },
  { code = "title",  label = "Title" },
]
```

Fields:

- `source` — required; an inline table of `kind` and `name`.
  - `kind = "ref"` — every item carrying a forward ref of kind `name` to the item the view is
    resolved against. `name` must be a declared entry of `[ref_kinds]`.
  - `kind = "subentity"` — the resolved item's own sub-entities of kind `name`. `name` must be a
    declared entry of `[subentity_kinds]`, and the item must be of a type that hosts that kind.
  - `kind = "subtree"` — the resolved item's descendants whose type is `name`. `name` must be a
    declared entry of `[items]`.
- `fields` — the projected columns, in order. Each is `{ code, label }`. `code` is either a base
  record attribute (below) or a badge field the source's own type or kind declares; `label` is the
  header a presentation may print.
- `group_by` — optional; the `code` of one declared `fields` entry. Records are grouped by that
  field's value. Omit it and the projection carries a single unkeyed group, so the shape a client
  reads is the same either way.
- `order_by` — optional; a list of `fields` codes to sort records within each group.

The table key is the view's name, and it is also where its presentation lives — there is no
`presentation` field, because the template path *is* the identity (below).

**Base record attributes.** These resolve for any source without the type declaring a field for
them, and which ones are available depends on the source kind — projecting one from a source that
cannot produce it is refused when the spec loads, not silently rendered blank:

| `code` | `ref` | `subentity` | `subtree` | What it is |
|---|---|---|---|---|
| `id` | ✓ | ✓ | ✓ | The record's id — a full item id, or a sub-entity's local id |
| `status` | ✓ | ✓ | ✓ | Its status, as declared |
| `status_role` | ✓ | ✓ | ✓ | The role that status resolves to — the axis to group on |
| `assignee` | ✓ | ✓ | ✓ | Its assignee slug, or `null` |
| `title` | ✓ | ✓ | ✓ | Its title |
| `type` | ✓ | — | ✓ | The item's own type; a sub-entity has none |
| `story` | — | ✓ | — | The parent story a sub-entity maps onto, where its kind maps one |
| `any declared badge field` | — | ✓ | ✓ | e.g. `priority`, `severity`, or one you declared |

**A `ref` source projects base attributes only.** Its records can be items of any type — that is
what makes it a membership edge — so there is no single type whose declared fields would apply to
all of them, and naming a badge field there is refused at load rather than rendered blank. A
`subentity` source resolves badge fields against the named kind's own `fields`, and a `subtree`
source against the named type's.

**Group on `status_role`, not on a status name.** A view's members can span several types whose
lifecycles spell "finished" differently — `Done`, `Verified`, `Accepted` — so grouping on the
literal status silently splits work that is equally finished. `status_role` is the declared axis
that answers the question, and it is what the bundled milestone roll-up groups on.

**Presentation: `templates/views/<name>.md.j2`.** A view's rendering is an ordinary bundled
template, resolved by the view's own name, and it is overridden the way every other template is —
drop a file at `.overrides/templates/views/<name>.md.j2` and it wins, per file, ahead of the bundled
tree. `sq override scaffold`, `sq override diff` and `sq override update` cover it with no
view-specific machinery:

```bash
sq override scaffold views/milestone_rollup.md.j2   # start from the bundled rendering
sq override diff views/milestone_rollup.md.j2       # your edits, and what an upgrade changed
sq override update views/milestone_rollup.md.j2     # re-stamp once you have reconciled
```

The template receives `fields`, `group_by` and `groups`; a group has `key`, `count` and `records`,
and a record's cells are addressed by field code — `record.values["id"].text` for the rendered text,
`record.values["id"].json_value` for the structured value. **A view you declare needs a template of
its own at that path** before it can be rendered; until you write one, resolve it with `--json`,
which does not render at all.

**Dropping a view.** `[selected].views` names the views that survive, like every other section. A
view attached to an item type is also attached from that type's side — the type's own `views` list —
so drop both together:

```toml
[items.milestone]
views = []          # detach it from the type that shows it

[selected]
views = []          # and drop the declaration itself
```

Dropping the **type** through `[selected].items` needs neither line: a bundled view that only that
type attached is taken with it automatically, so there is no second, unrelated-looking key to
remember.

**Referential checks.** A view naming a ref kind, sub-entity kind or item type the merged spec does
not declare is refused at load with the rest of the spec's cross-references, and so is a `group_by`
or `order_by` naming a code the view's own `fields` do not carry. `sq workflow lint` reports it with
everything else.

**Reading back what you declared:**

```bash
sq workflow views          # name, source kind, source name, fields, grouping
sq workflow views --json   # machine-readable
```

### What the override may and may not change

The override may add a new item type, status, lifecycle, collection, status role, ref kind or
derived view; shadow a built-in one, field by field; and drop a built-in by listing the survivors in
a top-level `[selected]` table. The full grammar — deep merge, arrays as leaves, splat-refs and `[selected]` —
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
- **A ref kind dropped or renamed while live refs spell it** — bounded, not a hard stop: `sq workflow
  lint` refuses, with the affected IDs listed, and so does adding a *new* ref of that kind. Every
  other command keeps running — `sq check` reports the stale kind as a warning per item, `sq
  graph`/`refs` traverse the edge and report no declared semantic, and `sq repair` and the ref-removal
  verb both still run. Restore the entry, or remove those refs with `sq <type> <n> ref rm`; run `sq
  repair` first if the edge is a legacy-mapped encoding you'd rather canonicalise onto the current
  default than remove. A kind no edge uses may be dropped or renamed freely.

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
