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
  transforms/
    progress.py               # a view transform: any path a view's `transform` names
```

**Key points:**

- **`templates/`** mirrors the bundled `_rendering/templates/` tree exactly. An override is named by
  its **template path** (e.g., `items/task.md.j2`, `agents/role.md.j2`). You don't override
  everything — drop a single file and only that template changes; the rest still use the bundle.
- **`roles/`** holds TOML files for role data: one file per role slug (e.g., `architect.toml`). A
  per-slug file is a layer over a role that exists, a catalog role, a role built from a template or
  a role that defines itself, and changes its fields (like the architect's title or model). It
  never creates a role: a custom role is created with `sq role add` (see
  [roles.md § "Custom roles"](roles.md#custom-roles-sq-role-add)), and a file for a slug with no
  role under it is a `sq check` error.
- **`roles.toml`** is your squad's delta on the **role catalog** as one document: the roles
  themselves, the role templates, the named bundles and the roster defaults (see
  [The role catalog override](#the-role-catalog-override-rolestoml)).
- **`workflow.toml`** is your squad's vocabulary delta — item types, statuses, lifecycles, and badge
  collections (see below). It can add to the bundled vocabulary, shadow a bundled entry field by
  field, and drop one you don't want.
- **`playbook.toml`** is your squad's delta on the **team playbook**: which roles interact with each
  item type, and the guidance each of them reads before touching one (see
  [Playbook overrides](#playbook-overrides-role-guidance-per-item-type)). It is what your generated
  `sq-<type>` skills are compiled from.
- **Transform files** are Python files a view's `transform = { path = … }` names, relative to
  `.overrides/` (`transforms/` is a convention, not a requirement). They are code that sq runs:
  see [Giving a view a transform](#giving-a-view-a-transform).
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

A list field such as `responsibilities` or `agreements` is replaced whole when you set it. To add
to the bundled list instead, open yours with the `$(*self)` splat-ref, which keeps every bundled
entry and goes on tracking the bundle across upgrades:

```toml
# .overrides/roles/architect.toml
# squads:override-base:<version>
responsibilities = ["$(*self)", "Keep the decision index current"]
```

`sq role architect show` then lists the bundled responsibilities followed by the new one. The same
line works in a `[[roles]]` entry of `roles.toml`. `sq override scaffold --role architect` writes
the stamp and this line, commented out. The deep merge, plain-array and splat-ref rules are those
of [The override grammar](#the-override-grammar-shadow-append-and-drop).

`full_name`, the role's name, is the one field that applies only once: it names the role when the
role is created. See [Which name wins](#which-name-wins).

**A per-slug file is a layer over a role that exists.** It merges over whichever base the role
has: its catalog entry, the template it was built from, or the definition a role created with
`sq role add` stores. Everything that reads a role resolves it that way: `sq sync`,
`sq role <slug> show`, `sq check`. The values the role item stores (its name, default-role
designation, `model` and `pronouns`) are applied after the file, so they win over it.

For a developer, add the role first. `sq dev add --tech <tech>` takes `--name`, `--model`, `--slug`
and `--pronouns`, and that is all most developers need. Write an override only for what those
flags do not set:

```bash
sq dev add --tech go --name "Gina Go" --model sonnet
sq override scaffold --role go-dev
```

```toml
# .overrides/roles/go-dev.toml
# squads:override-base:<version>
title = "Senior Go developer"
# mission, responsibilities, etc. keep following the dev template
```

After `sq sync`, `sq role go-dev show` opens with:

```
│ Gina Go (`go-dev`)                                                           │
│ title: Senior Go developer                                                   │
```

Two rules follow from that layering:

- **Fields you omit keep the base's values.** A file that sets only `title` changes only the
  title; the rest goes on following the template, so a change to `[templates.dev]` still reaches
  this developer.
- **A field you declare wins, except the stored ones.** `full_name` names a role only when the file
  is present at the moment the role is created, and never renames a role you already have; a
  stored `model` wins over the file's `model`.

**A file for a slug with no role under it is an error.** With no role item and no catalog entry
for its slug, the file has nothing to layer over, whether it is partial or complete. `sq check`
reports it (exit `3`):

```
error .overrides/roles/rust-dev.toml: role override has no role under it: no role item and no catalog entry for 'rust-dev' — create the role first, or `sq role add rust-dev --file squads/.overrides/roles/rust-dev.toml`
```

Create the role, and the file becomes its layer: `sq dev add --tech rust` for a developer (a
`full_name` in the file then names it, unless `--name` is given), or `sq role add <slug> --file
<path>` for a role that defines itself; the remedy prints the file's path relative to the directory
you run `sq` in. A file passed to
`sq role add` has done its job once the role exists: its definition is stored on the role, so
delete the file, or `sq check` warns under `role_definition_shadowed` that it shadows what the role
stores:

```
warn ROLE-23: .overrides/roles/auditor.toml sets capabilities, color, description, mission, responsibilities, title, which role 'auditor' stores in its item: the file wins, so `sq role auditor update` of those fields has no effect — delete the file or those keys
```

`sq role activate <slug>` for a slug that only a per-slug file declares exits `1` and names
`sq role add`:

```
error: role 'auditor' is declared only by .overrides/roles/auditor.toml, which layers over a role and does not define one; create the role with `sq role add auditor --file squads/.overrides/roles/auditor.toml`
```

**The workflow override merges by field too, and can also drop:**
`workflow.toml` composes over the bundled vocabulary the same way — write the fields you want
changed, inherit the rest, and use a `[selected]` list to remove a built-in entirely. See
[The override grammar](#the-override-grammar-shadow-append-and-drop).

**A custom role is not an override.** A role no catalog declares, such as a `security-analyst` or a
`compliance-officer`, is created with `sq role add`, which stores its definition on the role item;
nothing under `.overrides/` is needed. See
[roles.md § "Custom roles: `sq role add`"](roles.md#custom-roles-sq-role-add). It is a developer
only if it holds a capability the `dev` template declares (see
[roles.md § "Capabilities"](roles.md#capabilities)).

### The role catalog override: `roles.toml`

A per-slug file changes one role. **`.overrides/roles.toml`** is the whole role catalog as one
document, the same catalog `sq role catalog` lists, and it also reaches the parts no per-slug file
can: the role templates and the named bundles. Start it from a stamped, commented example:

```bash
sq override scaffold roles      # or: sq override scaffold --roles-catalog
```

The document's top-level keys are `roles`, `templates`, `bundles`, `defaults` and `selected`. Any
other is refused by name.

- **`[[roles]]`** — one entry per role, keyed by its `slug`. An entry naming a bundled slug merges
  field by field onto it, so you write only what changes. An entry naming a new slug declares a new
  catalog role, and then `full_name`, `title`, `description` and `mission` are required. An entry
  may declare `capabilities` (see [roles.md § "Capabilities"](roles.md#capabilities)).
- **`[templates.<name>]`** — a role template (see
  [roles.md § "Role templates"](roles.md#role-templates)). A table naming a bundled template, such
  as `dev`, merges field by field onto it; a new name declares a new template. Every field of a
  template reaches the roles already built from it on the next `sq sync`, except a role's stored
  name and a `model` the role stores.
- **`[bundles]`** — the named role lists (`all`, `core`, `minimal`). The `all` bundle must name
  every role in the catalog, so a role you add here has to join it too.
- **`[defaults]`** — roster-wide defaults; see below.

```toml
# .overrides/roles.toml
# squads:override-base:<version>

[templates.dev]
model = "opus"
name_pool = ["Hedy", "Katherine", "Frances"]
responsibilities = ["$(*self)", "Run the {Tech} linters"]

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

With that file, the architect is retitled, every developer gains a responsibility and runs on
`opus` unless it stores a model of its own, the next `sq dev add` picks a name from the new pool,
and `security-analyst` appears in `sq role catalog` as a project role, ready for
`sq role activate security-analyst`.

A `[dev]` table is not a key of the catalog: the developer template is `[templates.dev]`, and a
file that still carries `[dev]` stops every role command:

```
error: .overrides/roles.toml: [dev] is not a key of the role catalog; rename it to [templates.dev] (its name_pool, model, color and capabilities keys are unchanged)
```

**A roster-wide pronouns default.** A `[defaults]` table in `roles.toml` takes one key,
`pronouns`, applied to every role with no pronouns of its own, never to an operator, and never
written onto an item; run `sq sync` after changing it. A role's own pronouns are set with
`sq role <slug> update --pronouns`, not in the catalog: a `pronouns` key in a `[[roles]]` entry or
a per-slug file is refused. See [roles.md § "Pronouns"](roles.md#pronouns).

**Precedence, lowest to highest:** the bundled catalog, then `roles.toml`, then a per-slug
`.overrides/roles/<slug>.toml`, then the values the role item stores. When both override files set
the same field for one role, the per-slug file wins. For `full_name` the order decides only the name a role gets when it is
created: an active role keeps the name it stores, whatever either file says later (see
[Which name wins](#which-name-wins)).

**Dropping a role or a template** goes through `[selected]`: `roles` lists the roles that
survive and `templates` the templates that do. A role already built from a dropped template, or
activated from a dropped entry, stays on the roster and `sq check` reports it under
`role_base_resolves`. A bundle that still names a dropped role is refused, naming the bundle:

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

A dropped role cannot be activated, and a dropped template cannot build one. A
file that only adds, such as a new bundle or a new template, needs no stamp. One that changes a
bundled role, a bundled bundle or a bundled template must carry the
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
`[roles.*]`, `[ref_kinds.*]` and `[views.*]`, plus the single `[squad]` and `[selected]` tables —
and anything else at the top level is refused by name at load time:

```
item: unknown top-level key 'item' — use one of the accepted top-level keys in v<version>:
['collections', 'items', 'lifecycles', 'ref_kinds', 'roles', 'selected', 'squad', 'statuses',
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
  `sq import` write it. A key a dedicated command owns is declared `settable = false`. The
  `update` verb of a role, skill or operator takes no `--set`, so their attributes are set with an
  `update` event of `sq import`. On a role and on a generated skill, that event is refused for an
  attribute the bundled spec declares, and accepted for one your override declares (see
  [roles.md § "What a generated role or skill refuses"](roles.md#what-a-generated-role-or-skill-refuses)).
  A role's definition comes from the role catalog and its overrides: its `model`, a developer's
  included, is set in `.overrides/roles/<slug>.toml` or `roles.toml`, and `sq sync` writes a
  developer's onto its role item, the value it runs on.
- `label` (optional): the name `sq <type> <n> show` prints the attribute under. A labelled
  attribute that an item stores is shown as one line of the header, in declared order, and on
  `show --json` as an entry of `display.attributes`, `{key, label, value}`. An attribute without a
  label is not shown. The bundled milestone declares
  `target_date = { kind = "date", label = "target date" }`.

`sq workflow types --json` lists each type's attributes with their `kind`, `required`,
`settable` and `label` (`null` when absent). The bundled spec declares `target_date` on `milestone`, `target_ref` on `review`,
`tags` and `tech` on `guide`, `is_default`, `model` and `tech` on `role`, and
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
`discussion`, `display`, `matched_subentities`, `views`), or `extra`, `path` or `prefix`, and a
badge field cannot take the name of a key `--json` adds either:

```
- 'guide': attribute 'title' is a reserved frontmatter key — rename the attribute in the workflow override and in the items that store it
- 'task': attribute 'display' is a reserved key every --json item row adds — rename the attribute in the workflow override and in the items that store it
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
through `sq repair`, with their values. No command removes a key it was not asked to change, with
one exception: on a role, `sq repair` removes the retired role keys `full_name`, `skills` and
`is_dev`, unless the `role` type declares them as attributes (see
[adoption.md § "What `sq repair` writes"](adoption.md#what-sq-repair-writes)).

A key you add by hand puts the file ahead of the index, as any hand edit does: run `sq repair`
before the next write to that item, which is refused until then with a message naming
`sq repair`. `sq check` reports the drift meanwhile, and reports the key itself once it is
indexed.
`--json` item rows carry them too, at the top level beside the core keys, except a key named like
one `--json` adds (`badges`, `body`, `discussion`, `matched_subentities`, `views`), which stays in
the file and out of the row. A value is kept in the form JSON can carry: a YAML-only value is written back
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
type gets the checks that are always on plus the checks on by default for its `category`, and a type's own
`validators` list is where you **add** to it and say how much you mean each addition. A check that
looks at the squad as a whole sits outside every type's list: some always run, and the others are
selected in the `[squad]` table (see "Squad-wide checks" below).

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
- Eight policy checks about the work an item tracks: `item_title_max`, `external_id_not_in_title`,
  `description_present`, `assignee_present`, `body_written`, `settled_requires_discussion`,
  `ref_rule_target_typed` and `blocked_has_blocker`. See "The work-policy checks" below.

One more sits in no category's defaults but is selected on one bundled type:
`subentities_settled_with_parent`, on `review`. See "The settled-parent check" below.

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

**The settled-parent check.** `subentities_settled_with_parent` reports an item resting at a
status whose role declares `settled = true` while any of its sub-entities rests at a status whose
role does not. It names the count and the local ids, once per item:

```
warn REV-<n>: status is Approved with 2 unsettled findings: <k>, <k>
```

Both sides are read from the status role, never from a status name. With the bundled vocabulary,
an `Approved` or `Rejected` review is reported while a finding is `Open` or `Fixed`: a fixed
finding still waits for its verification. A `Verified`, `WontFix`, `Noted` or `Deferred` finding
is settled. A review that is not settled yet, `InReview` for one, is never reported. The check
takes no parameter.

At its bundled `warn` level it refuses no move: approving a review with an open finding goes
through, and `sq check` reports it afterwards. Selected at `@error`, it gates the move instead,
`--force` included, so the sub-entities have to settle first:

```
error: status is Done with 1 unsettled story: <k>
```

The bundled spec selects it on `review` and nowhere else, so an override that writes
`[items.review] validators` must open with `"$(*items.review.validators)"` to keep it (see "a
type's own list is an ordinary array" below). Any type that hosts sub-entities can name it too,
a feature whose stories should be closed before it is, for one:

```toml
[items.feature]
validators = ["subentities_settled_with_parent"]
```

A type that hosts no sub-entity kind may name it and reports nothing.

**The work-policy checks.** Eight more checks hold an item to a team's habits about the work it
tracks. The bundled spec selects none of them, so a squad that names none sees no finding from
them, and nothing needs migrating. Each reports at `warn` unless you name a level, and each applies
to `work` and `records` types only.

Two are about titles:

- **`item_title_max:<n>`**, for a team that keeps titles to a one-line handle. It reports an item
  whose title is longer than `n` characters. Characters are counted after Unicode normalisation
  (NFC): an accented letter typed as two code points counts as one, while an emoji sequence joined
  by zero-width joiners counts as several. A retitle to `n` characters or fewer clears it.
- **`external_id_not_in_title:<regex>`**, for a team that keeps tracker ids out of titles. It
  reports an item whose title matches your regular expression anywhere, and names the first match.
  A retitle that no longer matches clears it. Read the warning about the pattern below before you
  write one.

Two are about content:

- **`body_written`**, for a team that wants every item described. It reports an item whose body is
  still the scaffold its template rendered. Writing the body clears it.
- **`description_present`**, for a team that reads the summary in listings. It reports an item
  whose summary (`--desc`) is empty or whitespace only. `update --desc` clears it.

Two are about status:

- **`assignee_present`**, for a team where work under way always has an owner. It reports an item
  resting at a status whose role declares `live = true` with nobody assigned. `update --assignee`
  clears it.
- **`settled_requires_discussion`**, for a team that records why work closed. It reports an item
  resting at a status whose role declares `settled = true` while its own discussion holds no
  comment. A comment on one of its stories, subtasks or findings does not count; one `comment` on
  the item clears it.

Two are about refs:

- **`blocked_has_blocker`**, for a team that wants a blocked item to say what it waits on. It
  reports an item resting at a status whose role declares `blocked = true` while no dependency edge
  touches it in either direction: neither a ref of its own of a dependency kind, nor one from
  another item pointing at it. A kind counts by its `dependency` role, never by its name, and an
  edge counts whatever the status of the item at its other end. `ref add` of a dependency edge, on
  either item, or a status move clears it.
- **`ref_rule_target_typed`**, for a team that wants a typed edge to point where its rule says. It
  reports each edge whose kind has a `ref_rules` entry with a `target` on the item's type, when the
  edge points at an item of another type. Only rules that declare a `target` are read, and a ref
  written without a kind is read as the spec's default kind. An edge to an item that does not
  exist is left to the dangling-ref check. The bundled feature's `implements` rule is one, so an
  `implements` edge from a feature to a task is reported. `ref rm` of the edge clears it.

"Live", "settled" and "blocked" are flags a status role declares, never a role name or a status
name: `sq workflow roles` shows them, and "Status roles" below says how to declare them.

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

Moving it to `InProgress` with no assignee adds `status is InProgress but nobody is assigned`. The
other four checks report:

```
warn TASK-<n>: body is unwritten (still the template scaffold) — write it with `sq task <n> body -m "..."`
warn TASK-<n>: status is Done but its discussion holds no comment
warn TASK-<n>: status is Blocked but no dependency edge is recorded (kinds: blocks, depends-on) — record a dependency edge (`--ref <id>:<kind>` on create, `ref add` after)
warn FEAT-<n>: implements edge to TASK-<m> points at a task, but a feature's implements refs must point at a contract
```

**A worked example: titles and bodies on two types.** This selects a 120-character title limit and
written bodies on features and epics. `epic` ships a `validators` list of its own (`no_parent`), so
its line opens with the splat that keeps it:

```toml
[items.feature]
validators = ["item_title_max:120", "body_written"]

[items.epic]
validators = ["$(*items.epic.validators)", "item_title_max:120", "body_written"]
```

A feature with a 144-character title and an epic, both just created, are then reported:

```
warn FEAT-<n>: body is unwritten (still the template scaffold) — write it with `sq feature <n> body -m "..."`
warn FEAT-<n>: title is 144 chars (threshold: 120) — an item title is a one-line handle; put the detail in the body
warn EPIC-<m>: body is unwritten (still the template scaffold) — write it with `sq epic <m> body -m "..."`
```

Tasks and every other type report nothing, and with the two lines taken out `sq check` prints
`✓ no issues`. Without the splat the epic line still loads, but it drops `no_parent`, and epics
start accepting a parent with no warning.

`body_written` compares the body with the scaffold the item's template renders when `sq check`
runs. An item whose scaffold has changed since it was created no longer equals it and reads as
written: an item created before you edited its template override, or one whose scaffold
interpolates a field that has changed since, such as a review's target. Items created after the
edit are compared with the new scaffold.

**Where they apply.** The eight apply to `work` and `records` types and never to a role, skill or
operator. Naming one on `role`, `skill` or `operator` is refused at load:

```
item 'role': validators entry 'item_title_max:80' cannot apply to a roster type — item_title_max is
a policy about tracked work and applies to 'work' and 'records' types only; drop the entry
```

**A selection that can never fire is refused at load**, by every command and by
`sq workflow lint`, naming the type and what it lacks. Only the spec is read, never the items:

- `ref_rule_target_typed` on a type with no `ref_rules` entry that declares a `target`. Give the
  type such a rule, or drop the entry. Under the bundled spec only `feature` has one. A rule whose
  target type you drop through `[selected]` goes with it, so the same refusal follows:

  ```
  item 'task': validators entry 'ref_rule_target_typed' needs a ref_rules entry with a target, and
  'task' declares none (a rule whose target type was dropped through [selected] is removed with
  it) — declare { kind = ..., target = ... } in its ref_rules, or drop the entry
  ```

- `assignee_present` on a type whose lifecycle holds no status of a role declaring `live = true`.
  Under the bundled spec that is `decision` and `guide`:

  ```
  item 'decision': validators entry 'assignee_present' needs a status of a role declaring live =
  true, and the lifecycle 'adr' of 'decision' holds none — without one it never fires; drop the
  entry or give the lifecycle a status of a live role
  ```

- `blocked_has_blocker` on a type whose lifecycle holds no status of a role declaring
  `blocked = true`. Under the bundled spec it loads on `epic`, `feature`, `task` and `bug`, and is
  refused on the other work and records types:

  ```
  item 'review': validators entry 'blocked_has_blocker' needs a status of a role declaring blocked
  = true, and the lifecycle 'review' of 'review' holds none — without one it never fires; drop the
  entry or give the lifecycle a status of a blocked role
  ```

- `blocked_has_blocker` in a spec that declares no ref kind with `role = "dependency"`, which is
  what dropping `blocks` and `depends-on` through `[selected]` leaves:

  ```
  item 'task': validators entry 'blocked_has_blocker' needs a declared ref kind with role =
  "dependency", and the spec declares none — without one no edge can satisfy it; drop the entry or
  declare a dependency ref kind
  ```

**The two parameters are required.** Either name written bare, or with nothing after the colon, is
refused, the same way `ref_rule_target_present` is:

```
item 'feature': validators entry 'item_title_max' is missing its required parameter — name it as
'item_title_max:<n>', or drop the validator; without a parameter it never fires
```

`item_title_max` takes a positive integer, read the way `subentity_title_max` reads its own:

```
item 'task': validators entry 'item_title_max:0' names a non-positive-integer item_title_max
threshold '0'
```

`external_id_not_in_title` takes a Python regular expression, searched for anywhere in the title
with no flags: write `(?i)` at its start to ignore letter case, and use one alternation for several
trackers (`(?:JIRA|OPS)-[0-9]+`), since the check can be named only once per type. Everything after
the first colon is the pattern. Write the entry as a TOML literal string, in single quotes, which
keeps every backslash as written: `'external_id_not_in_title:[A-Z]+-\d+'`. In double quotes a single
backslash stops every command before the spec is read:

```
Malformed workflow override <path>: Unescaped '\' in a string (at line 3, column 50)
```

The pattern is compiled at load, and refused when it does not compile, when it matches the empty
string (it would report every title), or when it compiles with a warning:

```
item 'task': validators entry 'external_id_not_in_title:[abc' names an invalid regular expression
'[abc': unterminated character set at position 0
item 'task': validators entry 'external_id_not_in_title:x*' names a regular expression 'x*' that
matches the empty string, so it would report every title — make it require a character
item 'task': validators entry 'external_id_not_in_title:[[a]]' names a regular expression '[[a]]'
that compiles with a warning: Possible nested set — rewrite it
```

A pattern cannot contain a literal `@`, because `@` starts the level. Write it as `\x40`:
`'external_id_not_in_title:me\x40corp'`. An entry such as `external_id_not_in_title:foo@warn` is
the pattern `foo` at `warn`; any other text after the `@` is refused:

```
item 'task': validators entry 'external_id_not_in_title:user@host' reads 'host' as its level — '@'
separates the pattern from the level ('error' or 'warn') and cannot appear in the pattern; write a
literal '@' as \x40
```

**A warning about the pattern: nothing bounds a match.** squads sets no time limit on it. The
pattern runs on every `sq check`, for each item of a type that selects it; on `sq import`, at any
level, for each item the import wrote, once the import is written; and on a create or update of
such an item only when its type selects the check at `@error`, where the write holds the squad's
index lock while the pattern runs. A pattern that backtracks, such as `(a+)+$` against a title of
thirty `a`s and a `!`, can therefore hang `sq check`, an import, and, at `@error`, the write. Keep
the pattern to literal text and character classes, with no repetition nested inside another.

**What `@error` does for each.** Six of the eight take part in the create/update gate, so at
`error` they refuse a write, with the finding as the error and nothing written:

| Check | Refused at `@error` | The way out |
|---|---|---|
| `item_title_max` | a create or retitle over the number | a title of `n` characters or fewer |
| `external_id_not_in_title` | a create or retitle that matches | a title that does not match |
| `description_present` | a create without `--desc`, and `update --desc ""` | `--desc` on create, `update --desc` after |
| `assignee_present` | a move to a live status with nobody assigned | `update --assignee` first, or `update --status <S> --assignee <slug>` in one command |
| `blocked_has_blocker` | a move to a blocked status with no dependency edge | `ref add` of a dependency edge before the move |
| `ref_rule_target_typed` | a create with a misdirected `--ref` | `ref rm` of the edge |

As with every gating check, an item that already fails one has its next `update` or `status`
refused, whatever that command changes, until the finding is cleared. `ref add` and `ref rm` are not
gated: under `ref_rule_target_typed@error` a misdirected edge is still added, and the refusal lands
on the item's next update; removing an item's last dependency edge at a blocked status is accepted,
and `sq check` then reports it. An import is checked event by event the same way before anything is
written, and a refused event writes nothing.

The other two, `body_written` and `settled_requires_discussion`, read the item's file, so at `error`
they make `sq check` exit `3` and refuse no write: the move to `Done` goes through, and the finding
is in the next report. An import that leaves such a finding is applied and exits `3`.

A check selected at `warn` is not evaluated on a create or update at all. It runs in `sq check` and
on the items an import wrote.

**Selection is per type.** A line under `[items.feature]` changes nothing for a task, a decision
or any other type: a squad that wants one of these checks everywhere names it on each type. (The
`[squad]` table selects the squad-wide checks only; a per-item check named there is refused.)
Three bundled types, `epic`, `review` and `skill`, ship a `validators` list of their own, and there
the entry has to be added to the bundled list, not written over it — see "a type's own list is an ordinary
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

The gate also runs only what can refuse: a check a type selects at `warn` is not evaluated on a
create or update, whatever it reads.

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
item 'feature': validators entry 'ref_rule_target_present' is missing its required parameter —
name it as 'ref_rule_target_present:<type>', or drop the validator; without a parameter it never
fires
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
section, and neither the always-on checks nor the checks on by default for a category can be subtracted from. The
quietest a bundled check can be made is `warn`, which still reports. The opt-in checks
are on by default for no category, so a type that does not name one does not run it.

**But a type's own list is an ordinary array, and arrays are leaves** (see § "Plain arrays are
leaves — replaced whole"). Three bundled types ship a `validators` entry of their own, `epic`
(`["no_parent"]`), `review` (`["subentities_settled_with_parent"]`) and `skill`
(`["item_skill_shadowed"]`), and writing the key in your override replaces the whole list rather
than adding to it. This turns the status-banner check on for epics
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

The same goes for `review`. Written plain, `validators = ["no_status_banner"]` under
`[items.review]` drops `subentities_settled_with_parent`, and an approved review holding an open
finding stops being reported. Open the list with the splat:

```toml
[items.review]
validators = ["$(*items.review.validators)", "no_status_banner"]
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

#### Squad-wide checks: the `[squad]` table

Some checks look at the squad as a whole rather than at one item. They run once per `sq check`,
never at the create/update gate, and they belong to no type's list.

**Always on.** Eleven report a defect in any squad, so they run in every squad and cannot be selected,
dropped or given another level:

| Check | Reports | Level |
|---|---|---|
| `index_reconciled` | the index and the item files disagree | `error` |
| `backend_reconciled` | an active agent backend's managed files are missing | `error` |
| `roster_config_integrity` | a roster with no live role left, or a live role that preloads a retired skill | `error` |
| `default_designation_duplicated` | more than one live role holds the default-role designation | `error` |
| `roster_slug_valid` | a role or operator slug that breaks the slug rules (see [stability.md § "Comment headers"](stability.md#comment-headers)) | `error` |
| `playbook_guide_role_live` | a playbook guide that names no live role, including a slug no role holds | `warn` |
| `role_base_resolves` | a live role whose base does not resolve: a catalog role whose slug the catalog does not declare, a template role naming an undeclared template or missing (or carrying) the `tech` its template takes, a role that defines itself without a job title or description, or one storing both `template` and `mission` (see [roles.md § "Where a role's definition comes from"](roles.md#where-a-roles-definition-comes-from)) | `error` |
| `role_definition_shadowed` | a per-slug role file that sets a field the role stores in its item, so `sq role <slug> update` of that field has no effect | `warn` |
| `display_config_valid` | an unknown key or a non-boolean value in `.squads.toml`'s `[display]` table | `warn` |
| `working_language_valid` | a `working_language` in `.squads.toml` that is not a language tag squads recognises; English applies | `warn` |
| `view_transform_resolves` | an override view transform whose file is missing, leaves `.overrides/`, fails to import, or lacks a function sq can call; it imports the file, which runs its top-level code (see [Giving a view a transform](#giving-a-view-a-transform)) | `error` |

**Selectable.** Six run only when the `[squad]` table selects them. Its one key, `validators`,
takes the entry grammar a type's list takes (`name`, `name:param`, `name@level`,
`name:param@level`). The bundled list selects `type_has_live_author`, so it runs in every squad
whose override leaves the list alone. The other five state a policy a team may or may not hold,
and none of them runs until you name it. Each reports at `warn` unless you name a level:

| Check | Reports | Parameter |
|---|---|---|
| `type_has_live_author` (bundled) | a type outside the roster holding an item at a status that is not settled, with no live role that has an `authors = true` playbook guide on it, once per type; it names the role to activate or reactivate, or says to add a developer (see [Playbook overrides](#playbook-overrides-role-guidance-per-item-type)) | none |
| `children_settled_with_parent` | a parent at a settled status with a child at a status that is not settled, once per parent | none |
| `dependency_acyclic` | each cycle of dependency edges, once, with a path around it | none |
| `wip_limit:<n>` | each assignee holding more than `n` active items | required, at least `1` |
| `unassigned_active:<n>` | more than `n` active items with no assignee, in one finding | required, at least `0` |
| `stale_active:<days>` | each active item last updated more than `days` days ago | required, at least `1` |

```toml
[squad]
validators = [
  "$(*squad.validators)",
  "children_settled_with_parent",
  "dependency_acyclic@error",
  "wip_limit:3",
  "unassigned_active:0",
  "stale_active:14",
]
```

What the words in that table mean, read from your vocabulary and never from a name:

- **Active** is an item of a `work`-category type resting at a status whose role declares
  `live = true` (`sq workflow roles`). A roster entry, a `records` item and an item at a status of
  a non-live role are never active.
- **Settled** is the status role's `settled` flag. A child is an item whose `parent` is the item;
  sub-entities are not children. Any parent type counts.
- **A dependency edge** is a ref whose kind declares the dependency role, read in its declared
  direction, so the two dependency kinds describe the same edge. Every other kind is ignored, and a
  cycle is reported whatever the status of its items.
- **The boundaries are strict.** `wip_limit:3` is clean at three active items and reports at four;
  `unassigned_active:0` reports a single unassigned active item; `stale_active:14` reports an item
  untouched for more than 14 days, measured against one instant read when the run starts.

On a squad with a settled feature, two open tasks under it that block each other, and one of them
unassigned, that selection reports:

```
warn: 1 active item has no assignee (limit 0): TASK-<n>
error: dependency cycle: TASK-<n> -> TASK-<m> -> TASK-<n>
warn FEAT-<k>: FEAT-<k> is Done with 2 open children: TASK-<n>, TASK-<m>
```

**`@error` changes only the exit code.** These checks never run at the gate, so at `error` a
finding makes `sq check` exit `3` and refuses no write: the `ref add` that closed the cycle above
went through.

**The list merges like any array.** An override's `validators` replaces the bundled list whole;
`"$(*squad.validators)"` keeps it and adds to it, which is why the example opens with it. Naming
`type_has_live_author` after the splat as well is refused as a repeat. `[selected]` has no `squad`
key: the table's one key is a list, so you replace the list instead.

**Turning `type_has_live_author` off** is a list that leaves it out. A squad whose types are
written by people rather than agents, or a squad started with `sq init --roles minimal` or
`core` that leaves some types to its default role, writes `validators = []`, or the checks it
wants without the splat, such as `validators = ["dependency_acyclic"]`.
To raise it, name it with the level in place of the splat, `"type_has_live_author@error"`:
`sq check` then exits `3` on a type with no live author, and no write is refused.

**What is refused at load**, each naming the entry, by every command and by `sq workflow lint`:

- a name that is not one of the six: an unknown name, an always-on one
  (`index_reconciled always runs and cannot be selected — drop the entry`), or a per-item check
  (`body_written is a per-item validator — name it on a type's validators list`). The reverse is
  refused too: a type's `validators` list naming one of the six is told to use `[squad]`
  (``type_has_live_author is a squad-global validator — select it in the `[squad]` table's
  `validators` list``);
- a parameter on a check that takes none, and a missing, non-integer or too-small one on a check
  that requires it (`wip_limit needs its parameter — write 'wip_limit:<n>'`,
  `wip_limit needs a positive integer parameter (got '0')`);
- a level other than `error` or `warn`;
- the same check twice, whatever the parameters or levels;
- a selection your vocabulary makes unable to fire: `wip_limit`, `unassigned_active` or
  `stale_active` when no `work` type's lifecycle holds a status of a live role, and
  `dependency_acyclic` when no ref kind declares the dependency role. Only the spec is read; the
  items are not.

#### Checks outside every list: files, ids, overrides and configuration

`sq check` also runs checks that belong to no `validators` list, neither a type's nor `[squad]`'s.
They run in every squad, at the level shown, and no override can select, drop or relevel them.
Each one reports damage, not a policy: content that `sq` cannot read or edit safely, or a
configuration it cannot load. Leaving one out would hide a broken squad, not tune a convention.

The file checks run once per item file and read the raw text, so they still report when the
frontmatter cannot be read:

| Rule | Reports | Level | Why it cannot be turned off |
|---|---|---|---|
| `markers_balanced` | an `sq:` marker with no end, an end with no start, an end before its start, or a marker repeated | `error` | every write `sq` makes edits between markers; with a broken pair it cannot tell where a region ends |
| `view_target_resolves` | an enabled view tag naming a view that is not declared, has no template, or cannot apply to the type | `error` | the tag can never render |
| `view_tag_in_region` | a view tag outside `sq:body` | `warn` | the tag can never render |
| `seeded_view_resolves` | a view the type seeds whose tag is missing, or a view tag repeated | `error` | the body no longer shows what the type generates there |
| `body_regions_present` | a file with no `sq:body` marker pair at all | `error` | there is no region left for `sq` to write the body into |
| `file_readable` | a file that cannot be read | `error` | nothing else can be checked on it |
| `frontmatter_parses` | frontmatter that is missing or is not valid YAML | `error` | the frontmatter is the item's record |
| `id_present` | frontmatter with no `id` | `error` | the id is how every command, ref and the index address the item |
| `id_well_formed` | an `id` that `sq` cannot read a prefix and number from | `error` | the same |
| `fields_valid` | a frontmatter value of the wrong shape | `error` | the item cannot be loaded |
| `timestamps_present` | frontmatter missing `created_at` or `updated_at` | `warn` | a placeholder is invented on each read until a write fills it in |

The squad checks run once per `sq check`:

| Rule | Reports | Level | Why it cannot be turned off |
|---|---|---|---|
| `ids_unique` | two files carrying the same id | `error` | an id must address one item |
| `numbers_unique` | files carrying one number under different ids | `error` | one counter numbers every type, so a number is unique across the squad |
| `frontmatter_matches_index` | a field whose value in the file differs from the index | `warn` | the file is the source of truth; the next mutation would write the index's value back, so `sq repair` must run first |
| `override_stamped` | an override under `.overrides/` that shadows a bundled file and carries no `squads:override-base` stamp | `error` | without the stamp, `sq` cannot tell whether the bundled file changed under it |
| `override_current` | an override whose bundled base changed since the version it is stamped with | `warn` | the override may hide an upgrade's change; `sq override diff` shows it |
| `override_loads` | a template, role or role catalog override that cannot be read, lacks the markers a template needs, or does not load; a per-slug role file with no role under it | `error` | the overrides are the configuration every selection is read from |
| `skill_type_declared` | a live skill generated for an item type the workflow no longer declares | `warn` | its generated files have been withdrawn, so the skill points at nothing |

The configuration checks are reported by `sq check` itself when a document will not load. No
selection can reach them, since the selections live in the document that failed:

| Rule | Reports | Level |
|---|---|---|
| `workflow_loads` | the workflow spec, with its override, will not load; the message names the cause | `error` |
| `playbook_loads` | the playbook, with its override, will not load; the message names the cause | `error` |
| `corpus_scans` | the item files could not be scanned | `error` |

A workflow or playbook override that will not load is reported by these two rules, not by
`override_loads`. For an unknown validator name in `.overrides/workflow.toml`:

```json
{
  "level": "error",
  "item": "workflow",
  "message": "workflow config invalid: Invalid workflow spec: item 'task': validators entry 'nonesuch' names an unknown validator (<squad>/.overrides/workflow.toml) \u2014 run `sq workflow lint`",
  "rule": "workflow_loads"
}
```

Some validators are always on as well. Every type runs the common core (`item_status_valid`,
`dangling_ref`, `ref_kind_valid`, `agent_registered`, `parent_acyclic` and `attribute_valid`) and
the checks its `category` turns on: `parent_in`, `subentity_status_valid`,
`subentity_container_marker`, `subentity_body_written`, `subentity_title_present`,
`subentity_deferral_resolved` and
`subtask_story_mapping` for `work`; `no_parent` and `supersedes_incoming` for `records`;
`pronouns_valid` for `roster`. A type's `validators` list can change their level, within each
check's floor, but cannot drop them. Only the checks a type adds beyond them are selectable. The
eleven always-on squad-wide checks in the table above (`index_reconciled` and the others) cannot be
selected, dropped or relevelled at all.

**Every finding names its rule.** In `sq check --json`, each finding carries `rule`: the name of
the check that produced it. For a validator, per-item or squad-wide, it is the validator's name,
such as `dangling_ref`; for the checks above, it is the rule shown in their tables. On a squad with
a broken marker pair, two files carrying one id, and a ref to an item that does not exist:

```json
[
  {
    "level": "error",
    "item": "TASK-NNNNNN-write-the-exporter.md",
    "message": "unclosed marker <!-- sq:discussion -->",
    "rule": "markers_balanced"
  },
  {
    "level": "error",
    "item": "FEAT-<k>",
    "message": "2 files carry this id (features/FEAT-NNNNNN-export-reports-copy.md, features/FEAT-NNNNNN-export-reports.md); merge the content you want into one file, delete the other by hand, then run `sq repair`",
    "rule": "ids_unique"
  },
  {
    "level": "warn",
    "item": "TASK-<m>",
    "message": "dangling ref TASK-<x>",
    "rule": "dangling_ref"
  }
]
```

A file check names the file in `item`; the other checks name the item, or the source they read.
A tool that reads this output should match a finding by `rule`, never by `message`: the message
is written for people to read. The human output of `sq check` does not show the rule.

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
- `ordered` — required in practice: write `ordered = true`. A collection without it (the key
  defaults to `false`) is refused at load with `collection 'impact': unordered collections are not
  supported yet`. **Declare the badges strongest first** — rank follows declaration order, the way
  the bundled `priority` collection runs urgent → low
- `default` — optional; the badge code an item or sub-entity gets when it is created without a value
- `badges` — the badge definitions, each with `code`, `label` and `emoji`

A collection is a *library*; a type carries it by declaring a **field** bound to it. Add one to a
built-in type without disturbing its existing fields:

```toml
[items.task]
fields = ["$(*self)", { code = "impact", label = "Impact", collection = "impact" }]
```

Then, on any item of that type:

```bash
sq create task "…" --impact high        # set it at creation (one option per declared field)
sq task <n> update --set impact=high    # set it  (--unset impact clears it)
sq list --badge impact=high             # exact filter on any declared badge field
sq list --min-badge impact=medium       # threshold filter, ordered collections only
sq list --sort impact                   # sort by an ordered field's rank
```

The bundled `priority` axis has dedicated sugar for the same operations — `--priority` /
`--min-priority` — and every other badge field goes through `--set` / `--badge` / `--min-badge`.

A field can declare its own `default`, which wins over the collection's:
`{ code = "risk", label = "Risk", collection = "impact", default = "low" }`. `sq create` stores that
default for every declared field it is not given a value for; a field with no default on either
level stays unset. Items that already exist keep what they store.

**Where a field's badge shows.** A badge is shown only for a field the item's type declares, in
declared order. A line that leads with one badge, such as a `sq tree` or `sq graph` line, shows the
type's first declared field; the Priority column of `sq list` and `sq mine` shows the declared
`priority` field. A code an item stores under a field its type no longer declares stays in the
file and in the `--json` row's own key, and gets no badge: the tree line leads with the first
field the type still declares, or with no badge, and the table cell is empty.

An item field's `code` cannot be the name of a built-in `sq create` option: `author`, `parent`,
`desc`, `label`, `ref`, `assignee`, `message`, `file`, `json` or `help`. Such a field is refused
when the spec loads, so every command stops with
``items.task field[2]: code 'label' is also a built-in `sq create` option (--label); declare the field under another code``
until you rename it. Values items already store under the old code are not moved to the new one.

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
- **`blocked`** — whether an item resting at this status is waiting on something else. It defaults
  to `false`, and the bundled `blocked` role is the only bundled role that declares it. Only the
  `blocked_has_blocker` check reads it (see "Validators" above); `sq blocked` and the `blocked` key
  of `sq tree --json` come from dependency edges, not from this flag. It takes `true` or `false`
  and nothing else:

  ```
  Invalid role 'blocked': blocked must be true or false, got 'yes'
  ```

- **`deferred`** — whether a sub-entity resting at this status has handed its work to another
  item, which it names with `--deferred-to`. It defaults to `false`, takes `true` or `false` and
  nothing else, and the bundled `deferred` role is the only bundled role that declares it. A move
  into such a status is refused without a carrier, and the `subentity_deferral_resolved` check
  verifies the carrier (see [workflow.md](workflow.md#closing-a-finding-as-noted-or-deferred)
  § "Closing a finding as Noted or Deferred"). Only a sub-entity lifecycle may reach a status of
  such a role; an item lifecycle that does is refused at load:

  ```
  item 'bug': lifecycle 'bug' reaches ['Deferred'] whose role declares deferred = true — only a
  sub-entity lifecycle may; use a ref to name a carrier or give the status another role
  ```

  A status of your own gets the behaviour by naming such a role, whatever the status is called:

  ```toml
  [roles.later]
  settled = true
  hidden = true
  color = "info"
  deferred = true

  [statuses.Postponed]
  role = "later"

  [lifecycles.finding.transitions]
  Open = ["Fixed", "WontFix", "Noted", "Deferred", "Postponed"]
  ```

Squads ships with nine bundled roles covering common patterns. You can reference them in your
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

| Role | `settled` | `hidden` | `color` | `live` | `blocked` | `deferred` | Use case |
|------|-----------|----------|---------|--------|-----------|------------|----------|
| `pending` | `false` | `false` | `neutral` | `false` | `false` | `false` | Draft, proposed, requested (awaiting work) |
| `active` | `false` | `false` | `positive` | `true` | `false` | `false` | In progress, under review, being addressed |
| `attention` | `false` | `false` | `danger` | `false` | `false` | `false` | Blocked, failing, or needs urgent attention |
| `blocked` | `false` | `false` | `danger` | `false` | `true` | `false` | Explicitly blocked and waiting |
| `in_force` | `true` | `false` | `info` | `false` | `false` | `false` | Accepted, published, or in effect (terminal, shown) |
| `deferred` | `true` | `true` | `info` | `false` | `false` | `true` | Work handed to another item the sub-entity names (terminal, hidden) |
| `done` | `true` | `true` | `positive` | `false` | `false` | `false` | Complete, verified or noted (terminal, hidden by default) |
| `retired` | `true` | `true` | `muted` | `false` | `false` | `false` | Superseded, deprecated, or cancelled (terminal, hidden) |
| `superseded` | `true` | `true` | `muted` | `false` | `false` | `false` | Replaced by a newer decision (terminal, hidden) |

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

**Declaring your own blocked role.** An override that keeps the bundled `blocked` role keeps its
flag. One that replaces the bundled roles with its own has no blocked role until one of its roles
declares the flag, and until then a type that selects `blocked_has_blocker` is refused at load:

```
item 'task': validators entry 'blocked_has_blocker' needs a status of a role declaring blocked =
true, and the lifecycle 'work' of 'task' holds none — without one it never fires; drop the entry
or give the lifecycle a status of a blocked role
```

Add `blocked = true` to the role your waiting statuses use, and the spec loads:

```toml
[roles.waiting]
settled = false
hidden = false
color = "danger"
blocked = true

[statuses.Blocked]
role = "waiting"

[selected]
roles = ["pending", "active", "attention", "waiting", "in_force", "done", "retired", "superseded"]
```

**Viewing the role catalog:**

```bash
sq workflow roles           # list all available roles
sq workflow roles --json    # machine-readable format
```

```
Role        Settled  Hidden  Color     Live  Blocked
active                       positive  yes
attention                    danger
blocked                      danger          yes
done        yes      yes     positive
in_force    yes              info
pending                      neutral
retired     yes      yes     muted
superseded  yes      yes     muted
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

A view declares its `source`, and optionally a `position` and a `transform`. `fields`, `group_by`,
`order_by` and a type attachment (`items.<type>.views`) are refused by name, and
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
source, an optional `position`, an optional `transform`, and a template, nothing more. The
complete field reference is
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

The bundled `role_definition` view declares `position = "top"`, so a role's definition comes
before the prose written beside it; setting it to `"bottom"` puts the prose first.

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
`role`/`playbook`/`self` — plus `item` and `spec`, and `data` when the view declares a transform.
Without a transform, grouping and ordering are the template's own job, with Jinja's
`groupby`/`sort`/`selectattr`:

```jinja
{% for r in source | sort(attribute="type,sequence_id") %}
- **{{ r.id }}** {{ r.status }} — {{ r.title }}
{% endfor %}
```

The bundled milestone roll-up has a transform: its template renders `data.delivered`,
`data.outstanding` and `data.settled`, already split and ordered. Restyling it is a template
change — copy the template with `sq override scaffold` and edit it. A template override can still
read `source` and group it its own way, but its text then no longer matches what `show --json`
reports under `views.milestone_rollup`; to change the split for both, give the view a transform of
your own (below).

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

##### Giving a view a transform

A transform is a Python function that turns a view's source into plain data. The template renders
that data, and `show --json` returns it under `views.<name>`, so a script reads the same numbers a
person sees. The grammar, the call and every rule are in
[workflow.md § "View transforms"](workflow.md#view-transforms); this is the worked example.

A feature view that counts its stories. Declare it in `.overrides/workflow.toml`:

```toml
[views.story_progress]
source = { kind = "subentity", name = "story" }
transform = { path = "transforms/progress.py", function = "story_progress" }
```

Write the function in `.overrides/transforms/progress.py`. It takes the source positionally and
asks for `spec` by name, so sq passes `spec` and not `item`:

```python
def story_progress(source, *, spec):
    done = [s for s in source if spec.role_for(s.status).settled]
    return {
        "total": len(source),
        "done": len(done),
        "open": [
            {"id": s.local_id, "title": s.title, "status": s.status}
            for s in source
            if s not in done
        ],
    }
```

Render the data in `.overrides/templates/views/story_progress.md.j2`:

```jinja
**Stories: {{ data.done }} of {{ data.total }} settled.**
{% for s in data.open %}
- {{ s.id }} {{ s.status }} — {{ s.title }}
{% endfor %}
```

Check it, then place the view on a feature:

```bash
sq workflow lint                          # the declaration, then the file: imports, function found
sq feature <n> view add story_progress
sq feature <n> show                       # the rendered line and the open stories
sq feature <n> show --json | jq .views    # the same data
sq workflow view story_progress FEAT-<n> --json   # what the function receives
```

`show --json` then carries the function's return value, and `body` keeps the tag as stored:

```json
{
  "views": {
    "story_progress": {
      "total": 2,
      "done": 0,
      "open": [
        {"id": "US<j>", "title": "Draw the widget", "status": "InProgress"},
        {"id": "US<k>", "title": "Paint the widget", "status": "Todo"}
      ]
    }
  },
  "body": "## Summary\n\n_TODO: summarise this feature._\n\n<!-- sq:view:story_progress -->"
}
```

`sq override scaffold workflow` writes a commented version of the same declaration on its
`related_incidents` example.

**Where the file is looked up.** `path` is relative to the `.overrides/` folder of the squad the
command runs against: the squad `-C` names, or the one the walk-up from the working directory
finds. The process's own working directory takes no part, so `sq -C ../other-project show <id>`
runs the other project's transforms and never a file of the same name where you stand.

**Confined to `.overrides/`.** The loader refuses a `path` with a `..` segment, an absolute path or
a backslash. A symlink is followed and only its final target counts: a link inside `.overrides/`
whose target is also inside is accepted, and one whose target is outside is refused, naming the
resolved target, before any of that file's code runs:

```
error: view 'story_progress' on FEAT-<n> (transform transforms/progress.py:story_progress): path resolves to /home/me/elsewhere/outside.py, outside .overrides/
```

`.overrides` may itself be a symlink to a folder elsewhere: the comparison is made after resolving
it.

**A transform file is code your team commits, and sq runs it.** Treat it as you would a
`conftest.py`: it runs with the permissions of whoever runs `sq`, with nothing asked first. Any
command that renders its view runs it — `sq show`, `--raw` and `--json`, `sq workflow view`, the
TUI reader — and `sq check` and `sq workflow lint` import it, which runs its top-level code, to
check that it loads. Review a change to a transform file as you would a change to any other code
in the repository, and do not run `sq` on a squad whose `.overrides/` you do not trust.

**What a transform file can import.** The standard library and the packages installed in the
environment `sq` runs in. sq does not add `.overrides/` to the import path, so a helper module
next to the file cannot be imported: keep helpers in the same file. sq reads the file afresh on
each read and writes no bytecode cache under `.overrides/`, so an edit takes effect on the next
command.

**The file is not a registered module when the function runs.** sq executes the file under a
generated module name that stays in `sys.modules` only while the file's top level runs, so nothing
from one read survives into the next. Code that looks that module up by name *during the call*
fails:

- `typing.get_type_hints()` on a class whose annotation names a class defined later in the file:
  `NameError: name 'Later' is not defined`;
- a pydantic model with a forward reference to a later class: the model is reported as not fully
  defined;
- `pickle` of an instance of a class the file defines:
  `PicklingError: Can't pickle <class '_squads_view_transform_…'>: No module named '_squads_view_transform_…'`.

Each comes out as an ordinary transform error. Plain functions, dicts, lists and
dataclasses without forward references work as they do anywhere; return plain data rather than
instances.

##### Authoring a role or skill body by hand

A role takes prose with no override: `sq role <slug> body` writes beside its generated
definition on every role (see
[roles.md § "Updating and commenting on roles, skills and operators"](roles.md#updating-and-commenting-on-roles-skills-and-operators)).

A permanently-system skill's body (`squads`, `greeting`, `sq-memory`) and a per-item-type
`sq-<type>` skill's body render through their view and refuse prose — replace and append alike,
`--force` or not. The same skills refuse a description, an attribute the bundled spec declares, a
title and view edits (see
[roles.md § "What a generated role or skill refuses"](roles.md#what-a-generated-role-or-skill-refuses)).
Their content normally comes from the playbook overrides or the view's own template override. To
write one of these bodies yourself instead, drop its view from `[selected]`. `[selected].views`
lists the survivors, so name every other view you keep:

```toml
[selected]
views = ["milestone_rollup", "role_definition", "greeting_skill", "memory_skill", "item_skill"]
```

With `squads_skill` dropped, `sq skill squads body -m "…"` is admitted, and `sq sync` and
`sq repair` leave the prose alone. The tag already in the body now names an undeclared view, so
`sq check` reports it until you run `sq skill squads view disable squads_skill`. Putting the view
back in `[selected]` makes the body refuse writes again. A skill body that holds prose and lacks
its tag is reported, with the remedy. The text you wrote stays, and renders beside the view once
its tag is re-enabled with `view add`; changing it means dropping the view again.

Dropping `role_definition` the same way is only for replacing a role's generated definition with
text of your own. It affects every role at once: each one's tag becomes an undeclared-view error
in `sq check` until cleared with `sq role <slug> view disable role_definition`, and a role
activated while the view is dropped gets no tag.

A runbook you want to keep does not belong in an `sq-<type>` skill's body: give it a skill of its
own with `sq skill add`. If one already sits in an `sq-<type>` skill, `sq check` names the five
steps that move it out — see
[migration.md § "After `sq migrate up`: seeded views"](migration.md#after-sq-migrate-up-seeded-views).

---

## The override grammar: shadow, append, and drop

Your `workflow.toml` is a **delta**, not a replacement. squads reads the bundled spec, composes your
file over it, and validates the result. Five rules govern how the two combine.

The examples below use workflow keys, but the first three rules, deep merge, plain arrays and
splat-refs, hold the same way for the role overrides, `roles.toml` and `roles/<slug>.toml`: a
role's `responsibilities = ["$(*self)", "…"]` appends to its bundled list (see
[Role overrides merge by field](#precedence-rule)).

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
and `views` — the sections the top level accepts, less `[selected]` itself and `[squad]`, whose one
key is a list you replace in `[squad]` instead. Anything else under
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
`frontmatter_key_undeclared` and the eight work-policy checks listed there.

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
  { slug = "security-analyst", authors = true, enter = ["Read the threat model"], do = ["Record any exposure found"], handoff = ["Exposure confirmed → @*plan to plan the fix"], watch = ["Don't file a bug for a policy question"] },
]
```

After `sq sync`, `sq create bug --author security-analyst` no longer prints
`advisory: 'security-analyst' is not the in-lane author for 'bug' items`,
`sq role security-analyst show` lists `bug` under `creates`, and the bug line of the team workflow
in `CLAUDE.md` and `AGENTS.md` names every in-lane author on the roster ("The **QA engineer** and
the **security analyst** author **bugs** …").

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
- **A slug is a role slug or `*<capability>`.** A role slug names one role of any kind: a
  catalog role, a role built from a template, or a role that defines itself. `*<capability>`
  addresses every live role holding that capability (see
  [roles.md § "Capabilities"](roles.md#capabilities)); the bundled guides addressed to `*dev` use
  that form to reach every developer. The playbook loader checks a subject for its form only, so
  `*Dev`, `*` and `* dev` are refused at load, naming `.overrides/playbook.toml`, while a
  well-formed slug no role holds loads and is reported by `sq check` (below).
- **A capability guide renders under its capability.** Its section in the generated skill is headed
  with the capability and its holders (``## For `*infra`: Bob Builder (`builder`)``), and
  `authors = true` puts the type in the create lane of every holder.
- **A guide reaches the skill only while its role is live.** A guide naming a role that is not
  live loads but is dropped when the skill is generated. `sq check` and `sq sync` both warn while
  that is true, naming the guide and both ways out. For a slug the role catalog declares, the way
  in is `sq role activate <slug>`; for any other slug, `sq role add <slug> …` or
  `sq role activate <slug> --from <template>`:

  ```
  warn: playbook guide for role 'ghost' on type 'task' names no live role, so its guidance is dropped from the generated `sq-task` skill — create the role (`sq role add ghost …`, or `sq role activate ghost --from <template>`), or remove the guide from `.overrides/playbook.toml` under `[types.task]`
  ```

  The same warning covers a role you activated and later retired. A guide of yours addressed to a
  capability no live role holds is warned about the same way, with its two ways out:

  ```
  warn: playbook guide for capability '*infra' on type 'bug' names no live role, so its guidance is dropped from the generated `sq-bug` skill — declare `capabilities = ["infra"]` on a live role, or remove the guide from `.overrides/playbook.toml` under `[types.bug]`
  ```

  A bundled capability guide nobody holds stays silent. These are warnings, not refusals: both
  commands still exit `0`.
- **A type with open work needs a live author.** `sq check` warns, through the
  `type_has_live_author` check the bundled `[squad] validators` list selects, about each type
  outside the roster that holds an item at a status that is not settled while no live role has an
  `authors = true` guide on it, bundled or yours. The remedy names each author the playbook gives
  the type, joined with "or": a catalog role never activated, a role retired from the roster, and
  for a guide addressed to a capability, every catalog or roster role holding it. A developer
  capability no role holds reads "add a developer". In a squad started with
  `sq init --roles minimal`, with a `qa` guide and a `*review` guide authoring `bug`, a `*dev`
  guide authoring `contract`, and `reviewer` activated then retired, `sq check` reports, beside
  the guide warnings above:

  ```
  warn: type 'bug' has 1 open item but no live role authors it — activate `qa` (`sq role activate qa`) or reactivate `reviewer` (`sq role reviewer status Active`)
  warn: type 'contract' has 1 open item but no live role authors it — add a developer (`sq dev add --tech <tech>`)
  warn: type 'review' has 1 open item but no live role authors it — reactivate `reviewer` (`sq role reviewer status Active`)
  warn: type 'task' has 1 open item but no live role authors it — activate `tech-lead` (`sq role activate tech-lead`)
  ```

  When the role lifecycle has no edge from the retired status back to the live one, the reactivate
  remedy carries `--force` and says why:
  ``reactivate `reviewer` (`sq role reviewer status Active --force`; Archived has no edge to Active)``.
  A type no guide authors at all is reported with no remedy. A type whose items are all settled is
  not reported, so retiring a role on purpose leaves its finished items without a warning. To turn
  the check off or raise it, see [Squad-wide checks](#squad-wide-checks-the-squad-table).
- **A hand-off names a capability with `@*<name>`.** In guide lines and in a type's `commands`,
  `@*<name>` renders in the generated skill as the `@<slug>` of every live holder, `/`-joined in
  roster order, or as `*<name>` when nobody holds it; the bundled guides use it for every hand-off,
  and the security-analyst example above uses `@*plan` (see
  [roles.md § "Mentioning a capability in hand-offs"](roles.md#mentioning-a-capability-in-hand-offs)).
  A literal `@<slug>` names one fixed role. A token whose name is malformed (`@*Sec`) makes
  the playbook fail to load, naming the type. A well-formed token in one of your guides that no live
  role holds is warned about once per type and capability by `sq check` and `sq sync`:

  ```
  warn: playbook guide on type 'bug' mentions `@*security`, but no live role holds the capability, so the generated `sq-bug` skill renders it as `*security` and mentions nobody — declare `capabilities = ["security"]` on a live role, or edit the line in `.overrides/playbook.toml` under `[types.bug]`
  ```

  The same token in a bundled guide renders as `*<name>` without a warning, and a token in a type's
  `commands` is not checked.
- **Unknown top-level keys are refused by name**, the same fail-closed rule the workflow override
  follows. The accepted keys are listed in the message.

### Guidance for a role you invented

A role you created yourself, with `sq role add` or from a template, can be given playbook guidance
like any bundled role. Name it in a type's `roles`, run `sq sync`, and it gets its own section in
that type's generated `sq-<type>` skill; the skill is also preloaded on the role's generated
pointer, so the role boots with it. Until you name it somewhere in the playbook, a custom role
appears in no item skill at all.

**Write the guide and create the role in either order, but do both.** A guide naming a slug no
role holds yet loads, and `sq check` reminds you its guidance is not reaching the skill. What you
should not do is leave it there, because the guidance stays absent from the generated skill:

```bash
sq role add security-analyst --name "Sam Security" --job-title "security analyst" --desc "Reviews changes for exposure." --mission "Keep the attack surface small."
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

- Your override's `override-base` stamp against the installed squads version.
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

This rewrites the `squads:override-base:` stamp to the installed squads version — **and nothing
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

# A developer already on your roster (every field commented out with its current value)
sq override scaffold --role python-dev

# Start the workflow override (vocabulary: item types, statuses, lifecycles, collections)
sq override scaffold workflow

# Start the playbook override (which roles interact with each item type, and their guidance)
sq override scaffold playbook

# Start the role catalog override (roles, templates and bundles in one document)
sq override scaffold roles

# Overwrite an existing override
sq override scaffold items/task.md.j2 --force
```

**What it does:**
- `--role <slug>` writes `.overrides/roles/<slug>.toml`. For a role of the bundled catalog, every
  field an override can set follows the stamp, commented out with its bundled value: `full_name`,
  `title`, `description`, `mission`, `responsibilities`, `agreements`, `model`, `color`,
  `can_spawn` and `capabilities`. A commented `responsibilities = ["$(*self)", "…"]` line shows how
  to append to the bundled list instead of replacing it. Uncomment the lines you want to change and
  run `sq sync`; a field left commented keeps its bundled value. For a role already on the roster
  (a developer such as `python-dev`, or any other role) the same fields follow, commented out with
  that role's current values. A slug with no role item and no catalog entry is refused with exit `1`
  and nothing written, naming the commands that create a role:

  ```
  error: no role 'nobody' to override: create it with `sq role add nobody --name … --job-title … --desc … --mission …` or `sq role activate nobody`
  ```
- `--new` is retired. A custom role is created with `sq role add`, and `--new` exits `1` naming it:

  ```
  error: `sq override scaffold --new` is retired: create the role with `sq role add foo --name … --job-title … --desc … --mission …`
  ```
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
- Rewrites the `squads:override-base:` stamp to the installed squads version.
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
- **Base version:** the squads version the override was branched from (from the stamp), or
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
roles) or the name pattern of the template it is built from (developer roles).

### Naming roles after init

When you activate a new role, add a developer or create a custom role, you can provide a name
then:

```bash
# Activate a bundled role with a custom name
sq role activate architect --name "Chief Designer"

# Add a Python developer with a custom name
sq dev add --tech python --name "Pythonista"

# A custom role always takes its name at creation
sq role add sre --name "Sam Reliability" --job-title "site reliability engineer" --desc "Keeps production up." --mission "Keep the services up and the pager quiet."
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

1. **A name you give:** `--name` on `sq role activate`, `sq role add` or `sq dev add`, or at
   `sq init` a `--name` flag, the `[init.names]` table or the prompt.
2. **`full_name` in `.overrides/roles/<slug>.toml`**, when the file is there as the role is
   created.
3. **`full_name` in `.overrides/roles.toml`.**
4. **The bundled catalog's name**, or for a role built from a template the template's `name`
   pattern (for a developer, a first name from the pool followed by the tech).

**After that, the stored name is the role's name.** No configuration change renames an active
role: a `full_name` added to or changed in either override file, or a squads release that changes
a bundled name, names the roles created after it and leaves the ones you have alone. `sq sync`
never changes a name, and the upgrade to a new squads version keeps every stored name. To rename a
role, use `sq role <slug> update --title` (see "Renaming an active role" below).

**What `sq sync` keeps, and what it refreshes.** The name is kept. So is a `model` the role
stores, set with `--model` at creation or with `sq role <slug> update --model`. Everything else in
a catalog or template role's definition — its job title (the catalog's `title`, not the name
stored as the role item's `title`), mission, responsibilities, spawn authority, its model when it
stores none, its preloaded skills — is refreshed from the catalog entry or the template (and your
overrides) on every sync, so an improvement squads ships reaches a role you activated long ago. A
role that defines itself keeps the definition it stores.

**Renaming an active role** sets its stored `title` with `update --title`, on any role, a bundled
one included:

```bash
sq role architect update --title "Chief Designer"
```

The rename moves the role's `updated_at` and shows up in `sq reflog` as an update carrying the old
and new names. The role's `.claude/` pointer and the `CLAUDE.md` roster show the new name at once.
The slug does not change (see below), and comments the role wrote earlier keep the name they were
written under.

### Slug immutability

**Role slugs stay canonical and are never renamed.** The slug (`architect`, `tech-lead`,
`python-dev`) is the addressing key for skills, @mentions, pointer filenames, and interactions. A
team renames *who fills the architect slot*, not *the architect slot itself*.

If you need a new role entirely, create it under a new slug with `sq role add`. If you need to split an existing
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
same file would not rename them either: a `full_name` names a developer only when the file is
there before `sq dev add` creates it.

### Define a custom role

You want a compliance-officer role that isn't in the bundled catalog. Create it with its
definition:

```bash
sq role add compliance-officer --name "Cora Compliance" --job-title "compliance officer" --desc "Keeps the project's work compliant." --mission "Review changes for regulatory and policy compliance." --model opus
```

The definition is stored on the role item, and `add` writes its pointer. For a longer definition,
with responsibilities or capabilities, put it in a TOML file in the per-slug override grammar and
pass it with `--file` (see [roles.md § "Custom roles"](roles.md#custom-roles-sq-role-add)). Change
it later with `sq role compliance-officer update --mission …` or `update --file`.

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
in v<version>: ['agreements', 'can_spawn', 'capabilities', 'color', 'description', 'full_name',
'is_default', 'mission', 'model', 'responsibilities', 'selected', 'slug', 'title']
```

`sq check` reports it as an error, `sq role <slug> show` refuses, and so does `sq sync` once the
role is on the roster. Nothing passes an unknown field through to a template. For a field squads
*does* recognise (like `model`), set it in the override and run `sq sync`. To store a key of your
own on each role item instead, declare it as an attribute of the `role` type in
`.overrides/workflow.toml` (see [Attributes](#attributes-the-keys-a-type-stores)). `sq role <slug>
update` takes no `--set`, so set it with an `update` event of `sq import`:
`echo '{"op": "update", "target": "ROLE-<n>", "fields": {"<key>": "<value>"}}' | sq import - --as <slug>`.
