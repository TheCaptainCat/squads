---
id: ADR-984
sequence_id: 984
type: decision
title: A developer is a role that declares a capability, not a slug suffix
status: Accepted
author: architect
refs:
- MILE-934:targets
- REV-956:addresses
- ADR-971
- ADR-754
- ADR-979
- ADR-981
- FEAT-976
- ADR-1007
- ADR-1151
description: Roles declare capabilities; *dev addresses the dev capability; extra.is_dev
  is dropped and extra.tech kept; slugs stay; no second 0.16 schema bump
created_at: '2026-10-09T18:30:02Z'
updated_at: '2026-10-25T21:42:31Z'
---
<!-- sq:body -->
## Context

Before this decision, "is this role a developer?" was answered by a slug spelling and,
separately, by a stored marker, and the two disagreed for the same role in one squad. The
measurements below describe that code.

Each claim is marked **read** (the source was read), **driven** (a command was run: the working
tree's build at `8cdcd018` on `release/0.16`, in a scratch squad) or **inferred**.

**Two answers.**

- **The stored marker** `extra.is_dev`, written by `sq dev add` and by nothing else. Six reads: the
  resolver's merge base, the frontmatter skew exemption, the catalog refresh (twice), the name-pool
  position, and `sq dev list` (read; each of the six sites in REV-956 finding 1 was opened).
- **The spelling** `slug.endswith("-dev")`: `is_dev_slug` with seven callers, and five re-spellings
  that do not use the helper, one of them in Jinja (read; each of the twelve sites in that finding
  was opened). The `*dev` playbook sentinel is declared twice in Python and used four times in the
  bundled playbook (read).
- **Sites that inventory does not list** (read): the section template's unconditional sentence "a
  developer's slug is `<tech>-dev`" and its `<tech>-dev` delegate example; six `<tech>-dev`
  placeholders in bundled playbook prose; the literal section heading `developers`; a literal
  `python-dev` example in the memory skill template; and `extra.tech`, declared settable on any
  role item with the note "harmless elsewhere" (`_models/_metadata.py`).

**The disagreement** (driven). A role declared by `.overrides/roles/platform-dev.toml`, titled
"platform engineer" and activated with `sq role activate`, stores `extra = {slug}`. Then:

- its pointer preloads `sq-task`, `sq-bug`, `sq-contract` and `sq-review`; with it as the only such
  role, the task skill gains its "For developers" section and `CLAUDE.md` gains the `<tech>-dev`
  delegate example;
- `sq dev list` prints "no developers", `role_base_from_item` returns no base, and the skew
  exemption treats it as a non-developer.

The converse is the adopter-facing half (read): a custom role cannot receive the developer
guidance unless its slug ends in `-dev`, because the marker has no writer but `sq dev add`.

**The two answers serve two different questions.**

- The spelling decides which playbook guides address a role: its preloaded skills, the shared
  section, its create lane.
- The marker decides how a role's definition is produced: from the generator `dev_role(tech)`
  instead of a catalog entry (read).
- `extra.is_dev` and `extra.tech` are written together by the one writer, and the resolver
  subscripts `extra.tech` whenever the marker is set. In any squad that works, the marker is true
  exactly when `tech` is present (read).

**What a developer stores and what is derived.** The item stores `slug`, `tech`, `is_dev` and
`model` (driven). Title, mission, responsibilities and colour are regenerated from `tech` and the
catalog's `[dev]` table on every read; a per-slug override merges over that base (read; ADR-754).
The slug is stored identity and is never re-derived (ADR-971).

**An existing developer reads the template from the bundled catalog** (driven). With
`[dev] color = "red"` in `.overrides/roles.toml`, a new developer's pointer is written red and the
next `sq sync` rewrites it green: `dev_base_from_item` calls `dev_role()`, which is bound to the
bundled document. A capability declared in `[dev]` would be read the same way.

**A slug with no item is still judged by its spelling** (driven). `sq role go-dev show` for a
developer not yet added exits 0 with a generated preview. A partial `.overrides/roles/go-dev.toml`
loads, where the same file named `data-lead.toml` is reported by `sq check` as missing its required
fields.

**A function that holds a slug can ask nothing else.** `RoleView`, the projection given to backends
and templates, carries no developer field. It is defined in `_backends/_base.py`, which
`_interactions` cannot import, so two structural protocols stand in for it (read; REV-956
finding 2).

**Clients and documented text.**

- The VS Code client reads role items through `list -t role --json` (read) and reads neither
  `extra.is_dev`, `extra.tech` nor the suffix (driven: a search of its source, validated against a
  known positive in its tests).
- `docs/stability.md` names none of `sq dev`, `*dev`, the suffix, or any `extra` key (driven: a
  search validated on a known positive). It does say `sq migrate` never rewrites overrides (read).
- `docs/roles.md` and `docs/overrides.md` document the suffix rule, the `*dev` sentinel, that a
  developer's definition is refreshed from the bundled one, and that an override for a developer
  not yet added is accepted (read).

**The 0.16 schema step.** `SCHEMA_VERSION` is `0.15` and the registry ends at 0.14 to 0.15: no 0.16
runner exists (read). ADR-979 decides a 0.15 to 0.16 step for comment headers.

## Decision

### 1. A role declares capabilities, and the playbook addresses a capability

- `capabilities` is a list of names on a role's definition. It is accepted in a `[[roles]]` entry,
  in a per-slug role file and in the `[dev]` table. A name matches `[a-z0-9][a-z0-9-]*`. The
  default is empty.
- The bundled catalog declares `dev` on `[dev]`, so every templated developer holds it. The
  capabilities the bundled roles hold for hand-offs (`plan`, `review`, `verify`, `product`,
  `edit`) are decided by ADR-1121.
- A playbook guide's subject is a role slug, or `*<name>`, which addresses every live role that
  holds capability `<name>`. `*dev` stops being a sentinel and becomes the first use of that form.
  The bundled playbook's four `*dev` guides keep their subject.
- **The vocabulary is open and the engine holds no capability name.** `dev` appears in the bundled
  documents only. A project may declare others, for example `*reviewer` over two reviewer roles,
  with no code change.
- A capability-addressed guide behaves the same for any name: its holders
  preload the type's skill, its section renders only while at least one holder is live, and
  `authors = true` on it puts the type in every holder's create lane.
- Its section names the capability and lists the live holders. No label is declared.
- **Checked, not trusted.** A malformed name is refused at load, naming the file. A guide declared
  by an override whose capability no live role holds is reported by `sq check` and `sq sync`, on
  the terms a guide naming a non-live role already is. A role holding a capability that no guide
  addresses is not reported.

### 2. The capability is resolved once and travels on the role

- `RoleDef` and `RoleView` carry `capabilities`. `resolve_role_for_item` is the one place it is
  computed, as it is for `is_default`.
- Nothing below the resolver decides anything from a slug string. The role derivations
  (`item_types_for_role`, `skills_for_role`, `allowed_create_types`, `item_skill_role_sections`,
  `example_assignee_slug`) take the resolved role or the roster, never a bare slug.
- Every function on that path takes the active role catalog and playbook as required arguments.
  The template is read from the catalog the squad resolves, never from a shim bound to the bundled
  catalog.
- No code tests a slug for the `-dev` suffix outside the migration runners.

### 3. A developer is produced from the template, or declared like any role

There are two ways to have a developer and one treatment afterwards.

- **Declared.** Any role file carrying `capabilities = ["dev"]`, activated with
  `sq role activate`. Its item stores its slug and nothing of its definition.
- **Templated.** `sq dev add --tech <t>` instantiates the catalog's developer template. The
  definition is regenerated from the template and the role's `tech` attribute on every read, a
  per-slug override merges over it (ADR-754), and its capabilities come from the template's
  `capabilities`.

`sq dev add` takes `--tech`, `--name`, `--model`, `--slug` and the name pool. `sq dev list` lists
the live roles that hold a capability the developer template declares, templated or not.

ADR-1151 generalises the template: "templated" means built from any `[templates.<name>]` table,
`[dev]` is `[templates.dev]`, a template's prose (title, description, mission, responsibilities) is
declared in the table, `sq dev add` is an alias of `sq role activate [<slug>] --from dev --tech
<t>`, and `sq dev list` reads `[templates.dev].capabilities`.

### 4. Storage: no developer marker; `tech` stays

- **No `is_dev` marker is stored.** It is derivable: a role item that carries `tech` is a
  templated role.
- **`tech` stays.** It is a top-level role attribute, declared in the bundled workflow spec with
  `settable = false` and pinned by the loader (ADR-1007), and `sq dev add` is its only writer. It
  is the template's one parameter and nothing else holds it: the slug is a lossy form of it
  (`Node.js` becomes `node-js-dev`) and is not read.
- Which base a role resolves from never answers what the role may do. ADR-1151 decides how that
  base is chosen, from a stored `template` attribute (written as `dev` on existing developers),
  with `tech` the template's parameter, and the name-pool position counting the roles that store
  the same template.
- `model` is a declared role attribute too, written for a templated role only.
- Nothing enters the index that the files cannot rebuild.

### 5. Slugs

- Existing slugs stay (ADR-971, ADR-979). `python-dev` keeps its name, its pointer and its history.
- A new developer's slug is proposed as `<slugified tech>-dev`, or given with `--slug`. An explicit
  slug follows ADR-979's reserved-slug rules and is compared exactly, as `sq operator add --slug`
  is, so one tech can have a second developer.
- The suffix is a default spelling. No read path consults it.

### 6. A slug that names no role resolves to nothing

A `<tech>-dev` slug with no roster item gets no spelling fallback.

- `sq role <slug> show` and `sq override scaffold --role <slug>` for a developer not yet added
  exit 1 with the ordinary unknown-role error, in place of a generated preview.
- A partial `.overrides/roles/<slug>.toml` for a slug with no item and no catalog entry is reported
  by `sq check`, whatever the slug's spelling. `sq dev add` still merges such a file at creation.

This narrows ADR-754 decision 2, whose precedence was "a stored fact first, a naming convention
only where no stored fact exists". The first half stands.

### 7. Generated text names roles from the roster

- No template and no bundled guide states a slug pattern. The roster printed in the
  managed section already gives every slug.
- Delegate examples and the example assignee are concrete slugs of live roles, computed in Python
  and handed to the template. No template carries a curated list of bundled slugs.
- Bundled playbook prose names developers through the `@*dev` capability token (ADR-1121), never
  through a slug spelling.

## Rejected

- **A boolean `is_dev` on the role definition.** It moves the literal from a spelling to a field
  name. The engine would still hold one hard-wired group and its sentinel, and a project could not
  declare a second.
- **Keeping the stored marker and projecting it onto `RoleView`.** A declared role has no verb that
  sets it, it stores per item what the template declares once, and it keeps one name for two
  questions.
- **Scaffolding every developer into its own role file**, with no template at read time. This is
  the most uniform end state: the item stores `{slug}` and the resolver has one path. It makes each
  developer a copy of template text that a later release cannot reach, where `docs/roles.md`
  promises the definition is refreshed. Existing squads would need `sq migrate` to write and
  rewrite files under `.overrides/`, which `docs/stability.md` says it never does.
- **A separate `capability` key on a guide, beside `slug`.** It makes `lane.roles[].slug` nullable
  in the `playbook` view payload, which the `--json` tier forbids, and it refuses every playbook
  override that names `*dev` on upgrade. The `*<name>` form costs neither.
- **A declared capability catalog** (`[capabilities.dev]` with a label). It buys a section heading
  and typo detection on a role's list, for a third new table in a closed key space. The orphan
  guide report catches the typo that changes behaviour.
- **Reading the suffix for one more release.** A dual read is permanent code for a state the
  upgrade ends, which is the reasoning ADR-979 applied to comment headers.
- **Renaming existing developers, or changing the default suffix.** Slugs are permanent, and a new
  default would only mix two conventions.

## Consequences

**Behaviour on upgrade from 0.15.**

- A project role whose slug ends in `-dev` and which `sq dev add` did not create receives no `*dev`
  guidance until its file declares `capabilities = ["dev"]`.
- The two exit-1 paths and the `sq check` report of decision 6.
- An existing developer picks up a project's `[dev]` override on the next `sq sync`.

**Migration and schema.**

- The change rides the 0.15 to 0.16 schema step that ADR-979 introduced, with no bump of its own:
  a build that does not write `is_dev` must not share a squad with one that reads it.
- `is_dev` is one of the closed list of retired role keys (`RETIRED_ROLE_KEYS`) that the rebuild at
  the end of `sq migrate up` strips.
- `sq migrate` rewrites no override. The 0.16 runner reports each project role that ends in `-dev`
  without the template parameter, and the step's manual text names the remedy. A migration runner
  is the one place that may know the retired spelling.

**Frozen surfaces.**

- **Role catalog document.** `capabilities` is in the closed key space of a role and of `[dev]`. An
  older package refuses a document that carries it.
- **Playbook.** A guide subject is a slug or `*<name>`. An override that names `*dev` addresses the
  holders of the `dev` capability, not a slug spelling.
- **`--json`, additive.** `capabilities`, an array always present, on `role catalog`, `role list`,
  `role <addr> show` and each `roster[]` row of the `playbook` view payload. `lane.roles[].slug`
  keeps its type and carries `*dev` for a capability-addressed guide.
- **CLI.** `sq dev add --slug`, and the exit codes of decision 6.
- **VS Code client.** No source change.

**Other decisions.**

- ADR-754 decision 2 is narrowed by decision 6. ADR-971 decision 2 reads the presence of `tech` as
  selecting the template.
- ADR-981's `[defaults]` and this decision's `capabilities` extend the same closed key space and the
  same models, and do not interact in meaning.

## Left out

- **The template's prose as data.** This decision left title, mission and responsibilities
  composed in Python; ADR-1151 moves them into the template table with a placeholder grammar.
- **`model` stamped at creation.** `sq dev add` without `--model` stores the catalog
  default, so a later change to `[dev].model` does not reach that developer. It is the stamped
  default ADR-981 turned down for pronouns, and it is a separate change.
- **The `op-` prefix.** It is a reserved namespace that role creation enforces (ADR-979), not a
  convention.
- **A capability filter on `sq role list`, and `--json` on `sq dev list`.**
- **Example slugs in `--help` text** (`python-dev`). They are examples of a legal slug.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T18:30:59Z] `architect` Robert Architect:
  - @manager for op-pierre: left Proposed, nothing broken down. The calls I most want weighed before accepting, in order of how much they shape the build:
    
    1. **Ordinary in treatment, not in production.** Every consumer sees a developer as a role with a capability, and an adopter can declare one in a plain role file. A developer made by `sq dev add` still gets its definition from the `[dev]` template on every read, selected by `extra.tech`. The literal reading of the milestone line is the alternative I rejected: scaffold each developer into its own role file. I turned it down because template updates would stop reaching developers and `sq migrate` would have to write under `.overrides/`. If uniformity matters more than those two, say so and decisions 3, 4 and 6 change.
    2. **An open capability vocabulary instead of a boolean.** `*<name>` addresses any declared capability, and the bundled one is named `dev` so `*dev` and every existing playbook override keep loading. It is wider than what was asked for. The cost is a subject grammar with a sigil in a field called `slug`.
    3. **Two changes on upgrade with no automatic fix.** A custom role that ends in `-dev` loses the developer guidance until its file declares the capability; the migration reports it and rewrites nothing. An override written before its developer is added stops passing `sq check`, and `sq role <slug> show` no longer previews a developer that does not exist.
    4. **`sq dev add --slug`** is new surface. It is what lets a second developer share a tech.
    5. **Migration.** No schema bump of its own; it relies on ADR-979's 0.15 to 0.16 step and adds one key to the retired-key sweep. That step now has three contributors. FEAT-976 says dev roles (`<tech>-dev`) are stamped `system`: that wording needs the product owner's attention, I did not edit it.
    6. **Order.** Import guard, then the `RoleView` move, then the slice of the `_interactions` split this rewrites, all before any behaviour changes. I did not make the rest of REV-956 findings 3, 5 and 6 preconditions, which is narrower than the review suggested for finding 6.
    7. **Left out on purpose:** the template's prose as catalog data, and the model stamped at `sq dev add`.
    
    Found while verifying, not filed (I was asked to create no bug): a project `[dev]` override reaches a new developer and is reverted for that same developer by the next `sq sync`, because an existing developer's template is read from the bundled catalog. Driven on the working tree at `8cdcd018`. Decision 2 fixes it; it may deserve its own bug if this build is not next.
    
    Verified myself: every site in REV-956 finding 1's inventory was opened, and its disagreement was reproduced in a scratch squad (a `platform-dev` custom role). Taken from the review without re-measuring: findings 2, 3, 5, 6 and 16, including the import-graph measurements. Not driven: that the retired-key sweep removes `is_dev` with no runner code, and the override drift path.
    
    If accepted, ADR-754 decision 2 and ADR-971 decision 2 each need a dated narrowing in place and a `related` ref back. I touched neither.
- [2026-10-09T18:40:01Z] `op-pierre` Pierre Chat:
  - 2026-10-09: accepted as written, including the open capability vocabulary, developers staying templated, sq dev add --slug, and the two upgrade changes with no automatic fix.
- [2026-10-25T21:06:48Z] `architect` Robert Architect:
  - Dated narrowing added 2026-10-25 for ADR-1151 (role bases and templates). The original text is unedited.
- [2026-10-25T21:42:31Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale passages fixed; decision unchanged. ADR-1007 note folded (tech/model top-level, is_dev a retired key); bundled capabilities point to ADR-1121; the dated ADR-1151 narrowings restated as what ADR-1151 decides; Order of work and stale migration bookkeeping removed.
<!-- sq:discussion:end -->
