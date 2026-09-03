# Project-level overrides

Your squad may want to customize how squads renders items, roles, or backend artifacts — a custom
task template to match your team's style, different names for roles, your own item types, or your
own wording for the guidance each role reads before it picks up a piece of work. **Overrides** are
how you do that without forking the entire squads package.

Overrides live under `squads/.overrides/` (`squads/` is your squad folder — its name is
`squads` by default, configurable via `.squads.toml`), a directory that mirrors the bundled
template structure. You own and maintain them; squads detects when an upgrade changes the bundled
originals and warns you to reconcile. The [`sq override`](#the-sq-override-command-group) command
group handles the full authoring + upgrade workflow.

---

## TL;DR: Get a custom task template

```bash
# Copy the bundled task template into your squad as a starting point
sq override scaffold items/task.md.j2

# Edit it
$EDITOR squads/.overrides/templates/items/task.md.j2

# Check for drift warnings
sq check

# Later, if squads upgrades and the bundled task template changed:
# See what both your edit AND the upgrade changed
sq override diff items/task.md.j2

# Merge manually (the diffs show what you customised and what the upgrade added)
$EDITOR squads/.overrides/templates/items/task.md.j2

# Tell squads you're done reconciling
sq override update items/task.md.j2

# Verify the warning is gone
sq check
```

---

## Override layout

All overrides live under a single umbrella directory, **`<squad-dir>/.overrides/`**:

```
<squad-dir>/.overrides/
  templates/
    items/
      epic.md.j2
      feature.md.j2
      task.md.j2
      bug.md.j2
      review.md.j2
      guide.md.j2
      decision.md.j2
    subentities/
      story.md.j2
      subtask.md.j2
      finding.md.j2
      block.md.j2
      summary.md.j2
    agents/
      role.md.j2
    claude/
      pointer_agent.md.j2
      pointer_skill.md.j2
      claude_section.md.j2
  workflow.toml
  playbook.toml
  roles/
    architect.toml
    tech-lead.toml
    tech-writer.toml
    manager.toml
    python-dev.toml
    custom-role.toml
```

**Key points:**

- **`templates/`** mirrors the bundled `_rendering/templates/` tree exactly. An override is named by
  its **template path** (e.g., `items/task.md.j2`, `agents/role.md.j2`). You don't override
  everything — drop a single file and only that template changes; the rest still use the bundle.
- **`roles/`** holds TOML files for role data: one file per role slug (e.g., `architect.toml`). You
  can override bundled roles (like changing the architect's name or model) or define entirely new
  custom roles.
- **`workflow.toml`** is your squad's vocabulary delta — item types, statuses, lifecycles, and badge
  collections (see below). It can add to the bundled vocabulary, shadow a bundled entry field by
  field, and drop one you don't want.
- **`playbook.toml`** is your squad's delta on the **team playbook**: which roles interact with each
  item type, and the guidance each of them reads before touching one (see
  [Playbook overrides](#playbook-overrides-role-guidance-per-item-type)). It is what your generated
  `sq-<type>` skills are compiled from.
- The directory is discovered automatically by the same walk-up that finds `.squads.toml`. It
  travels with your squad folder, so it's portable across projects.

---

## Precedence rule

Override lookup is **per-file, project → bundled default**:

1. If `.overrides/templates/<template-name>` exists, squads uses it.
2. Otherwise, squads uses the bundled template from the package.

There is **no whole-squad override mode** — presence of a file is the override, and you can mix
and match:

```
.overrides/
  templates/
    items/task.md.j2          # ← custom task template
    items/bug.md.j2           # ← custom bug template
    (no feature.md.j2)        # ← use bundled feature template
    agents/role.md.j2         # ← custom role body shape
```

**Template overrides are whole-file:**
If you override `items/task.md.j2`, the entire file is replaced. squads does not attempt line-by-line
merging of template content. (The required `<!-- sq:* -->` marker regions must still be present —
see [Staleness and drift](#staleness-and-drift) below.)

**Role overrides merge by field:**
A `roles/architect.toml` override only replaces the fields you set. Fields you omit inherit from
the bundled role definition:

```toml
# .overrides/roles/architect.toml
full_name = "Chief Design Officer"
model = "opus"
# title, mission, responsibilities, etc. inherit from the bundled architect
```

**A developer's override merges onto the developer you already have:**
Developers aren't in the bundled catalog — they're created on demand by `sq dev add` — so a
`roles/<tech>-dev.toml` merges over the definition that developer already carries rather than over
a bundled entry. Everything that reads a role resolves it that way — `sq dev add`, `sq sync`,
`sq role <slug> show`, `sq check`.

```toml
# .overrides/roles/python-dev.toml
title = "Senior Python developer"
# full_name, mission, responsibilities, model, etc. inherit from the live python-dev role
```

Three rules follow from that base:

- **Fields you omit keep the role's current values.** A file that sets only `title` changes only
  the title.
- **A field you declare wins — including `full_name`, which renames the developer.** That is the
  same thing declaring `full_name` does for a bundled role.
- **A name you never wrote is never invented.** Omit `full_name` and the developer keeps the name
  they already have, whether it came from `--name` or from the pool.

A file for a tech you haven't added yet is accepted rather than refused, so you can write the
override first and run `sq dev add --tech <tech>` afterwards.

**The workflow override merges by field too, and can also drop:**
`workflow.toml` composes over the bundled vocabulary the same way — write the fields you want
changed, inherit the rest, and use a `[selected]` list to remove a built-in entirely. See
[The override grammar](#the-override-grammar-shadow-append-and-drop).

A brand-new role slug (one not in the bundle) defines a wholly custom, non-dev role — e.g. a
`security-analyst` or `compliance-officer` — from the TOML. Start it with:

```bash
sq override scaffold --new compliance-officer
```

This writes `squads/.overrides/roles/compliance-officer.toml` with the essential fields stubbed and the
advanced fields present as commented-out lines to uncomment and fill in:

```toml
# .overrides/roles/compliance-officer.toml
full_name = "Compliance Officer"
title = "The keeper of standards"
description = "Ensures all code meets compliance requirements."
mission = "Keep the team on the right side of policy."
responsibilities = ["Review all PRs for policy violations", "Maintain the compliance handbook"]
model = "opus"
# can_spawn = true   # opt this role into spawning/orchestrating subagents (default: false)
```

Then `sq role activate compliance-officer` creates the role the same way it does for a bundled
slug. See [roles.md](roles.md) for the activation flow.

---

## Workflow overrides: item types, statuses, badge collections, ref kinds and views

By default, squads uses a bundled set of **item types** (`sq workflow types` lists the set your
build ships), **status lifecycles** (state machines for each type), **badge collections** (priority
and severity, the reusable axes that label findings, tasks, etc.), **ref kinds** (the labelled
edges — `blocks`, `fixes`, `supersedes` and the rest — that link one item to another) and
**derived views** (declared read-only projections over those edges).
**`.overrides/workflow.toml`** is where you change that vocabulary. You can do
three things with it:

- **Add** — new item types, statuses, lifecycles, badge collections, status roles, ref kinds, views.
- **Shadow** — redefine a bundled entry, field by field. The fields you write replace their bundled
  counterparts; the ones you leave out are inherited.
- **Shrink** — drop a bundled entry you don't want, by listing the ones you keep.

See [The override grammar](#the-override-grammar-shadow-append-and-drop) below for how your file
composes against the bundled one. The rest of this section is the field reference for each type of
declaration.

### Creating a workflow override

To scaffold a starter override file:

```bash
sq override scaffold workflow
```

This creates `squads/.overrides/workflow.toml` with a commented-out worked example.
Edit this file to add your custom types, statuses, lifecycles, and collections.

### Format and sections

The override file is standard TOML. Its top level is a **closed set of section names** —
`[items.*]`, `[statuses.*]`, `[lifecycles.*]`, `[collections.*]`, `[subentity_kinds.*]`,
`[roles.*]`, `[ref_kinds.*]` and `[views.*]`, plus the single `[selected]` table — and anything else
at the top level is refused by name at load time:

```
item: unknown top-level key 'item' — use one of the accepted top-level keys in v<version>:
['collections', 'items', 'lifecycles', 'ref_kinds', 'roles', 'selected', 'statuses',
'subentity_kinds', 'views']
```

The refusal names the version it is speaking for, because the accepted set grows as squads gains
sections. The list your own copy prints is the authoritative one: `sq workflow lint` reports it
without needing a working spec, which is the point of that command still running while a bad
override stands.

That refusal matters more than it looks: `[item.task]` written for `[items.task]` is the easiest
mistake to make in this file, and a section name squads didn't recognise would otherwise mean your
whole override does nothing at all.

The complete field reference is in [workflow.md](workflow.md) § "Project workflow overrides".

#### Items: custom work types

Define a new item type (e.g., an `incident` type for on-call workflows):

```toml
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident"      # reference a built-in or custom lifecycle
```

Required fields:
- `prefix` — uppercase letter(s) for the type's ID prefix (e.g., `INC` for `INC-<n>`)
- `folder` — subdirectory under `squads/` where items of this type are stored
- `lifecycle` — the lifecycle name (built-in or custom) governing the type's state machine

Optional:
- `category` — the item's category: `"work"` (default) or `"records"`. See **Custom records-category
  item types** (below) for details.
- `parents` — list of allowed parent item types; empty or omitted means no hierarchy constraint
- `aliases` — list of short command aliases (e.g., `["inc"]` allows `sq inc <n>` as shorthand)

#### Custom records-category item types

Squads distinguishes two item categories:

- **Work items** (`category = "work"`, the default) — ephemeral; flow through a lifecycle towards completion
  (epic, feature, task, bug, review). Work items can be children in a hierarchy and map to effort.
- **Records** (`category = "records"`) — durable reference documents; authored once, maintained indefinitely
  (decisions/ADRs, guides, contracts, standards, postmortems, etc.). Records have no parents and no hierarchy.

The bundled records types are `decision` (ADR), `contract` (PRD), `milestone` and `guide`. When you
define a custom records-category type, squads treats it like a decision or guide: it takes no parent,
nests in its own folder, and never appears in `sq inbox` by default (it's for reference, not work
tracking).

**When to use records category:**

Use records for any item that is:
- A **durable reference** meant to last and be maintained (not a disposable work item)
- **Free-standing** (no parent or children)
- **Not part of a hierarchy** (e.g., a postmortem, runbook, RFC, ADR, etc.)

**Declaring a custom records type:**

```toml
[items.postmortem]
prefix = "PM"
folder = "postmortems"
category = "records"          # mark it as a records-type, not work
lifecycle = "guide"           # reuse the guide lifecycle or define your own
```

This creates a `postmortem` type with:
- IDs like `PM-1`, `PM-2`, etc.
- Storage in `squads/postmortems/`
- The same lifecycle as guides (Draft → Published → Deprecated)
- No parent constraints (records never have parents)

After defining it, you can:

```bash
sq create postmortem "API outage" --author architect   # → PM-1, starts Draft
sq postmortem 1 body --file postmortem-incident.md
sq postmortem 1 status Published
sq list -t postmortem    # list all postmortems (shown at all times)
```

**Records never appear in `sq inbox` by default;** they're indexed for reference, not active work tracking.

#### Statuses: custom state labels

Define new statuses (e.g., states for your custom incident lifecycle):

```toml
[statuses.Triage]
role = "attention"

[statuses.Mitigating]
role = "active"

[statuses.Resolved]
role = "done"
```

Required fields:
- `role` — the name of a status role (from the role catalog) that governs this status's
  terminal/hidden/color attributes. See **Status roles** (below) for the full role catalog and
  how to define custom roles.

Optional:
- `badge` — emoji or short symbol displayed in sub-entity roll-up tables (used only for sub-entities)

Terminal-ness, default visibility and colour are all derived from the referenced role rather than
declared per status. If you omit `role`, a status defaults to the `pending` role (non-terminal,
shown by default, neutral color).

#### Lifecycles: custom state machines

Define a new lifecycle (the state transitions for a custom item type):

```toml
[lifecycles.incident]
initial = "Triage"

[lifecycles.incident.transitions]
Triage = ["Mitigating", "Resolved"]
Mitigating = ["Resolved", "Triage"]
Resolved = ["Triage"]
```

Required fields:
- `initial` — the starting status when a new item of this type is created
- `transitions` — a map of `SourceStatus = [TargetStatus1, TargetStatus2, …]` showing which
  transitions are allowed

#### Collections: custom badge axes

Define a custom badge collection (a reusable axis like priority or severity):

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

Fields:
- `label` — required; the human-readable name of the axis
- `ordered` — optional, defaults `false`; `true` if the badges have a meaningful ranking. **Declare
  an ordered collection strongest first** — rank follows declaration order, the way the bundled
  `priority` collection runs urgent → low
- `default` — optional; the badge code used when no value is set
- `badges` — the badge definitions, each with `code`, `label` and `emoji`

A collection is a *library*; a type carries it by declaring a **field** bound to it. Add one to a
built-in type without disturbing its existing fields:

```toml
[items.task]
fields = ["$(*self)", { code = "impact", label = "Impact", collection = "impact" }]
```

Then, on any item of that type:

```bash
sq task <n> update --set impact=high    # set it  (--unset impact clears it)
sq list --badge impact=high             # exact filter on any declared badge field
sq list --min-badge impact=medium       # threshold filter, ordered collections only
sq list --sort impact                   # sort by an ordered field's rank
```

The bundled `priority` axis has dedicated sugar for the same operations — `--priority` /
`--min-priority` — and every other badge field goes through `--set` / `--badge` / `--min-badge`.

#### Status roles: terminal/hidden/color attributes

A **role** is a catalog entry that defines how a status displays and behaves. When you declare a
status with `role = "rolename"`, squads uses that role's attributes to determine:

- **`settled`** — whether the status is terminal (done). Terminal statuses are treated as
  "complete" and hidden from `sq inbox` by default.
- **`hidden`** — whether the status is hidden from default list views (shown only with `--all` flag).
- **`color`** — a semantic color intent for display across the CLI and clients (positive/danger/warning/muted/neutral/info).
- **`live`** — whether an entry resting at this status is *on offer*. It decides whether a roster
  entry (role, skill, operator) is written into your agent host's generated config. It defaults to
  `false`, and is deliberately narrower than "not settled": a status can be paused or waiting —
  non-settled — without being live.

Squads ships with eight bundled roles covering common patterns. You can reference them in your
statuses, or define custom roles in your override:

```toml
[roles.my_custom_role]
settled = false          # not terminal
hidden = false           # shown by default
color = "warning"        # semantic intent for rendering

[statuses.MyStatus]
role = "my_custom_role"
```

**Bundled role reference:**

| Role | `settled` | `hidden` | `color` | `live` | Use case |
|------|-----------|----------|---------|--------|----------|
| `pending` | `false` | `false` | `neutral` | `false` | Draft, proposed, requested (awaiting work) |
| `active` | `false` | `false` | `positive` | `true` | In progress, under review, being addressed |
| `attention` | `false` | `false` | `danger` | `false` | Blocked, failing, or needs urgent attention |
| `blocked` | `false` | `false` | `danger` | `false` | Explicitly blocked and waiting |
| `in_force` | `true` | `false` | `info` | `false` | Accepted, published, or in effect (terminal, shown) |
| `done` | `true` | `true` | `positive` | `false` | Complete or verified (terminal, hidden by default) |
| `retired` | `true` | `true` | `muted` | `false` | Superseded, deprecated, or cancelled (terminal, hidden) |
| `superseded` | `true` | `true` | `muted` | `false` | Replaced by a newer decision (terminal, hidden) |

**Color semantics:**

The `color` field carries semantic intent, not a concrete hex value. Squads maps each color
across clients (CLI, VS Code extension, etc.) to concrete, theme-aware colors. The palette is
closed — you may only use these names: `positive`, `danger`, `warning`, `muted`, `neutral`, `info`.

**Defining a custom role:**

```toml
[roles.awaiting_merge]
settled = false
hidden = false
color = "warning"

[statuses.WaitingForMerge]
role = "awaiting_merge"
```

Then use `role = "awaiting_merge"` in any status to reference it. A status that doesn't specify a
`role` defaults to the `pending` role, so it's always safe to omit the field for simple cases.

**Viewing the role catalog:**

```bash
sq workflow roles           # list all available roles
sq workflow roles --json    # machine-readable format
```

See [workflow.md](workflow.md) § "Project workflow overrides" for a worked example.

#### Ref kinds: the labelled edges between items

A **ref** links one item to another, and its **kind** is the label on that link:
`sq <type> <n> ref add <id> --kind fixes` records that this item fixes the one it points at. The
kind is stored inline with the edge in the item's own file, which makes it durable on-disk data —
the same class of value as a type's prefix or a status name, and protected the same way.

`[ref_kinds]` is where that vocabulary is declared. Declaring one of your own is a three-line table:

```toml
[ref_kinds.escalates]
label = "Escalates"
hint = "A escalates B to a wider audience"
```

That is the whole declaration, and it is usable immediately:

```bash
sq <type> <n> ref add <id> --kind escalates   # write an edge of your kind
sq workflow ref-kinds                         # your kind, listed beside the bundled ones
```

A kind your merged spec doesn't declare is still refused by name — the accepted set is now yours,
not a fixed list:

```
error: unknown ref kind 'bogus'. Valid kinds: addresses, blocks, depends-on, duplicates, fixes, implements, related, scopes, supersedes, targets
```

Fields:
- `label` — required; the human-readable name shown wherever the kind is presented.
- `hint` — optional; the one-line meaning, written as a sentence about *A* (the item carrying the
  ref) and *B* (the item it points at), which is how the bundled hints read.
- `role` — optional; the **semantic** squads binds behaviour to (below). Omit it and the kind is
  navigational.
- `direction` — `"blocker"` or `"dependent"`. Only meaningful alongside `role = "dependency"`, and
  required there.

The key of the table *is* the kind, spelled exactly as it appears on disk inside an `ID:kind` edge.
There is no separate name field.

**`role` is what the engine reads — never the kind's name.** That is what makes a bundled kind
renameable: behaviour follows the declared semantic, so a renamed dependency kind keeps driving
`sq blocked` and a renamed supersession kind keeps driving `sq check`.

| `role` | What squads binds to it |
|---|---|
| `default` | The kind a bare `ref add <id>` resolves to when you pass no `--kind`. It is also the on-disk encoding: an edge of the default kind is written with no kind at all, so renaming the kind that carries `default` relabels those edges rather than re-pointing them. |
| `dependency` (with `direction`) | The `sq blocked` graph. `"blocker"` reads *A blocks B*; `"dependent"` reads *A depends on B*. |
| `preload` | The skill → role edge whose inversion decides which skills a role's generated pointer preloads. |
| `supersession` | `sq check`'s rule that a record resting at a status whose role is `superseded` should have an incoming edge of this kind; it warns when one doesn't. |
| *(omitted)* | Display and navigation only. |

**A kind that declares no `role` is navigational — and that is what a kind you declare gets unless
you say otherwise.** That is the ordinary case, not a lesser one: a navigational kind is a
first-class edge that shows up in `sq <type> <n> show`, carries its own label and hint, and appears
in `sq graph --json` with `edge_kind` set to your spelling and `edge_semantic` `null`. It simply
drives no engine behaviour of its own. Give a kind a `role` only when you mean to move one of the
four behaviours above onto it. Most of the bundled kinds are navigational — `implements`, `fixes`,
`addresses`, `duplicates` and `targets` — and `targets` is the plainest case of all: squads binds
nothing to it whatsoever. It ships as a general membership edge — *this item belongs to that one* —
and its meaning is whatever reads it: your own conventions, your own tooling, or a person following
the link.

**The floor the merged spec must satisfy.** These are checked on the composed result, so a bundled
kind you drop counts against them just as your own additions do:

- **Exactly one kind carries `role = "default"`.** It is mandatory: a bare edge on disk carries no
  kind, so it is undecodable without one.
- **Exactly one kind carries `role = "preload"`.** Zero leaves every skill unreachable from the role
  that scopes it; two make the inversion ambiguous.
- **At most one kind per `dependency` direction.** Zero is legal in either direction — a squad that
  declares no dependency kind simply gets an empty `sq blocked`. A kind declaring
  `role = "dependency"` with no `direction` is refused outright.
- **Any number of `supersession` kinds, zero included.**
- **Every key must be a bare TOML key** (`[A-Za-z0-9_-]+`). In particular it may not contain `:`,
  which is the separator an `ID:kind` edge is split on, and the bare-key shape is what keeps the
  entry addressable by a splat-ref.

Each of these is reported as an ordinary spec error, so `sq workflow lint` shows it with the rest:

```
the workflow spec must declare exactly one ref kind with role = 'preload' (a skill's forward edge to the role that preloads it); found 0: []
```

**Dropping or renaming a kind.** A kind is dropped by leaving it out of `selected.ref_kinds`, and
renamed by dropping the old key and declaring a new one. Neither locks the squad: every command
still loads and every edge is still readable. `sq workflow lint` refuses while live items still
carry the old spelling, with the offending IDs listed, and so does adding a *new* ref of that kind —
`sq check` reports the same items as a per-item warning instead, and `sq graph`/`refs` traverse the
edge and report no declared semantic:

```
ref kind 'escalates' is no longer declared in the workflow spec, but 1 live item(s) still carry a ref of that kind: ['INC-4'] — restore the entry in the override, or remove those refs with `sq <type> <n> ref rm <target>` (run `sq repair` first if the edge is a legacy-mapped encoding you'd rather canonicalise onto the current default than remove)
```

Restore the entry, or remove the affected refs — `sq <type> <n> ref rm` runs regardless of this
finding, so the removal is performable immediately. A kind **no edge uses** may be dropped or
renamed freely — which is the case you are actually in when you choose your vocabulary at adoption
time, before anything has been linked.

Two things that are *not* refusals but will surprise you:

- **Bare edges are unaffected by a rename of the default kind.** They store no spelling, so there is
  nothing on disk to strand — the relabelling is the whole effect.
- **A type's ref rules name kinds too.** A type may declare `ref_rules` — a per-type note attached
  to one kind, which squads folds into the hints it prints for items of that type. Dropping a kind
  a rule still names is refused at load, because such a rule could never apply. Shadow or drop the
  rule in the same override:

  ```
  items.task ref_rule[1]: kind 'addresses' is not one of the declared ref kinds ['blocks', 'depends-on', 'escalates', 'fixes', 'related', 'scopes', 'supersedes'] — every ref surface would reject it, so a rule for it can never apply
  ```

**Reading back what you declared:**

```bash
sq workflow ref-kinds           # kind, label, hint, role, direction
sq workflow ref-kinds --json    # machine-readable format
```

See [workflow.md](workflow.md) § "Ref kinds" for the bundled set and what each one is for.

---

#### Derived views: declared projections

A **derived view** is a read-only projection over relationships an item already has — every item
pointing here with a given ref kind, this item's own sub-entities, or its descendants of some type —
carried into a chosen set of fields, optionally grouped and ordered, and rendered by a template.
Views are declared in `[views]`, and nothing about them is a special case: they merge, shadow and
drop exactly like item types and statuses do.

Every view is **computed on every request**. No view is ever written into an item's file, so
declaring, changing or dropping one rewrites nothing on disk and leaves nothing behind.

**Declaring one of your own:**

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

`source.kind` is `"ref"`, `"subentity"` or `"subtree"`, and `source.name` must be a declared ref
kind, sub-entity kind or item type respectively — a name your merged spec does not declare is
refused at load, with the rest of the spec's cross-references. The complete field reference is in
[workflow.md § "Derived views"](workflow.md#derived-views-declared-projections).

Read it back, and resolve it against an item:

```bash
sq workflow views                             # your view, listed beside the bundled ones
sq workflow view open_incidents <id>          # resolved and rendered
sq workflow view open_incidents <id> --json   # the projection: fields, grouping, records
```

**Shadowing a bundled view.** Write only the keys you want changed; everything you leave out is
inherited and keeps tracking the bundled declaration. To reorder the bundled milestone roll-up
without restating its six fields or its grouping:

```toml
[views.milestone_rollup]
order_by = ["status", "id"]
```

Changing a bundled view's `group_by` is a bigger move than it looks: the bundled template renders
the groups it was written against, so regrouping a view means re-templating it too (below).

`fields` is a plain array and therefore a leaf — writing it replaces the bundled list wholesale
rather than merging into it. A splat-ref extends it instead of restating it, the same way it does
for a type's `parents` or `ref_rules`: `fields = ["$(*self)", { code = "…", label = "…" }]` keeps
everything the bundled view projects and appends your own column.

**Overriding a view's presentation.** A view's rendering is a bundled template at
`templates/views/<name>.md.j2`, resolved by the view's own name — there is no `presentation` key,
because the template path *is* the identity. That makes it an ordinary template override with no
view-specific machinery:

```bash
sq override scaffold views/milestone_rollup.md.j2   # a stamped copy of the bundled rendering
# edit squads/.overrides/templates/views/milestone_rollup.md.j2
sq override diff views/milestone_rollup.md.j2       # Δ-mine and Δ-upgrade, like any template
sq override list                                    # your override, with its base version and drift state
```

The template receives `fields`, `group_by` and `groups`; a group carries `key`, `count` and
`records`, and a record's cells are addressed by field code:

```jinja
{% for group in groups %}
{% for r in group.records %}
- **{{ r.values["id"].text }}** {{ r.values["status"].text }} — {{ r.values["title"].text }}
{% endfor %}
{% endfor %}
```

**A view you declare needs a template of your own at that path.** There is no generic fallback
rendering: until `.overrides/templates/views/<name>.md.j2` exists, resolve your view with `--json`,
which skips presentation entirely.

**Dropping a view.** `[selected].views` names the views that survive. A view a type attaches is
named twice — once in `[views]`, once in that type's own `views` list — so drop both:

```toml
[items.milestone]
views = []          # detach it from the type that shows it

[selected]
views = []          # and drop the declaration
```

Dropping the **type** through `[selected].items` needs neither line. A bundled view that only that
type attached goes with it, so there is no second key to remember; a view no type ever attached is
never touched by a type drop.

---

## The override grammar: shadow, append, and drop

Your `workflow.toml` is a **delta**, not a replacement. squads reads the bundled spec, composes your
file over it, and validates the result. Five rules govern how the two combine.

### 1. Deep merge — declare only what changes

Tables recurse key by key. Write one field of a bundled entry and only that field moves; everything
else is inherited from the bundle, and keeps tracking it across upgrades.

```toml
# .overrides/workflow.toml
[items.task]
aliases = ["t", "tk", "ticket"]

[items.task.labels]
singular = "Ticket"
plural = "Tickets"
singular_lower = "ticket"
plural_lower = "tickets"
```

Tasks now read as "Ticket" everywhere squads writes the type's name for a human or an agent — the
generated `sq-task` skill, `sq workflow types --json` — and `ticket` joins `t` and `tk` as a way to
address one, so every verb that works under `sq task <n>` also works under the alias. Their prefix,
folder, lifecycle, allowed parents, sub-entity kind, ref rules and priority axis are untouched: you
did not restate them, so a later release that improves any of them still reaches you.

(The type's **key** is still `task`. `labels` changes how the type is named in prose, and `aliases`
adds ways to address it; neither renames the key you write in `[items.task]`, in an item's
frontmatter, or in `sq list -t`. To move a corpus onto a genuinely different type, see
[workflow.md](workflow.md) § "Renaming existing types and statuses".)

This is what "shadowing" means: a hand-written value replaces its bundled counterpart. It works the
same at any depth — `[lifecycles.work.transitions]` merges per source status, `[collections.priority]`
merges per field.

> **Prefix and folder are settled once a type has items.** These two fields are how squads finds a
> type's files on disk, so changing either while items of that type exist would strand the whole
> corpus. squads refuses the change and lists the affected IDs. The two ways forward are to revert
> the field, or to make the change while that type has no items — **no command realigns an existing
> corpus**. Choose your prefixes and folders for a type before you start filing items under it.

### 2. Plain arrays are leaves — replaced whole

An array in your override replaces the bundled array outright. No element is quietly unioned in:

```toml
[items.task]
parents = ["epic"]        # tasks now hang off epics INSTEAD of features
```

The alternative — merging list elements — would produce a list nobody wrote and nobody can read back
out of the file. If you want to *extend* a bundled list rather than replace it, use a splat-ref.

### 3. Splat-refs — append to a bundled list without restating it

A **splat-ref** splices a value from the bundled spec into your override, so you can add to a bundled
list without copying it (and thereby freezing it against future improvements).

| Form | Meaning |
|------|---------|
| `$(path)` | the bundled value at *path*, spliced in as **one** element |
| `$(*path)` | a bundled **list** at *path*, its elements spread into the surrounding list |
| `$(self)` / `$(*self)` | the same, for **the key you are currently writing** |

`["$(*self)", <new>]` is therefore how you say *append*:

```toml
[items.task]
# keep every bundled parent type, and also allow an epic
parents = ["$(*self)", "epic"]

# keep every bundled ref rule, and add one of your own — note the inline-array form
ref_rules = ["$(*self)", { kind = "targets", hint = "link the thing this task targets" }]
```

Things worth knowing before you write one:

- **A path is dot-joined TOML bare keys** — ASCII letters, digits, underscores and hyphens. Keys are
  addressed by the names TOML writes unquoted, so a hyphenated key (`user-story`) or a digit-leading
  one needs nothing special. A dotted path addresses a bundled key from anywhere in the document
  (`$(*items.task.ref_rules)`); `$(*self)` addresses the key currently being written, at any list
  depth — a list position has no name of its own to contribute, so nesting does not change what
  `self` means. Paths resolve against the bundled document, so they only ever name bundled keys.
- **A token must be the entire string value.** `"$(*self)"` is a token; `"see $(items.task.prefix)"`
  is literal text. There is no interpolation.
- **A splatted array of tables must use TOML's inline-array form** — `ref_rules = ["$(*self)", { … }]`.
  The `[[items.task.ref_rules]]` header form has no slot to put a token in.
- **Resolution is against the bundled spec only**, never against another part of your override. That
  is what makes the merge order-independent and cycle-free — and it also means a splat only ever
  *adds*. To remove something, replace the array outright, or use `[selected]`.
- **A splat on a brand-new key dangles**, and is refused. `["$(*self)", x]` under a type you just
  invented has no bundled list to append to; that is a mistake, not an empty append.

### 4. `$(` at the *start* of a value — and nowhere else

This is the one place the grammar can surprise you, because `$(…)` is also POSIX command
substitution and you may well want to write a shell command line into a hint or a description.

**A string is read as a token only when it begins with `$(`.** A string that merely *contains* `$(`
later on is ordinary data, passed through byte for byte, needing no escape:

```toml
hint = "run git commit -m \"$(cat msg)\" before you push"   # fine, verbatim
hint = "echo $(date) to timestamp the run"                  # fine, verbatim
```

A string that **begins** with `$(` is in token territory and must be a valid token or it is refused:

```toml
hint = "$(which python) -m pytest"    # REFUSED — malformed splat-ref path
```

Write `$$(` to escape a value that must literally start with `$(`:

```toml
hint = "$$(which python) -m pytest"   # loads as: $(which python) -m pytest
```

That is the only position where an escape is ever needed. Two corollaries: a value **cannot** begin
with a literal `$$(`, because a leading `$$(` always unescapes to `$(`; and the same rule applies to
**keys** as well as values — a key that begins with an unescaped `$(` is refused outright, since
there is no such thing as splicing into a key:

```
items.$(items.task): splat-ref token '$(items.task)' used as a key — keys are never a splat target
  → escape it with '$$(' for a literal key, or move the token to a value
```

### 5. `[selected]` — dropping a built-in

`[selected]` is one top-level table with a key per section, and each key lists the entries that
**survive**, not the ones you are removing:

```toml
[selected]
items = ["epic", "feature", "task", "bug", "decision", "review", "role", "skill", "operator"]
```

That squad has no `guide` type: it is absent from the list, so it is dropped. The accepted section
keys are `items`, `statuses`, `lifecycles`, `collections`, `subentity_kinds`, `roles` and
`ref_kinds` — the same set the top level accepts; anything else under `[selected]` is refused by
name.

Two things follow from `[selected]` being the surviving set of the *merged* spec:

- **List your own additions too.** If you both add `[items.handbook]` and write `selected.items`,
  `handbook` must appear in that list or your own new type is dropped again.
- **Naming something that doesn't exist is not an error.** The list is a filter, not an assertion.

### What an override still cannot change

Almost everything is ordinary vocabulary. The exceptions are small and structural:

- **The three roster type keys — `role`, `skill`, `operator` — must exist.** They cannot be dropped
  (including via `[selected]`), renamed, or added to.
- **`category = "roster"` cannot move.** Those three types keep it; no other type may claim it.

Everything else about a roster type — its `lifecycle` above all, plus `prefix`, `folder`, `labels`
and `order` — is an ordinary field merge, validated like any other type's. In particular **no status
name is reserved**: a project may name its lifecycle states whatever it likes, in any language. What
a roster lifecycle must *do* is declare at least one status that is live, and a settled status that
is not live and is reachable from a live one — so an entry can always be presented to your agent
host, and can always stop being presented.

### When an override is wrong

A bad workflow override is a **hard stop**: `sq` refuses to run against it rather than half-applying
it. The failure is always at load, never partway through a command. These are the ways to get there:

| What went wrong | What you see |
|---|---|
| Unrecognised top-level key — usually a mistyped section name | `unknown top-level key 'item'`, with the accepted set |
| Malformed splat token | `malformed splat-ref path '…' — not a valid dot-joined chain of TOML bare keys` |
| Splat path with no bundled counterpart | `dangling splat path 'self' has no counterpart in the bundled base` |
| `$(*path)` used outside a list | `spread token '…' used outside a list — nothing to spread into` |
| A token in key position | `splat-ref token '…' used as a key — keys are never a splat target` |
| A shadowed lifecycle the engine cannot drive | e.g. `lifecycle 'agent': state 'Active' unreachable from initial 'Draft'` |
| A drop that strands live items | `item TASK-<n> has type 'task' which is not declared in the workflow spec` |
| A prefix or folder change against a live corpus | `type 'task' prefix changed to 'JOB' … but 1 live item(s) are still filed under the old prefix` |
| A badge code removed from a collection live items still carry | `… live item(s) still carry it: ['TASK-<n>'] — add 'urgent' back to the collection, revert the override, or update the affected item(s)` |
| A roster type key dropped or re-categorised | `workflow override may not drop roster type 'operator'` |
| A declared behaviour whose category checks nothing | `item 'decision': declares a 'supersedes' ref rule, but category 'work' turns on no validator for it …` — same for a type hosting a sub-entity kind, or a kind declaring `maps_parent_story`, under a category that validates neither |

That last one is worth stating as a rule, because it is the one you can reach without a typo: **a
type may not declare a behaviour its category then leaves unchecked.** Moving `decision` to
`category = "work"` keeps its `supersedes` rule but stops anything verifying it, so a superseded
record with no incoming edge would pass silently — the check does not fail, it stops existing. The
message names all three ways out: drop the declaration, leave the type in a category that checks it,
or name the validator you want in the type's own `validators` list:

```toml
[items.decision]
category = "work"
validators = ["supersedes_incoming"]   # keep the check the category no longer turns on
```

The same list is also how you turn on a check nothing bundled selects. `ref_rule_target_present` is
the one that ships that way: squads types the `implements` edge from a feature to a contract but
never requires it, and a squad that wants the obligation opts in here — see
[workflow.md](workflow.md#keeping-a-contract-current) § "Keeping a contract current".

`sq workflow lint` is the instrument. It reports **every** violation at once with a location and a
fix hint, where a plain `sq` command stops at the first:

```bash
sq workflow lint
```

When a violation traces back to one of your own `[selected]` lines, the message says so rather than
leaving you to work it out:

```
unknown item type 'guide': 'guide' was dropped from a [selected] list
(selected.items) in .overrides/workflow.toml, not left undeclared — add it back
to selected.items to restore it
```

**Reading the file is no longer the same as knowing your vocabulary.** Once an override can shadow,
splat and drop, what types and statuses you actually have is a function of the bundled set *and*
your file. Ask squads rather than reading the TOML:

```bash
sq workflow types        # the item types this squad actually has
sq workflow statuses     # and their statuses
sq workflow roles        # the status-role catalog
sq workflow lint         # and whether the whole thing is valid
```

### What a drop or a rename actually changes

A **type you add** appears everywhere a bundled type does: `sq create <type>`, `sq <type> <n> …` and
its declared aliases, its own folder, its own ID prefix, and — after `sq sync` — its own generated
`sq-<type>` skill.

A **type you drop** stops being usable immediately. It disappears from the top-level command
listing, from `sq create`, from `sq list -t` and from `sq workflow types`, and every way of reaching
it is refused — naming your own `[selected]` line as the reason:

```
$ sq create guide "…"
error: unknown item type 'guide': 'guide' was dropped from a [selected] list
(selected.items) in .overrides/workflow.toml, not left undeclared — add it back
to selected.items to restore it
```

Four practical notes:

- **A drop is refused while live items still carry the type or status**, listing the offending IDs.
  Restore the key to `[selected]`, or move those items first — `sq migrate rename-type` and
  `sq migrate rename-status` are the audited ways to move a corpus onto different vocabulary (see
  [workflow.md](workflow.md) § "Renaming existing types and statuses"). Once the type has no items
  left, dropping it succeeds.
- **A ref kind is on the same footing, with one fewer remedy.** A kind the merged spec drops or
  renames while live items still carry it is refused the same way, naming the offending IDs. Its two
  remedies are to restore the entry, or to remove those refs first: no command rewrites the ref
  kinds an existing corpus carries, so there is no `sq migrate` counterpart here. A kind no edge
  uses may be dropped or renamed freely, and that is the case you are in when you pick your
  vocabulary at adoption time. Bare edges — the ones written with no kind at all — are never
  stranded by a rename of the kind carrying `role = "default"`; they store no spelling to strand.
  See **Ref kinds** above for the full field reference.
- **Dropping a type does not delete what was already generated for it.** Its folder under the squad
  directory, and the `sq-<type>` skill generated for it before the drop, stay on disk; `sq sync`
  adds and updates, it does not sweep. Delete them by hand if you want them gone.
- **The command group itself still answers if you ask for it by name.** A dropped type is gone from
  the top-level listing, but typing its help explicitly — `sq guide --help`, say — still prints that
  group's usage, because the group is part of the built-in command table. Nothing under it works:
  every verb is refused with the message above. Treat the top-level listing, or `sq workflow types`,
  as the answer to "which types do I have" — not the fact that a group's `--help` renders.

---

## Playbook overrides: role guidance per item type

`.overrides/playbook.toml` customises the **team playbook** — the matrix of which roles interact
with each item type, and what each of them is told to check, do and hand off. It is the source the
generated `sq-<type>` skills are compiled from, so editing it changes the text an agent actually
reads before it picks up a bug, a review or a task.

```bash
# Start the playbook override from a stamped, commented worked example
sq override scaffold playbook

# Edit it
$EDITOR squads/.overrides/playbook.toml

# Regenerate the sq-<type> skills from it, then verify
sq sync
sq check
```

### Format

One entry per item type, keyed by type name. A type's **prose fields** — `overview`, `lifecycle`,
`commands` — merge one field at a time, so you write only the field you want to change and the rest
of that entry is inherited from the bundle:

```toml
# .overrides/playbook.toml
# squads:override-base:<version>

[types.bug]
overview = "A defect against shipped behaviour. Reproduce it before you file it."
# lifecycle and commands are inherited unchanged
```

`roles` is a **list**, so it follows the leaf rule from
[the override grammar](#2-plain-arrays-are-leaves--replaced-whole): writing it replaces the type's
whole set of role guides. Use a splat-ref to add one without restating the others:

```toml
[types.task]
roles = [
  "$(*self)",
  { slug = "security-analyst", enter = ["Read the threat model"], do = ["Record any exposure found"] },
]
```

That reads as "every guide the bundle ships for `task`, plus mine", and the bundled guides go on
tracking the release.

**The append idiom has to be the inline-array form.** TOML's `[[types.task.roles]]` header syntax
has nowhere to put the `"$(*self)"` token, so a spread must be written as an inline array as above.

### Rules

- **Coverage follows your vocabulary; it is never declared here.** Which types the playbook covers is
  derived from the types your active spec declares, so there is no `[selected]` table for this
  document — drop a type in `.overrides/workflow.toml` and its playbook coverage goes with it.
  Writing `[selected]` here is refused, with a message pointing you at the workflow override. You
  only need an entry for a type whose guidance you want to change, or a type you added and want role
  guidance on: a declared type with no entry still gets its generated `sq-<type>` skill, with the
  commands and lifecycle but no per-role sections.
- **A slug appears at most once per type.** `roles` is keyed by slug — one slug renders one section
  in the generated skill — so a repeat is refused at load rather than merged or rendered twice.
  Which means: to change *one field* of a bundled guide, you must restate the array by hand (omit
  `"$(*self)"` and list every guide you want to keep). Spreading and then re-adding the same slug is
  not the way to edit one.
- **Every slug must be one of three things:** a bundled catalog role, the `*dev` sentinel (which
  matches any `<tech>-dev` role), or a project role you have defined under
  `.overrides/roles/<slug>.toml`. A project role is accepted here — you do not have to pick from the
  bundled catalog.
- **A project role must also be activated for its guidance to reach the skill**, and the order
  matters. `sq role activate <slug>` is what makes the role live; a guide naming a role that is not
  live *loads without complaint* but is dropped when the skill is generated. `sq check` and `sq sync`
  both warn while that is true, naming the guide and both ways out — activate the role, or remove the
  guide. The same warning covers a role you activated and later retired, and a stray file in
  `.overrides/roles/` whose name is read as a slug but never becomes a role. It is a warning, not a
  refusal: both commands still exit `0`.
- **Unknown top-level keys are refused by name**, the same fail-closed rule the workflow override
  follows. The accepted keys are listed in the message.

### Guidance for a role you invented

A **project-defined role** — one you started with `sq override scaffold --new <slug>` and activated
with `sq role activate <slug>` — can be given playbook guidance like any bundled role. Name it in a
type's `roles`, run `sq sync`, and it gets its own section in that type's generated `sq-<type>`
skill; the skill is also preloaded on the role's generated pointer, so the role boots with it. Until
you name it somewhere in the playbook, a custom role appears in no item skill at all.

**Write the guide and activate the role in either order — just do both.** `sq override scaffold
--new` prints activation as its *next* step, so it is natural to write the playbook guide while the
role is still inactive, and that is fine: the override loads, and `sq check` reminds you the
guidance is not reaching the skill yet. What you should not do is leave it there, because an
inactive role's guidance is silently absent from the generated skill:

```bash
sq override scaffold --new security-analyst   # then fill in the stubbed fields
sq role activate security-analyst             # ← the step that makes the guidance render
sq sync                                       # regenerate the sq-<type> skills
sq check                                      # confirms the warning has cleared
```

The same applies in reverse: **retiring a role leaves its guides behind**, and the generated skills
lose those sections. `sq check` names each one so a retirement does not quietly strip guidance you
still want — either reactivate the role, or delete the guides you no longer need. This is why a
retirement can produce several warning lines at once: one per item type that role had guidance on.

### Drift

A playbook override that shadows a bundled type's entry has to carry a
`# squads:override-base:<version>` stamp, for the same reason a shadowing workflow override does: a
shadowed entry stops tracking the bundle, so its provenance has to be on the record. Note that the
append idiom counts as shadowing — writing `roles` replaces the list, stamp included. An unstamped
one is reported as an error by `sq check`:

```
error .overrides/playbook.toml: shadowing playbook override has no
squads:override-base stamp; run `sq override update playbook` to re-stamp
```

The reconciliation cycle is the one every other override kind uses:
`sq override diff playbook` → hand-merge → `sq override update playbook` → `sq check`.

---

## Staleness and drift

Overrides are authored against a bundled template or role from some version of squads. When you
upgrade squads, the bundled original may change — a new required marker, a new context variable, a
new role field. We **detect and warn you** about this drift; you **merge by hand** to reconcile it.

### How staleness is detected

When you scaffold an override (via `sq override scaffold`), the file carries a **provenance stamp**
in whichever comment syntax that file speaks. A template override carries an HTML comment, inert to
rendering:

```
<!-- squads:override-base:<version> -->
```

A role override, the workflow override and the playbook override are TOML, so they carry the stamp
as a TOML comment on the file's first line:

```toml
# squads:override-base:<version>
```

Either way it records the version you scaffolded at — "this override was branched from squads
`<version>`." When you later upgrade squads and run `sq check`, it compares:

- Your override's `override-base` stamp against the current `squads_version`.
- The bundled template at your override's `override-base` version against the bundled template
  in the *current* version (recovered from the shipped `templates_manifest.json`, which indexes
  all bundled templates by version and hash).

If the bundled original **changed** between those versions, `sq check` warns:

```
.overrides/templates/items/task.md.j2: override may be stale — bundled task.md.j2 changed since
v<version>; run `sq override diff items/task.md.j2`, merge, then `sq override update items/task.md.j2`
```

**Important:** squads only warns if the bundled original **actually changed**. If you scaffold an
override at the version you're on and later upgrade, but the bundled task template didn't change in
between, there is no warning. The stamp alone is never a problem.

**Structural errors:**
Independently, `sq check` detects if an override is **missing a required marker region** (the
`<!-- sq:* -->` anchors that the marker-safe editing depends on). This is an error, not a warning:

```
.overrides/templates/items/task.md.j2: missing required marker <!-- sq:body -->
```

If your override has clean markers and renders without error, it will render even if its stamp is
old.

### Drift on the workflow override

A workflow override that only **adds** vocabulary needs no stamp: there is no bundled entry
underneath it to drift away from. The moment it **shadows** one, that changes — a shadowed built-in
stops tracking the bundle, so its provenance has to be recorded. A shadowing override with no stamp
is reported as an error by both `sq check` and `sq workflow lint`:

```
error .overrides/workflow.toml: shadowing workflow override has no
squads:override-base stamp; run `sq override update workflow` to re-stamp
```

It is a report, not a refusal — `sq` keeps working. An older stamp gives you the ordinary drift
warning instead. The reconciliation cycle below is the same for `workflow` as for any other
override: `sq override diff workflow`, hand-merge, `sq override update workflow`. For a workflow
override, Δ-mine is your file against the current bundled spec, which is what shows you exactly what
you have shadowed.

### The end-to-end reconciliation workflow

This is how you handle an override after a squads upgrade:

#### Step 1: Check for drift

```bash
sq check
```

If any override's bundled counterpart changed since its `override-base` stamp, you'll see a warning
per override. Structural errors (missing markers) are shown as errors.

#### Step 2: Inspect the drift with two-sided diffs

```bash
sq override diff items/task.md.j2
```

This shows **two separate diffs**, side by side, so you see both what you customised *and* what the
upgrade changed:

- **Δ-mine:** your override vs. the **current** bundled task template. This shows your
  customisation — what the team designed differently from the default.
- **Δ-upgrade:** the **base-version** bundled template (the one from `override-base`) vs. the
  **current** bundled template. This shows what the upgrade itself changed in the default since you
  last branched the override.

Read Δ-upgrade to spot any new required markers or context variables the upgrade added — you'll
need to fold those into your override.

Omit the template name to diff **every drifted override**:

```bash
sq override diff
```

#### Step 3: Merge by hand

Edit `.overrides/templates/items/task.md.j2` (or the override you're reconciling) to fold the
upgrade's changes into your version while keeping your customisations:

```bash
$EDITOR squads/.overrides/templates/items/task.md.j2
```

This is not automated; you own the merge. The goal is to keep your edits (from Δ-mine) while
adopting any required structural changes from the upgrade (from Δ-upgrade) — typically new markers
or variables that the current version of squads needs.

Run `sq check` often while editing to catch structural errors (missing markers) early.

#### Step 4: Re-stamp after the merge

```bash
sq override update items/task.md.j2
```

This rewrites the `squads:override-base:` stamp to the current `squads_version` — **and nothing
else**. The body you just merged is untouched. Re-stamping is your assertion: "I have reconciled
this against the current bundled default."

The next `sq check` recomputes drift against the new base and the warning clears. Your override is
now current.

#### Bulk re-stamp after a review pass

Once you've reviewed and merged all drifted overrides, re-stamp them all at once:

```bash
sq override update
```

With no argument, this re-stamps every structurally-valid override (ones with clean markers). Broken
overrides (missing required markers) are skipped — fix those first.

---

## The `sq override` command group

The four commands below are your complete override-authoring and upgrade toolkit.

### `sq override scaffold`

Copy a bundled template or role into `.overrides/` as a starting point for editing.

```bash
# Copy a template
sq override scaffold items/task.md.j2

# Copy a template by name (all bundled template paths work)
sq override scaffold agents/role.md.j2
sq override scaffold subentities/story.md.j2

# Copy a role TOML override (a bundled role, to change its name/model/etc.)
sq override scaffold --role architect

# Same for a developer already on your roster
sq override scaffold --role python-dev

# Start a wholly custom, non-dev role that isn't in the bundled catalog
sq override scaffold --new security-analyst
sq override scaffold --new security-analyst --can-spawn   # opt it into spawning subagents

# Start the workflow override (vocabulary: item types, statuses, lifecycles, collections)
sq override scaffold workflow

# Start the playbook override (which roles interact with each item type, and their guidance)
sq override scaffold playbook

# Overwrite an existing override
sq override scaffold items/task.md.j2 --force
```

**What it does:**
- `--role <slug>` writes an (initially empty) TOML stub for the named role into
  `.overrides/roles/`, ready for the fields you want to override. A developer slug
  (`python-dev`) works the same as a bundled one.
- `--new <slug>` starts a **brand-new, non-bundled** role: the essential fields (`full_name`,
  `title`, `description`, `mission`) are stubbed as active keys, the advanced fields
  (`responsibilities`, `agreements`, `model`, `color`, `can_spawn`) are included commented out.
  Refuses a slug that's already a bundled role — use `--role` for that. Follow up with `sq role
  activate <slug>` once you've filled it in.
- Template names copy the named bundled template into `.overrides/templates/`.
- `workflow` starts `.overrides/workflow.toml` from a commented worked example rather than a copy of
  the bundled spec — see
  [Workflow overrides](#workflow-overrides-item-types-statuses-badge-collections-and-ref-kinds).
- `playbook` starts `.overrides/playbook.toml` the same way, from a commented worked example of the
  one-line append idiom — see [Playbook overrides](#playbook-overrides-role-guidance-per-item-type).
  `--workflow` and `--playbook` are equivalent flag forms of those two names.
- Every scaffolded file is stamped with the current squads version, as an HTML comment in a template
  and a TOML comment in a role, workflow or playbook override.
- Refuses to clobber an existing override unless you pass `--force`.

**This is the only command that writes override bodies.** After scaffolding, you edit the file by
hand. squads never auto-rewrites an override — your customisations stay yours.

### `sq override diff`

Show two-sided diffs for an override to help you reconcile drift.

```bash
# Diff a specific template
sq override diff items/task.md.j2

# Diff a specific role
sq override diff --role architect

# Diff the workflow override against the current bundled spec
sq override diff workflow

# Diff the playbook override against the current bundled playbook
sq override diff playbook

# Diff every drifted override (no name needed)
sq override diff

# JSON output for scripting
sq override diff items/task.md.j2 --json
```

**The two deltas:**

- **Δ-mine:** your override vs. the **current** bundled template — what you customised away from
  today's default.
- **Δ-upgrade:** the **base-version** bundled template vs. the **current** bundled template — what
  the upgrade changed underneath your override.

Both deltas are computed from the current package data and the `templates_manifest.json` shipped
with squads, so you can see what needs merging without having to find old squads versions.

### `sq override update`

Re-stamp an override's `override-base` version after you've hand-merged it, clearing the drift
warning.

```bash
# Update a specific template
sq override update items/task.md.j2

# Update a specific role
sq override update --role architect

# Re-stamp the workflow override
sq override update workflow

# Re-stamp the playbook override
sq override update playbook

# Bulk re-stamp every structurally-valid override
sq override update
```

**What it does:**
- Rewrites the `squads:override-base:` stamp to the current `squads_version`.
- **Never touches the override body** — this is not auto-rewriting. It is your signed assertion
  that you have manually reconciled the override against the current bundled default.

Run `sq check` afterwards to confirm the warning has cleared and the override is current.

### `sq override list`

List every present override with its kind, base version, and current drift state.

```bash
sq override list

# JSON output for scripting
sq override list --json
```

**Output columns:**

- **Name:** template path, role slug, `workflow`, or `playbook` (e.g., `items/task.md.j2`,
  `architect`).
- **Kind:** `template`, `role`, `workflow`, or `playbook`.
- **Base version:** the `squads_version` the override was branched from (from the stamp), or
  `(unstamped)` for a shadowing override that has no stamp yet.
- **State:** 
  - `current` — the bundled counterpart hasn't changed since the base stamp.
  - `drifted` — the bundled counterpart changed and you should reconcile via `sq override diff` +
    hand-merge + `sq override update`.
  - `broken` — the override is missing a required `<!-- sq:* -->` marker (an error in `sq check`).

**Use this to see the override surface at a glance** — what you have, what's current, and what
still needs reconciling after a squads upgrade.

---

## Agent naming

When you run `sq init`, you can supply custom names for the bundled roles. This is especially
useful if your team has specific titles or prefers different names for the agent personas.

### Naming at initialization

**Declarative flags (repeatable):**

```bash
sq init --name architect="Ada Lovelace" --name manager="Grace Hopper"
```

**Configuration file:**

Add a `[init.names]` table to `.squads.toml`:

```toml
[init.names]
architect = "Chief Designer"
manager = "Team Lead"
tech-writer = "Documentation Lead"
```

Writing the file before you initialise means `sq init` finds one already there, so pass
`sq init --force` — your `[init.names]` table survives it. A `--name` flag beats the table for the
same slug, and the table is read at `init` only: a role you activate later takes its name from
`--name` or from the bundled catalog, never from this table.

**Interactive prompting (at a TTY):**

When you run `sq init` at an interactive terminal without supplying all names, squads prompts you:

```
Enter full name for architect: 
```

Pre-answer these prompts with flags or `[init.names]` so you're never blocked.

**Skip prompting entirely:**

```bash
sq init --default-names    # uses bundled names for all roles
```

This is useful in CI or scripts where you can't interact. **Non-TTY environments (pipes, scripts,
CI) always behave as if `--default-names` is set** — you'll never hit a prompt.

**Fallback:**

Any role not named via a flag, config, or prompt falls back to its bundled name (bundled roles)
or a name from the dev pool (custom developer roles).

### Naming roles after init

When you activate a new role or add a developer, you can provide a name then:

```bash
# Activate a bundled role with a custom name
sq role activate architect --name "Chief Designer"

# Add a Python developer with a custom name
sq dev add --tech python --name "Pythonista"
```

Omit the name and the role falls back to its bundled or pooled default.

`--name` only applies while the role is being created. Activating a role that is already live is a
no-op that returns the existing entry untouched — it reports success, and a `--name` you passed
with it does nothing. Rename a live role through its override instead (see
[Which name wins](#which-name-wins) below).

### How names flow into your squad

The chosen name is stored in the ROLE item's frontmatter (`extra.full_name`). Everything
downstream reads from there:

- The **Agent roster** in your `CLAUDE.md` (generated by `sq sync`).
- The **agent pointer files** in `.claude/` (e.g., `.claude/agents/architect.md`).
- The rendered **role body** in `squads/agents/roles/ROLE-*.md`.

If you want to rename a role later, use the same role-override mechanism — see
["Override a role's name and model"](#override-a-roles-name-and-model) below — then run
`sq sync` to regenerate the pointer and `CLAUDE.md` section from it.

### Which name wins

Four things can name a role — an `init` flag, the `[init.names]` table, the `init` prompt, and
`--name` on `sq role activate` or `sq dev add` — and a role override can name it a fifth time.
They do not compete for long, because the first four all write the same field: whichever of them
applied is simply *the name stored on the role*. So the order is short, and `sq sync` honours it
every time it runs:

1. **`full_name` declared in `.overrides/roles/<slug>.toml`.** A declared name renames the role;
   an omitted one leaves the stored name alone.
2. **The name already stored on the role**, however it got there — a flag, the config table, the
   prompt, `sq role activate --name`, or `sq dev add --name`.
3. **The bundled catalog's name** — or, for a `<tech>-dev` slug with no role yet, a name picked
   from the developer pool.

**What `sq sync` keeps, and what it refreshes.** The name is kept: sync never puts the bundled one
back over yours. So is a developer's `--model`, the other field `sq dev add` lets you choose.
Everything else in a role's definition — mission, responsibilities, spawn authority, a bundled
role's model, its preloaded skills — is refreshed from the bundled definition (or from your
override) on every sync, so an improvement squads ships reaches a role you activated long ago.

**A rename is a real edit.** Declaring a new `full_name` and syncing moves the role's `updated_at`
and shows up in `sq reflog` as an update carrying the old and new names. Syncing again with the
same override changes nothing further. And a rename is not a temporary coat of paint: once the
override's name has been applied, that *is* the stored name, so deleting the override afterwards
leaves the new name in place rather than restoring the old one.

**If a role is showing the bundled name where you set your own**, write the name you want into
that role's override and sync once:

```toml
# .overrides/roles/architect.toml
full_name = "Chief Designer"
```

```bash
sq sync
```

That is the whole repair — it names the role and, being stored, the name then stands on its own.

### Slug immutability

**Role slugs stay canonical and are never renamed.** The slug (`architect`, `tech-lead`,
`<tech>-dev`) is the addressing key for skills, @mentions, pointer filenames, and interactions. A
team renames *who fills the architect slot*, not *the architect slot itself*.

If you need a new role entirely, scaffold it under a new slug. If you need to split an existing
role, add a new one rather than renaming.

---

## Examples

### Customize the task template

Your team wants all tasks to have a standard "Success criteria" section and a "Dependencies"
section at the top. Scaffold the task template:

```bash
sq override scaffold items/task.md.j2
```

Edit `.overrides/templates/items/task.md.j2` to add your sections (keeping the required `<!-- sq:body -->`
marker):

```jinja2
# {{ item.title }}

## Success criteria

_Write the criteria for completion here._

## Dependencies

- [ ] Upstream requirement 1
- [ ] Upstream requirement 2

<!-- sq:body -->
<!-- sq:body:end -->
```

The next time a task is created or rendered, it will use your template.

### Override a role's name and model

You want the architect role to use a faster model for everyday work, and you want to call them
"Design Lead." Override the role:

```bash
sq override scaffold --role architect
```

Edit `.overrides/roles/architect.toml`:

```toml
full_name = "Design Lead"
model = "haiku"
```

The rest of the architect's definition (title, mission, responsibilities) stays the same. Run `sq
sync` to regenerate the pointer and CLAUDE.md section.

### Retitle a developer without renaming them

You added a Python developer with `sq dev add --tech python` and you want them addressed as a
"Senior Python developer" — but you're happy with the name they were given. Scaffold the override
and set one field:

```bash
sq override scaffold --role python-dev
```

```toml
# .overrides/roles/python-dev.toml
title = "Senior Python developer"
```

Run `sq sync`. The new title reaches the role's definition under `squads/agents/roles/`, its
pointer in `.claude/`, and the agent roster in `CLAUDE.md`; the developer's name, model, mission
and responsibilities are untouched, because the file didn't mention them. Add `full_name` to the
same file when you do want to rename them.

### Define a custom role

You want a compliance-officer role that isn't in the bundled catalog. Scaffold it:

```bash
sq override scaffold --new compliance-officer
```

This writes `squads/.overrides/roles/compliance-officer.toml` with the essentials stubbed. Fill them in
(and uncomment any advanced fields you want):

```toml
full_name = "Compliance Officer"
title = "The keeper of standards"
description = "Ensures all code meets compliance requirements."
mission = "Keep the team on the right side of policy."
responsibilities = [
  "Review all PRs for policy violations",
  "Maintain the compliance handbook",
]
model = "opus"
```

Run `sq role activate compliance-officer` to add it to your active roster, then `sq sync` to
generate the pointer and listing.

### Upgrade overrides after a squads release

You upgraded squads and `sq check` warns that two overrides drifted. Review each one (one name per
invocation, or omit the name to diff every drifted override at once):

```bash
sq override diff items/task.md.j2
sq override diff items/bug.md.j2
```

The output shows Δ-mine (your customisations) and Δ-upgrade (what the release changed) for each.
You see that the bug template gained a new `<!-- sq:acceptance -->` marker. Merge that into your
override by hand:

```bash
$EDITOR squads/.overrides/templates/items/bug.md.j2
```

Then re-stamp both:

```bash
sq override update items/task.md.j2
sq override update items/bug.md.j2
```

Or just:

```bash
sq override update
```

to re-stamp all structurally-valid overrides. Check the warnings are gone:

```bash
sq check
```

---

## Constraints and design

**Overrides are user-owned.** They live under `squads/.overrides/`, not inside the
squads package. You author and maintain them; squads detects when the bundled originals change and
warns you to reconcile. We never auto-rewrite an override — merging upgrades is always manual.

**`.overrides/` is discoverable and portable.** It's found by the same squad-folder walk-up that
locates `.squads.toml`, so it travels with your squad and is safe from path-traversal attacks.

**Partial overrides are the default.** There is no "override everything" mode. Drop a single
template file and only that one changes; the rest stay bundled.

**`sq migrate` never touches overrides.** When squads upgrades, `sq migrate` handles the breaking
changes to durable item files; `sq override` handles the user-owned override surfaces. They're
separate concerns.

---

## Troubleshooting

**Q: I scaffolded a template but forgot to keep the required markers. How do I know what's
required?**

Run `sq check`. It will report which markers are missing as an error. Read the original bundled
template to see what you need to restore:

```bash
# Find the bundled template in the squads package
python -c "import squads._rendering; print(squads._rendering.__file__)"
# Then look at the templates/ subdirectory
```

**Q: I edited an override but `sq check` still warns about drift. Did I do something wrong?**

No — a drift warning means the **bundled original changed**, not that your edit was wrong. Run `sq
override diff` to see what the upgrade changed, incorporate those changes if needed, and then `sq
override update` to re-stamp.

**Q: Can I override the `.claude/` artifacts?**

No. Those are tool-owned and generated by `sq sync` from `ROLE` items and templates. If you want
to customize what appears in `.claude/`, override the templates that generate it
(`templates/claude/*` and `templates/agents/*`).

**Q: Can I have multiple squads with different override sets?**

Yes. Each squad folder has its own `.overrides/` directory, so teams can maintain different
customisations per squad. The overrides are discovered relative to your active squad folder
(via `--dir` or `.squads.toml`).

**Q: What if I want to add a *new* field to a role that isn't in the bundled definition?**

Role TOML overrides accept any field you add — they're flexible. If it's a field squads doesn't
recognize, it's preserved in `extra` and available to your own templates. For a field that squads
*does* recognize (like `model`), override the TOML and re-stamp the role item with `sq sync`.
