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
      contract.md.j2
      milestone.md.j2
      _default.md.j2          # used by a type that has no template of its own
    subentities/
      block.md.j2             # one story, subtask or finding block
      head.md.j2              # used only by migrations; overriding it does not change `show`
      summary.md.j2           # used only by migrations; overriding it does not change `show`
    agents/
      role.md.j2
      skill.md.j2
      operator.md.j2
    claude/
      pointer_agent.md.j2
      pointer_skill.md.j2
      claude_section.md.j2
      settings.json.j2
    agents_md/
      agents_section.md.j2
    views/
      milestone_rollup.md.j2
      role_definition.md.j2
      squads_skill.md.j2
      greeting_skill.md.j2
      memory_skill.md.j2
      item_skill.md.j2
    workflow.md.j2            # the workflow cheatsheet (`sq workflow`, the squads skill)
    workflow_static.md.j2     # the fixed part of the cheatsheet, included by workflow.md.j2
  workflow.toml
  playbook.toml
  roles.toml
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
- **`roles.toml`** is your squad's delta on the **role catalog** as one document: the roles
  themselves, the named bundles, and the developer defaults (see
  [The role catalog override](#the-role-catalog-override-rolestoml)).
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
merging of template content. (Every `<!-- sq:* -->` marker region the bundled template carries
must still be present — `sq:body` and `sq:discussion` for a task, for example. See
[Staleness and drift](#staleness-and-drift) below.)

**Role overrides merge by field:**
A `roles/architect.toml` override only replaces the fields you set. Fields you omit inherit from
the bundled role definition:

```toml
# .overrides/roles/architect.toml
title = "Chief Design Officer"
model = "opus"
# mission, responsibilities, etc. inherit from the bundled architect
```

`full_name`, the role's name, is the one field that applies only once: it names the role when the
role is created. See [Which name wins](#which-name-wins).

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
- **A field you declare wins, except `full_name`.** The developer's name is the one stored when
  they were added. A `full_name` declared in the file names a developer added after it was
  written, when `sq dev add` is given no `--name`; it never renames one you already have.
- **A name you never wrote is never invented.** Omit `full_name` and a new developer takes a name
  from the pool.

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

### The role catalog override: `roles.toml`

A per-slug file changes one role. **`.overrides/roles.toml`** is the whole role catalog as one
document, the same catalog `sq role catalog` lists, and it also reaches the parts no per-slug file
can: the developer defaults and the named bundles. Start it from a stamped, commented example:

```bash
sq override scaffold roles      # or: sq override scaffold --roles-catalog
```

The document takes three tables, plus `[selected]`. Any other top-level key is refused by name.

- **`[[roles]]`** — one entry per role, keyed by its `slug`. An entry naming a bundled slug merges
  field by field onto it, so you write only what changes. An entry naming a new slug defines a new
  role, and then `full_name`, `title`, `description` and `mission` are required.
- **`[dev]`** — the defaults a developer gets from `sq dev add`: `model`, `color`, and
  `name_pool`, the names a new developer is picked from. Each field merges on its own.
- **`[bundles]`** — the named role lists (`all`, `core`, `minimal`). The `all` bundle must name
  every role in the catalog, so a role you add here has to join it too.

```toml
# .overrides/roles.toml
# squads:override-base:<version>

[dev]
model = "opus"
name_pool = ["Hedy", "Katherine", "Frances"]

[bundles]
all = ["$(*bundles.all)", "security-analyst"]   # every role must be in `all`

[[roles]]
slug = "architect"
title = "Chief Architect"

[[roles]]
slug = "security-analyst"
full_name = "Sam Security"
title = "security analyst"
description = "Reviews changes for exposure."
mission = "Keep the attack surface small."
```

With that file, the architect is retitled, the next `sq dev add` picks a name from the new pool
and runs on `opus`, and `security-analyst` appears in `sq role catalog` as a project role, ready
for `sq role activate security-analyst`.

**Precedence, lowest to highest:** the bundled catalog, then `roles.toml`, then a per-slug
`.overrides/roles/<slug>.toml`. When both override files set the same field for one role, the
per-slug file wins. For `full_name` the order decides only the name a role gets when it is
created: an active role keeps the name it stores, whatever either file says later (see
[Which name wins](#which-name-wins)).

**Dropping a role** goes through `[selected].roles`, which lists the roles that survive. A bundle
that still names a dropped role is refused, naming the bundle:

```
bundle 'all' references unknown slug 'devops' — 'devops' looks deselected via [selected].roles;
deselecting a role also means deselecting it from (or rewriting) every bundle that still names it
```

A bundle is a plain list, so rewrite it without the role:

```toml
[selected]
roles = ["manager", "architect", "tech-lead", "reviewer", "qa", "product-owner", "tech-writer"]

[bundles]
all = ["manager", "architect", "tech-lead", "reviewer", "qa", "product-owner", "tech-writer"]
```

A dropped role can no longer be activated. A file that only adds, such as a new bundle, needs no
stamp. One that changes a bundled role, a bundled bundle or `[dev]` must carry the
`squads:override-base` stamp, and `sq check` reports it as an error until it does. Appending a
role to `all` counts as changing it, so a file that adds a role always needs the stamp. The upgrade cycle is the same as for every other override:
`sq override diff roles`, merge by hand, then `sq override update roles` (see
[Staleness and drift](#staleness-and-drift)).

---

## Workflow overrides: item types, statuses, badge collections, ref kinds and views

By default, squads uses a bundled set of **item types** (`sq workflow types` lists the set your
build ships), **status lifecycles** (state machines for each type), **badge collections** (priority
and severity, the reusable axes that label findings, tasks, etc.), **ref kinds** (the labelled
edges — `blocks`, `fixes`, `supersedes` and the rest — that link one item to another) and
**derived views** (declared read-only sources over those edges, rendered by a template).
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
- `validators` — checks this type runs beyond the set its category already turns on, each with an
  optional parameter and level. Some checks run nowhere until a type names them here. See
  **Validators** (below).
- `[items.<type>.attributes]` — the keys an item of this type stores beyond the core ones, each
  with a kind. See **Attributes** (below).

#### Custom records-category item types

Squads distinguishes two item categories:

- **Work items** (`category = "work"`, the default) — ephemeral; flow through a lifecycle towards completion
  (epic, feature, task, bug, review). Work items can be children in a hierarchy and map to effort.
- **Records** (`category = "records"`) — durable reference documents; authored once, maintained indefinitely
  (decisions/ADRs, guides, contracts, standards, postmortems, etc.). Records have no parents and no hierarchy.

The bundled records types are `decision` (ADR), `contract` (PRD), `milestone` and `guide`. When you
define a custom records-category type, squads treats it like a decision or guide: it takes no parent
and nests in its own folder.

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
- IDs like `PM-<n>`, where `<n>` is the next number of the squad-wide sequence every type shares,
  not a count that starts at 1 for the new type
- Storage in `squads/postmortems/`
- The same lifecycle as guides (Draft → Published → Deprecated)
- No parent constraints (records never have parents)

After defining it, you can:

```bash
sq create postmortem "API outage" --author architect   # → PM-<n>, starts Draft
sq postmortem <n> body --file postmortem-incident.md
sq postmortem <n> status Published
sq list -t postmortem    # Published postmortems stay in this listing
```

Which statuses a listing hides follows the status role, not the category: `Published` has the
`in_force` role, which is not `hidden`, so a published postmortem stays in `sq list`. A records
item takes part in `sq inbox` the same way every item does: an `@mention` in its discussion is
listed while its status role is not settled, and drops out once it reaches a settled status such
as `Published`.

#### Attributes: the keys a type stores

An item file's frontmatter is one flat mapping. The **core keys** are the same on every item:
`id`, `sequence_id`, `type`, `title`, `slug`, `status`, `description`, `parent`, `author`,
`assignee`, `priority`, `severity`, `labels`, `refs`, `subentities`, `created_at`, `updated_at`,
`created_session` and `modified_session`. Every other key is an **attribute**, and a type declares
the attributes it carries in an `attributes` table:

```toml
[items.incident.attributes]
customer = { kind = "str" }
systems = { kind = "list" }
paged = { kind = "bool" }
review_due = { kind = "date", required = true }
```

- `kind` is one of `str`, `list` (a list of strings), `bool` or `date` (`YYYY-MM-DD`).
- `required` (default `false`): `sq check` reports an item that does not store it, as
  `error INC-<n>: missing required attribute 'review_due'`. It never makes an item unreadable, so
  adding it to a type with existing items only produces reports.
- `settable` (default `true`): whether `sq <type> <n> update --set` and an `update` event of
  `sq import` write it. A key a dedicated command owns is declared `settable = false`. Roles,
  skills and operators have no `update` verb, so their attributes are set through `sq import`.

`sq workflow types --json` lists each type's attributes with their `kind`, `required` and
`settable`. The bundled spec declares `target_date` on `milestone`, `target_ref` on `review`,
`tags` and `tech` on `guide`, `is_default`, `is_dev`, `model` and `tech` on `role`, and
`allowed_tools`, `model` and `when_to_use` on `skill`. Add attributes to a bundled type the same
way, roster types included:

```toml
[items.guide.attributes]
audience = { kind = "str" }
```

A declared attribute is set from the command line, with its value checked against its kind before
anything is written:

```bash
sq guide <n> update --set audience=operators
sq guide <n> update --set tags=setup,cli        # a list is comma-separated
sq incident <n> update --unset systems
```

```
error: 'paged' expects true or false; got 'heavy'
error: 'review_due' expects an ISO date (YYYY-MM-DD); got 'tomorrow'
```

A `bool` takes `true`, `false`, `yes`, `no`, `on`, `off`, `1` or `0`, in any letter case. `sq
import` checks a value the same way. A value already in a file is never changed or removed by
validation: `sq check` reports one that does not fit its kind, such as
`error INC-<n>: attribute 'systems': expected a list of strings, got str 'db'`, and it stays as
written until a command that targets that key replaces it.

**What the loader refuses.** An attribute cannot take the name of a core key, of another attribute
or badge field on the same type, of a key `--json` adds to an item row (`badges`, `body`,
`discussion`, `matched_subentities`), or `extra`, `path` or `prefix`:

```
- 'guide': attribute 'title' is a reserved key — pick another name
```

The `role` and `skill` attributes the bundled spec declares are the ones sq writes into each
agent's files, so an override may add to them but cannot drop one or change its kind:

```
- roster type 'role' must declare attribute 'model' with kind 'str' — add `model = { kind = "str" }` under [items.role.attributes]
```

`extra_fields` is not a key of a type: it is refused at load, naming the table to use instead:

```
items.task.extra_fields: 'extra_fields' is not a declared key — a type's keys are declared in an `attributes` table — replace it with `[items.task.attributes]` and one `<name> = { kind = "str" }` line per key (kind is str, list, bool or date).
```

**Keys no declaration names are kept.** A key you add to a file by hand, a key a removed
declaration used to name, and a key from a newer spec are all carried through every write and
through `sq repair`, with their values. No command removes a key it was not asked to change.
`--json` item rows carry them too, at the top level beside the core keys, except a key named like
one `--json` adds (`badges`, `body`, `discussion`, `matched_subentities`), which stays in the file
and out of the row. A value is kept in the form JSON can carry: a YAML-only value is written back
as its JSON equivalent the next time the item is written, so an unquoted date such as
`review_date: 2026-11-01` becomes the string `'2026-11-01'`, and a mapping key that is not a string
becomes one.

To be told about such keys, for example to catch a misspelt one, select the
`frontmatter_key_undeclared` check on a type (see **Validators**, below). It reports at `warn`
and changes nothing:

```
warn GUIDE-<n>: frontmatter key 'hand_key' is not declared on guide
```

**In a template**, an item's attributes are read from `item`, like its core keys:
`{{ item.audience }}`. An item stores only the attributes that are set, so guard an optional one:
`{% if item.audience is defined and item.audience %}`.

A custom badge field (see **Collections**, below) is stored the same way, at the top level under
its code (`impact: high`).

#### Validators: the checks a type runs, and how loud they are

Every item type runs a set of checks. `sq check` reports what they find, and the create/update
gate refuses a write on the `error`-level ones. You do not compose that set from scratch: each
type gets a cross-cutting core plus a bundle its `category` implies, and a type's own
`validators` list is where you **add** to it and say how much you mean each addition. A check that
looks at the squad as a whole sits outside every type's list: `roster_slug_valid`, which checks
role and operator slugs (see [stability.md § "Comment headers"](stability.md#comment-headers)), runs
on every `sq check` at a fixed `error` level, and cannot be selected, dropped or given another level.

```toml
[items.task]
validators = ["parent_present@warn"]
```

These checks are not selected for you anywhere in the bundled spec, so naming one in a type's
list is the only way it ever runs on that type:

- `parent_present` — every item of this type must have a parent.
- `ref_rule_target_present` — a delivered item of this type must carry a typed ref (see
  [workflow.md](workflow.md#keeping-a-contract-current) § "Keeping a contract current").
- `no_status_banner` — an item's body or summary must not open with a status label.
- `subentity_title_max` — a sub-entity title must not be longer than a threshold.
- `frontmatter_key_undeclared` — every top-level key of an item must be a core key or an attribute
  its type declares. It reports at `warn` and never changes the file; see **Attributes** (above).
- Seven policy checks about the work an item tracks: `item_title_max`, `external_id_not_in_title`,
  `description_present`, `assignee_present`, `body_written`, `settled_requires_discussion` and
  `ref_rule_target_typed`. See "The work-policy checks" below.

The set of names is fixed by the version you are running, and one it does not hold is refused at
load, naming your entry:

```
item 'task': validators entry 'nonesuch' names an unknown validator
```

**The status-banner and title checks.** Both hold an item to a writing convention, not to anything
squads needs in order to work, so a type runs one only when its list names it:

- **`no_status_banner`** warns when the first line of an item's body, or of its summary (`--desc`),
  is a status label: `Status:` in any letter case, bold or not, or a `## Status` / `### Status`
  heading. An item's status is its `status` field, and a copy written into the prose keeps saying
  what it said after the field has moved on. Only the first line is read, so the same heading
  further down a body is not reported, and an item is reported once: for its body, or else for its
  summary. The check takes no parameter.
- **`subentity_title_max`** warns when a sub-entity title — a story, subtask or finding in the
  bundled spec — is longer than a threshold: 120 characters when you name the check bare, or the
  number you give it (`subentity_title_max:80`). A type that names it also gets an advisory from
  `sq <type> <n> add-<kind>` when the title just given is over the same number; the sub-entity is
  added either way. The check follows the sub-entity kind a type hosts, not its category: a
  `records` type that hosts a kind runs it once the type names it, and a type that hosts no kind
  may name it and reports nothing.

One line turns both on for one type:

```toml
[items.feature]
validators = ["no_status_banner", "subentity_title_max"]
```

A feature whose body opens with `## Status`, and which carries a story with a 121-character title,
is then reported twice by `sq check`, which still exits `0`:

```
warn FEAT-<n>: advisory: story US<k> title is 121 chars (threshold: 120) — a sub-entity title is
a one-line handle; put the detail in the body
warn FEAT-<n>: body opens with a status/lifecycle banner — move state to frontmatter or a dated
discussion comment
```

A summary that opens the same way reads `description opens with a status/lifecycle banner`. And
`sq feature <n> add-story` with that title adds the story, then prints under its usual
confirmation:

```
Title is 121 chars — a sub-entity title is a one-line handle, not the description. Put the detail in the body:
  sq feature <n> story US<k> body -m "…"
```

A title of exactly 120 characters triggers neither. Take the line out and none of the three is
printed. Either name takes a level; what `@error` changes for each, and what it leaves alone, is
under "Levels" below.

**The work-policy checks.** Seven more checks hold an item to a team's habits about the work it
tracks. Each reports at `warn` unless you name a level:

| Check | Reports an item when | Parameter |
|---|---|---|
| `item_title_max` | its title is longer than the threshold | required: `item_title_max:<n>` |
| `external_id_not_in_title` | its title matches your pattern, such as a tracker id | required: `external_id_not_in_title:<regex>` |
| `description_present` | its summary (`--desc`) is empty | none |
| `assignee_present` | it rests in a live status with nobody assigned | none |
| `body_written` | its body is still the scaffold its template rendered | none |
| `settled_requires_discussion` | it rests in a settled status and its own discussion holds no comment | none |
| `ref_rule_target_typed` | an edge whose kind has a typed `ref_rules` entry on the type points at another type | none |

"Live" and "settled" are the status role's flags (`sq workflow roles`), never a status name. A
comment on one of the item's stories, subtasks or findings does not count for
`settled_requires_discussion`. And `ref_rule_target_typed` reads only the rules that declare a
`target`: the bundled feature's `implements` rule is one, so an `implements` edge from a feature
to a bug is reported.

The two with a required parameter are refused bare, the same way `ref_rule_target_present` is:

```
item 'feature': validators entry 'item_title_max' is missing its required parameter — name it as
'item_title_max:<n>', or drop the validator; without a parameter it never fires
```

A pattern cannot contain a literal `@`, because `@` starts the level. Write it as `\x40` inside a
single-quoted TOML string, which keeps the backslash: `'external_id_not_in_title:me\x40corp'`.
These checks apply to `work` and `records` types only. Naming one on `role`, `skill` or `operator` is
refused at load.

```toml
[items.feature]
validators = [
  "item_title_max:30",
  "external_id_not_in_title:JIRA-[0-9]+",
  "description_present",
  "assignee_present",
]
```

A feature created as `"Fix login timeout for JIRA-4411 users"` with no summary is then reported
three times by `sq check`, which still exits `0`:

```
warn FEAT-<n>: description is empty — set a summary: `--desc` on create, `update --desc` after
warn FEAT-<n>: title holds `JIRA-4411` (matches the external-id pattern `JIRA-[0-9]+`) — keep
tracker ids out of the title
warn FEAT-<n>: title is 37 chars (threshold: 30) — an item title is a one-line handle; put the
detail in the body
```

Moving it to `InProgress` with no assignee adds `status is InProgress but nobody is assigned`.
`body_written` and `settled_requires_discussion` read the item's file, so at `error` they make
`sq check` fail but never refuse a write. The other five take part in the write gate (see
"`error` does not always give you a write gate" below): with `description_present@error`, a
`sq create feature` without `--desc` is refused. `ref add` is not one of the gated writes, so
under `ref_rule_target_typed@error` a mistyped edge is still added, and the refusal lands on the
feature's next update instead.

**Selection is per type, and there is no squad-wide switch.** The line above changes nothing for a
task, a decision or any other type: a squad that wants a check everywhere names it on each type.
Two bundled types, `epic` and `skill`, ship a `validators` list of their own, and there the entry
has to be added to the bundled list, not written over it — see "a type's own list is an ordinary
array" below before you write either.

**The four shapes of an entry** — a parameter, a level, both, or neither:

| Shape | Example | What it says |
|---|---|---|
| `name` | `parent_present` | Run this check at its bundled level. |
| `name:param` | `subentity_title_max:80` | Run it with your parameter instead of the bundled one. |
| `name@level` | `parent_present@warn` | Run it at the level you name. |
| `name:param@level` | `subentity_title_max:80@error` | Both. |

**The param always comes first, and the separator for the level is `@`, not a second `:`.** `:`
already means "here is the parameter", so `name:param:level` would not say which half is which.
The level is cut off at the first `@` and the parameter off the first `:` of what remains, so a
reversed spelling does not quietly mean something else — it fails at load with the whole tail read
as a level:

```
item 'task': validators entry 'subentity_title_max@warn:40' names an unknown level 'warn:40'
(must be one of ['error', 'warn'])
```

The one place `@` is not ruled out is a parameter that names an item type, and item-type names are
not character-restricted. A type declared with `@` in its own name and then selected as a
`ref_rule_target_present` target mis-splits — the piece after the `@` is read as the level and
refused as an unknown one, so it fails closed while naming the wrong half of your entry.

**Levels: `error` and `warn`** — only those two, and a third is refused by name:

```
item 'task': validators entry 'parent_present@fatal' names an unknown level 'fatal'
(must be one of ['error', 'warn'])
```

- **`warn`** — reported and nothing more. `sq check` prints it and still exits `0`; every create,
  update and transition goes through.
- **`error`** — `sq check` exits `3`. Whether the create/update gate *also* refuses the write
  depends on the check, not on the level — read the next paragraph before choosing this.

**`error` does not always give you a write gate, and this is the thing to get right before you
pick a level.** The gate runs against the item it is about to write and the index. It deliberately
holds neither the item's own file on disk (on a create there is not one yet) nor a scan of which
types the corpus contains (a full walk on every write). So:

> **A check that reads only frontmatter and the index takes part in the gate. A check that reads
> the item's file text, or which types exist, is reported by `sq check` and sits the gate out
> whatever level you give it.**

`no_status_banner@error` is the clearest case of the second kind: `sq check` exits `3` on a body
that opens with a status banner, and the write that put it there — plus every write after —
succeeds. Same for `ref_rule_target_present@error`: a feature reaches a delivered status with no
`implements` ref, the transition is allowed, and the finding is in the report. Select either of
those at `error` expecting a blocked write and you get a red pipeline over an unchanged workflow.

So `@error` always makes `sq check` a hard gate for a rule, which is what you want it for in CI.
Only for a check of the first kind does it also refuse writes.

**And when it does refuse writes, it refuses more than you asked for.** A gating check raised to
`error` turns *ordinary edits* on the items already failing it into refusals, edits that have
nothing to do with what the check reports. A task type carrying `subentity_title_max:40@error`
with an over-length subtask title already on disk refuses a retitle, a summary change and a status
transition of that task until the subtask title is shortened, each with the finding as its error.
What it does not refuse is the write that makes the title too long: `add-subtask` with a title
over the number still adds the subtask and prints its advisory, and retitling a subtask past the
number goes through. The refusal lands on the task's own next edit, not on the subtask. Raising a
level on a corpus you have not cleaned first is how a board seizes up — see "Adopting
`parent_present` without the cliff" below for the way through.

**The floor: two checks you may raise but never lower.** Most accept either level. Two refuse to
go below `error`:

```
item 'task': validator 'parent_acyclic' cannot be selected below its floor level 'error'
(got 'warn')
```

The floor is deliberately tiny, and the reasoning is more useful than the list, because it tells
you where the next one would come from. **A check has a floor when lowering it would leave a real
breakage with nothing left that reports it.**

- **`parent_acyclic`** — a parent chain that closes on itself. This is the check behind that
  refusal: an update closing a loop is rejected with
  `BUG-<n>'s parent chain forms a cycle: BUG-<n> -> BUG-<m> -> BUG-<n>`, followed by the
  `--no-parent` command that breaks it. `warn`-level findings never gate anything, so at `warn`
  nothing would stand between a loop and your corpus.
- **`subentity_container_marker`** — the item's file has no container section for the sub-entity
  plural its kind now declares, which is what a `[subentity_kinds.<kind>] plural` rename over
  existing items produces. `sq check` is the only place this is visible: `sq workflow lint` reports
  the spec `OK`, ordinary updates keep succeeding, and `add-<kind>` fails with a bare
  `no <plural> section in <ID>` that does not say why. Silence the report and the only explanation
  of the failure goes with it.

Every other check that ships at `error` may be dialled down, and each for its own reason rather
than a blanket one:

- **`item_status_valid`, `subentity_status_valid`** — an item resting at a status its type no
  longer declares. There is a designed way out that does not involve the check: `--force` on a
  status update skips the transition lookup and only requires the *target* status to be one the
  type declares, so `sq <type> <n> status <declared-status> --force` recovers an item from off the
  graph whatever the level.
- **`parent_in`, `no_parent`** — a parent of the wrong type, or a parent on a type that should
  have none. These state a hierarchy policy; nothing downstream needs the constraint to already
  hold in order to work, and a team may want a looser shape than the bundled one on purpose.
- **`subtask_story_mapping`** — a sub-entity mapped to a parent story that does not resolve. It
  affects the roll-up display, and it is visible in that display.

`parent_present` is deliberately outside the floor, which is the whole point of the level suffix —
see below.

**A threshold is yours to set.** `subentity_title_max` is the worked example: it warns on a
sub-entity title longer than a threshold, and the threshold is its parameter — a positive integer,
refused otherwise:

```
item 'task': validators entry 'subentity_title_max:0' names a non-positive-integer
subentity_title_max threshold '0'
```

Name the check with no parameter and the threshold is 120. A type that does not name the check at
all has no threshold: `sq check` reports no title on it and `add-<kind>` prints no advisory,
whatever the length. The number a type runs applies to **both** places it surfaces, which is what
stops the two from disagreeing: the `sq check` finding and the advisory printed at
`sq <type> <n> add-<kind>` time. With `validators = ["subentity_title_max:40"]` on `task`, a
49-character subtask title produces the advisory at `add-subtask` and this at check time:

```
warn TASK-<n>: advisory: subtask ST<k> title is 49 chars (threshold: 40) — a sub-entity title is
a one-line handle; put the detail in the body
```

`ref_rule_target_present`'s parameter is the item type the ref must reach, and it is required —
without one the check can never fire, so the loader refuses it rather than let it sit there doing
nothing:

```
item 'feature': validators entry 'ref_rule_target_present' is missing its required target type
parameter — name it as 'ref_rule_target_present:<type>', or drop the validator; without a
parameter it never fires
```

The target you name must also be one this type declares a `ref_rules` entry for, and the message
says so with the line to add.

**When a repeat is legal, and when it is refused.** This is the rule to get right: the same shape
means "one selection" for one check and "two selections" for another, and the difference is whether
that check reads *every* matching entry or only the first. You do not have to work out which is
which — the loader knows, and it refuses any repeat that would leave an entry doing nothing rather
than accepting it.

**`ref_rule_target_present` accepts several entries with different parameters.** It reads all of
them and treats them as one obligation over several target types, so two entries are two
selections rather than a repeat, and this loads clean:

```toml
[items.feature]
ref_rules = [
  { kind = "implements", target = "contract" },
  { kind = "addresses", target = "milestone" },
]
validators = [
  "ref_rule_target_present:contract",
  "ref_rule_target_present:milestone",
]
```

**`subentity_title_max` does not.** It resolves the first matching entry and stops, so a second
one could only ever be inert. Rather than let you write a line that silently never takes effect,
the loader refuses it, names both entries, and says which one would have resolved:

```
item 'task': validator 'subentity_title_max' is selected more than once
('subentity_title_max:40' and 'subentity_title_max:80') — 'subentity_title_max' resolves only its
first matching entry, so the second would be silently ignored rather than take effect — refused
here instead; keep one entry
```

Two more cases, so the whole rule is in one place:

- **The identical entry twice** is always refused, for any check:
  `validator 'no_status_banner' is selected more than once ('no_status_banner' repeated) — keep
  one entry`. So is the same parameter twice on `ref_rule_target_present`.
- **A differing `@level` never makes two entries independent**, for any check:
  `no_status_banner@warn` alongside `no_status_banner@error` is refused with `an '@<level>' suffix
  alone does not make two entries independent selections`. A level is a property of the one
  selection, not a second one.

**Adopting `parent_present` without the cliff.** `parent_present` requires every item of the type
to have a parent. Nothing bundled selects it, and its level is why: at `error` it does not just
refuse new parentless items, it refuses the next ordinary edit to every parentless item already on
your board. On a corpus that has been running without the convention, turning it on that way is a
wall.

`parent_present` carries no floor, so you can adopt the convention as a warning:

```toml
[items.task]
validators = ["parent_present@warn"]
```

The spec loads with parentless tasks already on disk, `sq check` reports each one
(`warn TASK-<n>: task requires a parent of type feature`) and still exits `0`, new parentless tasks
are still created, and editing an existing one is not refused. Work through the backlog, then
tighten to `parent_present` — bare, or `@error`, which mean the same thing — when the report is
clean.

**What the list cannot do — there is no deselection surface.** `[selected]` has no `validators`
section, and neither the cross-cutting core nor a category bundle can be subtracted from. The
quietest a bundled check can be made is `warn`, which still reports. The checks nothing
bundled selects are in neither the core nor a bundle, so a type that does not name one does not
run it.

**But a type's own list is an ordinary array, and arrays are leaves** (see § "Plain arrays are
leaves — replaced whole"). Two bundled types ship a `validators` entry of their own, `epic`
(`["no_parent"]`) and `skill` (`["item_skill_shadowed"]`), and writing the key in your override
replaces the whole list rather than adding to it. This turns the status-banner check on for epics
and drops `no_parent`, with no warning, so epics start accepting a parent:

```toml
[items.epic]
validators = ["no_status_banner"]      # no_parent is gone
```

Splat the bundled list to keep it:

```toml
[items.epic]
validators = ["$(*items.epic.validators)", "no_status_banner"]
```

The splat needs a bundled list to copy. A type that ships none, `task` for one, refuses the same
token at load, so write its list plain:

```
dangling splat path 'items.task.validators' has no counterpart in the bundled base
```

**Reading it back.** `sq workflow lint` is what validates the entries — every problem at once,
each naming the type and the entry. A malformed one is a load-time hard stop like any other
override error, so until it is fixed every `sq` command refuses rather than running against a
half-applied spec.

There is no command that lists a type's effective validator set. What a selection actually does is
visible in `sq check`:

```bash
sq workflow lint     # are my entries well-formed?
sq check             # what do they find?
```

`sq check` exits `0` when it is clean or found warnings only, and `3` when it found anything at
`error` — so a raised level is testable in a script without reading the output.

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

Optional fields:
- `role` — the name of a status role (from the role catalog) that governs this status's
  terminal/hidden/color attributes; defaults to `pending`. See **Status roles** (below) for the
  full role catalog and how to define custom roles.
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

#### Derived views: declared sources

A **derived view** is a read-only source over relationships an item already has — every item
pointing here with a given ref kind, this item's own sub-entities, its descendants of some type,
its own merged role definition, a type's playbook lane, or the item itself — rendered by a
template. Views are declared in `[views]`, and nothing about them is a special case: they merge,
shadow and drop exactly like item types and statuses do.

A view declares only its `source`: `fields`, `group_by`, `order_by` and a type attachment
(`items.<type>.views`) are refused by name, and
[migration.md § "Upgrading to 0.15: view declarations"](migration.md#upgrading-to-015-view-declarations)
shows the load error and a worked conversion.

Every view is **computed on every request**. No view is ever written into an item's file, so
declaring, changing or dropping one rewrites nothing on disk and leaves nothing behind.

**Declaring one of your own:**

```toml
[views.open_incidents]
source = { kind = "ref", name = "escalates" }
```

`source.kind` is `"ref"`, `"subentity"`, `"subtree"`, `"role"`, `"playbook"` or `"self"`; for the
first three, `source.name` must be a declared ref kind, sub-entity kind or item type respectively
— a name your merged spec does not declare is refused at load, with the rest of the spec's
cross-references. There is no field list, no grouping, no ordering to declare — a view is a
source, an optional `position`, and a template, nothing more. The complete field reference is
in [workflow.md § "Derived views"](workflow.md#derived-views-field-reference).

##### Setting a view's position

`position` says where the view's tag sits in a document's `sq:body` region: `"bottom"` (the
default), `"top"`, or `"after(<regex>)"` — its own line after the line where the pattern's first
match ends, falling back to the bottom when nothing matches. Set it on your own view beside
`source`:

```toml
[views.open_incidents]
source = { kind = "ref", name = "escalates" }
position = "top"
```

or on a bundled view, without restating its `source`:

```toml
[views.milestone_rollup]
position = "after(^## Scope)"
```

Every body write re-places the tags, so a changed `position` moves the tag on each document's
next body write, and a new document gets it from the start. A bad value or a pattern that does not
compile fails the load; `sq workflow lint` lists it. The full grammar, the view-name rules and
the placement rules are in
[workflow.md § "Derived views: field reference"](workflow.md#derived-views-field-reference).

Read it back, and resolve it against an item:

```bash
sq workflow views                             # your view, listed beside the bundled ones
sq workflow view open_incidents <id>          # resolved and rendered
sq workflow view open_incidents <id> --json   # the resolved source, no presentation
```

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

The template receives `source` — the resolved value, unflattened: a plain list of real
`Item`/sub-entity objects for `ref`/`subentity`/`subtree`, or the source's own native value for
`role`/`playbook`/`self` — plus `item` and `spec`. Grouping and ordering are the template's own
job, with Jinja's `groupby`/`sort`/`selectattr`:

```jinja
{% for r in source | sort(attribute="type,sequence_id") %}
- **{{ r.id }}** {{ r.status }} — {{ r.title }}
{% endfor %}
```

Reordering the bundled milestone roll-up, or regrouping it onto a different axis, is therefore a
template change, not a declaration change — copy the template with `sq override scaffold`, edit
its Jinja `sort`/`groupby` call, and the one-line `[views.milestone_rollup]` declaration itself
never needs to move.

**A view you declare needs a template of your own at that path.** There is no generic fallback
rendering: until `.overrides/templates/views/<name>.md.j2` exists, resolve your view with `--json`,
which skips presentation entirely.

**Dropping a view.** `[selected].views` names the views that survive — a view is reached only by
placing its own `sq:view:<name>` tag in a document body, never by a type attachment:

```toml
[selected]
views = []          # drop the declaration
```

A tag already placed for a dropped view no longer resolves: `sq check` reports each one at error
level, and `sq <type> <n> view disable <name>` quiets it. A tag is never removed, only disabled.

##### Authoring a role or skill body by hand

A role's body, a permanently-system skill's body (`squads`, `greeting`, `sq-memory`) and a
per-item-type `sq-<type>` skill's body render through their view and refuse prose — replace and
append alike, `--force` or not. Their content normally comes from `.overrides/roles.toml`
(`.overrides/roles/<slug>.toml` for a project-defined role), the playbook overrides, or the
view's own template override. To write one of these bodies yourself instead, drop its view from
`[selected]`. `[selected].views` lists the survivors, so name every other view you keep:

```toml
[selected]
views = ["milestone_rollup", "role_definition", "greeting_skill", "memory_skill", "item_skill"]
```

With `squads_skill` dropped, `sq skill squads body -m "…"` is admitted, and `sq sync` and
`sq repair` leave the prose alone. The tag already in the body now names an undeclared view, so
`sq check` reports it until you run `sq skill squads view disable squads_skill`. A role has no
`body` verb; with `role_definition` dropped, a role's body is written through a `sq import` body
event:

```json
{"op": "body", "target": "ROLE-1", "body": "Our own QA charter.", "as": "manager"}
```

Dropping `role_definition` affects every role at once — each one's tag becomes an undeclared-view
error in `sq check` until disabled. A role activated while the view is dropped gets no tag at all.
Putting the view back in `[selected]` makes the bodies refuse prose again, and `sq check` names
the remedy for each document that lacks the tag. The text you wrote stays, and renders beside the
view once its tag is re-enabled with `view add`; changing it means dropping the view again.

A runbook you want to keep does not belong in an `sq-<type>` skill's body: give it a skill of its
own with `sq skill add`. If one already sits in an `sq-<type>` skill, `sq check` names the five
steps that move it out — see
[migration.md § "After `sq migrate up`: seeded views"](migration.md#after-sq-migrate-up-seeded-views).

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
items = ["epic", "feature", "task", "bug", "decision", "contract", "milestone", "review",
         "role", "skill", "operator"]
```

That squad has no `guide` type: it is absent from the list, so it is dropped. The accepted section
keys are `items`, `statuses`, `lifecycles`, `collections`, `subentity_kinds`, `roles`, `ref_kinds`
and `views` — the sections the top level accepts, less `[selected]` itself. Anything else under
`[selected]` is refused by name, and the refusal prints the accepted set for the version you are
running, which is the list to trust rather than this one:

```
selected.bogus: unknown [selected] section 'bogus' — use one of the accepted [selected] sections
in v<version>: ['collections', 'items', 'lifecycles', 'ref_kinds', 'roles', 'statuses',
'subentity_kinds', 'views']
```

Two things follow from `[selected]` being the surviving set of the *merged* spec:

- **List your own additions too.** If you both add `[items.handbook]` and write `selected.items`,
  `handbook` must appear in that list or your own new type is dropped again.
- **Every name in the list must exist in the merged spec.** A typo, or a type you have not declared
  in the same file, is a load-time hard stop that names the accepted set:

  ```
  selected.items.handbook: unknown items key 'handbook' — use one of the accepted items keys in
  v<version>: ['bug', 'contract', 'decision', 'epic', 'feature', 'guide', 'milestone', ...]
  ```

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
| A malformed or repeated `validators` entry | `item 'task': validators entry 'parent_present@fatal' names an unknown level 'fatal' (must be one of ['error', 'warn'])` — see § "Validators" for every shape the loader refuses |
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

The same list is also how you turn on a check nothing bundled selects, and how you set the level
and the parameter it runs with — see § "Validators" above for the full grammar. The checks that ship
unselected include `ref_rule_target_present` (squads types the `implements` edge from a feature to a
contract but never requires it — see [workflow.md](workflow.md#keeping-a-contract-current) §
"Keeping a contract current"), `parent_present`, `no_status_banner`, `subentity_title_max`,
`frontmatter_key_undeclared` and the seven work-policy checks listed there.

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

**Reading the file is not the same as knowing your vocabulary.** Because an override can shadow,
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

A role guide takes these fields:

| Field | What it holds |
|---|---|
| `slug` | The role the guide is for (required). |
| `enter` | What the role reads or confirms before acting. Rendered under **Enter**. |
| `do` | The core actions, ideally with the `sq` commands. Rendered under **Do**. |
| `handoff` | What moves the work on, and to whom. Rendered under **Hand off**. |
| `watch` | Pitfalls and scope limits. Rendered under **Watch for**. |
| `authors` | `true` makes the role an in-lane author of the type. Defaults to `false`. |

`authors` is the only field that changes behaviour. `sq create <type> --author <role>` prints an
advisory when the author has no `authors = true` guide on that type. The create still goes
through. A role meant to file bugs claims the lane like this:

```toml
[types.bug]
roles = [
  "$(*self)",
  { slug = "security-analyst", authors = true, enter = ["Read the threat model"], do = ["Record any exposure found"], handoff = ["Exposure confirmed → @tech-lead to plan the fix"], watch = ["Don't file a bug for a policy question"] },
]
```

After `sq sync`, `sq create bug --author security-analyst` no longer prints
`advisory: 'security-analyst' is not the in-lane author for 'bug' items`, and
`sq role security-analyst show` lists `bug` under `creates`.

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
  `.overrides/roles/<slug>.toml` or in `.overrides/roles.toml`. A project role is accepted here — you do not have to pick from the
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
warn .overrides/templates/items/task.md.j2: override may be stale: bundled items/task.md.j2 changed
since v<version>; run `sq override diff items/task.md.j2`, merge, then `sq override update items/task.md.j2`
```

**Important:** squads only warns if the bundled original **actually changed**. If you scaffold an
override at the version you're on and later upgrade, but the bundled task template didn't change in
between, there is no warning. An old stamp alone is never a problem.

**A missing stamp is.** A template override must carry the stamp, so one you created by hand
rather than with `sq override scaffold` (or one whose stamp line you deleted) is reported as an
error, and `sq override list` shows it as `(unstamped)` and `drifted`:

```
error .overrides/templates/items/task.md.j2: override has no squads:override-base stamp;
run `sq override scaffold --force` to re-scaffold with a stamp, or `sq override update` after
verifying the content
```

Once you have checked the content against the bundled template, `sq override update items/task.md.j2`
stamps it.

**Structural errors:**
Independently, `sq check` detects if an override is **missing a required marker region** (the
`<!-- sq:* -->` anchors that the marker-safe editing depends on). This is an error, not a warning:

```
error .overrides/templates/items/task.md.j2: override is missing required sq marker(s):
<!-- sq:discussion --> (breaks marker-safe editing; add the missing regions)
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
sq override scaffold subentities/block.md.j2

# Copy a role TOML override (a bundled role, to change its title/model/etc.)
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

# Start the role catalog override (roles, bundles and developer defaults in one document)
sq override scaffold roles

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
  [Workflow overrides](#workflow-overrides-item-types-statuses-badge-collections-ref-kinds-and-views).
- `playbook` starts `.overrides/playbook.toml` the same way, from a commented worked example of the
  one-line append idiom — see [Playbook overrides](#playbook-overrides-role-guidance-per-item-type).
- `roles` starts `.overrides/roles.toml` from a commented worked example — see
  [The role catalog override](#the-role-catalog-override-rolestoml). It is a different file from
  the per-slug one `--role <slug>` writes.
- `--workflow`, `--playbook` and `--roles-catalog` are equivalent flag forms of those three names.
- Every scaffolded file is stamped with the current squads version, as an HTML comment in a template
  and a TOML comment in a role, role catalog, workflow or playbook override.
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

# Diff the role catalog override against the current bundled catalog
sq override diff roles

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

# Re-stamp the role catalog override
sq override update roles

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

- **Name:** template path, role slug, `workflow`, `playbook`, or `roles` (e.g.,
  `items/task.md.j2`, `architect`).
- **Kind:** `template`, `role`, `workflow`, `playbook`, or `roles`.
- **Base version:** the `squads_version` the override was branched from (from the stamp), or
  `(unstamped)` for an override that has no stamp.
- **State:** 
  - `current` — the bundled counterpart hasn't changed since the base stamp.
  - `drifted` — the bundled counterpart changed and you should reconcile via `sq override diff` +
    hand-merge + `sq override update`. An unstamped override is listed as `drifted` too; for an
    add-only workflow or role catalog override, which needs no stamp, `sq check` stays clean.
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
`--name` or from the configuration (see [Which name wins](#which-name-wins)), never from this
table.

**Interactive prompting (at a TTY):**

When you run `sq init` at an interactive terminal without supplying all names, squads prompts you:

```
Enter full name for architect: 
```

Pre-answer these prompts with flags or `[init.names]` so you're never blocked.

**Skip prompting entirely:**

```bash
sq init --default-names    # uses the configured names for all roles
```

This is useful in CI or scripts where you can't interact. **Non-TTY environments (pipes, scripts,
CI) always behave as if `--default-names` is set** — you'll never hit a prompt.

**Fallback:**

Any role not named via a flag, config, or prompt takes the name the configuration gives it: a
`full_name` in its per-slug override file, else in `roles.toml`, else the bundled name (bundled
roles) or a name from the dev pool (developer roles).

### Naming roles after init

When you activate a new role or add a developer, you can provide a name then:

```bash
# Activate a bundled role with a custom name
sq role activate architect --name "Chief Designer"

# Add a Python developer with a custom name
sq dev add --tech python --name "Pythonista"
```

Omit the name and the role takes the name the configuration gives it, as at `init`.

`--name` only applies while the role is being created. Activating a role that is already live is a
no-op that returns the existing entry untouched — it reports success, and a `--name` you passed
with it does nothing. To rename a live role, see [Which name wins](#which-name-wins) below.

### How names flow into your squad

The name is stored as the ROLE item's `title`. Everything downstream reads from there:

- The **Agent roster** in your `CLAUDE.md` (generated by `sq sync`).
- The **agent pointer files** in `.claude/` (e.g., `.claude/agents/architect.md`).
- The heading of `sq role <slug> show`.

### Which name wins

A role's name is decided once, when the role is created, and stored. At creation the first of
these that applies wins:

1. **A name you give:** `--name` on `sq role activate` or `sq dev add`, or at `sq init` a `--name`
   flag, the `[init.names]` table or the prompt.
2. **`full_name` in `.overrides/roles/<slug>.toml`.**
3. **`full_name` in `.overrides/roles.toml`.**
4. **The bundled catalog's name**, or for a developer a name picked from the pool (a first name
   followed by the tech).

**After that, the stored name is the role's name.** No configuration change renames an active
role: a `full_name` added to or changed in either override file, or a squads release that changes
a bundled name, names the roles created after it and leaves the ones you have alone. `sq sync`
never changes a name, and the upgrade to a new squads version keeps every stored name.

**What `sq sync` keeps, and what it refreshes.** The name is kept. So is a developer's `--model`,
the other field `sq dev add` lets you choose. Everything else in a role's definition — its title,
mission, responsibilities, spawn authority, a bundled role's model, its preloaded skills — is
refreshed from the bundled definition (or from your override) on every sync, so an improvement
squads ships reaches a role you activated long ago.

**Renaming an active role** sets its stored `title` with an `update` event of `sq import`. Take the
role's ID from `sq list -t role`:

```bash
echo '{"op": "update", "target": "ROLE-<n>", "title": "Chief Designer"}' | sq import - --as manager
sq sync
```

The rename moves the role's `updated_at` and shows up in `sq reflog` as an update carrying the old
and new names. `sq sync` then regenerates the role's pointer and the `CLAUDE.md` roster from it.
The slug does not change (see below), and comments the role wrote earlier keep the name they were
written under.

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

Edit `.overrides/templates/items/task.md.j2` to add your sections, keeping every marker region the
bundled template carries: `sq:body`, the subtask container rendered from `open_marker` /
`close_marker`, and `sq:discussion`. Putting the new sections inside `sq:body` makes them the
starting text of every new task's body:

```jinja2
<!-- squads:override-base:<version> -->
<!-- sq:body -->
## Description

_TODO: describe this task._

## Success criteria

_Write the criteria for completion here._

## Dependencies

- [ ] Upstream requirement 1
- [ ] Upstream requirement 2
<!-- sq:body:end -->

{% set kind = spec.item_subentity_kind(item.type) %}
{% set tag = spec.subentity_plural(kind) %}
## {{ spec.subentity_container_heading(kind) }}

{{ tag | open_marker }}
{{ tag | close_marker }}

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
```

Keep the stamp line `sq override scaffold` wrote. Every task created after that starts from your
template; tasks already on disk keep the body they have.

### Override a role's name and model

You want the architect role to use a faster model for everyday work, and you want to call them
"Design Lead." Override the role before you activate it:

```bash
sq override scaffold --role architect
```

Edit `.overrides/roles/architect.toml`:

```toml
full_name = "Design Lead"
model = "haiku"
```

The rest of the architect's definition (title, mission, responsibilities) stays the same. Run
`sq role activate architect`: the new role is named "Design Lead" and runs on `haiku`. If the
architect is already active, `sq sync` applies the model and leaves the stored name as it is;
rename it as [Which name wins](#which-name-wins) shows.

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
and responsibilities are untouched, because the file didn't mention them. A `full_name` in the
same file would not rename them either: it names a developer only when one is added.

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
(the `.squads.toml` found by walking up from where `sq` runs, or from the folder `-C` names).

**Q: What if I want to add a *new* field to a role that isn't in the bundled definition?**

You can't. A role override accepts a fixed set of keys, and an unknown one is refused by name,
with the accepted set:

```
favourite_colour: unknown top-level key 'favourite_colour' — use one of the accepted top-level keys
in v<version>: ['agreements', 'can_spawn', 'color', 'description', 'full_name', 'is_default',
'mission', 'model', 'responsibilities', 'selected', 'slug', 'title']
```

`sq check` reports it as an error, `sq role <slug> show` refuses, and so does `sq sync` once the
role is on the roster. Nothing passes an unknown field through to a template. For a field squads
*does* recognise (like `model`), set it in the override and run `sq sync`. To store a key of your
own on each role item instead, declare it as an attribute of the `role` type in
`.overrides/workflow.toml` (see [Attributes](#attributes-the-keys-a-type-stores)). `sq role` has
no `update` verb, so set it with an `update` event of `sq import`:
`echo '{"op": "update", "target": "ROLE-<n>", "fields": {"<key>": "<value>"}}' | sq import - --as <slug>`.
