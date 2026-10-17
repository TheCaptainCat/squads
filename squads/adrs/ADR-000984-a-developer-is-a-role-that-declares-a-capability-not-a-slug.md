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
description: Roles declare capabilities; *dev addresses the dev capability; extra.is_dev
  is dropped and extra.tech kept; slugs stay; no second 0.16 schema bump
created_at: '2026-10-09T18:30:02Z'
updated_at: '2026-10-15T20:17:03Z'
---
<!-- sq:body -->
## Context

"Is this role a developer?" is answered by a slug spelling and, separately, by a stored marker.
The two disagree for the same role in one squad.

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
- The bundled catalog declares one capability, `dev`, on `[dev]`. The eight bundled roles declare
  none.
- A playbook guide's subject is a role slug, or `*<name>`, which addresses every live role that
  holds capability `<name>`. `*dev` stops being a sentinel and becomes the first use of that form.
  The bundled playbook's four `*dev` guides keep their subject.
- **The vocabulary is open and the engine holds no capability name.** `dev` appears in the bundled
  documents only. A project may declare others, for example `*reviewer` over two reviewer roles,
  with no code change.
- A capability-addressed guide behaves as the `*dev` guide does today, for any name: its holders
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
- Nothing below the resolver decides anything from a slug string. The functions that take a bare
  slug today (`item_types_for_role`, `skills_for_role`, `allowed_create_types`,
  `item_skill_role_sections`, `example_assignee_slug`) take the resolved role or the roster.
- Every function on that path takes the active role catalog and playbook as required arguments.
  `dev_role()`, the shim bound to the bundled catalog, is removed: the template is read from the
  catalog the squad resolves.
- `is_dev_slug`, both `DEV` constants and the Jinja `endswith("-dev")` are deleted.

### 3. A developer is produced from the template, or declared like any role

There are two ways to have a developer and one treatment afterwards.

- **Declared.** Any role file carrying `capabilities = ["dev"]`, activated with
  `sq role activate`. Its item stores `{slug}`.
- **Templated.** `sq dev add --tech <t>` instantiates the catalog's `[dev]` table. The definition is
  regenerated from `extra.tech` on every read, a per-slug override merges over it (ADR-754), and
  its capabilities come from `[dev].capabilities`.

`sq dev add` keeps `--tech`, `--name`, `--model` and the name pool, and gains `--slug`.
`sq dev list` lists the live roles that hold a capability `[dev]` declares, templated or not.

### 4. Storage: `extra.is_dev` goes, `extra.tech` stays

- **`extra.is_dev` is removed.** It is derivable: a role item that carries `extra.tech` is a
  templated role.
- **`extra.tech` stays.** It is the template's one parameter and nothing else holds it: the slug is
  a lossy form of it (`Node.js` becomes `node-js-dev`) and is not read. It leaves the role's
  settable `extra` fields; `sq dev add` is its only writer.
- Its presence answers one question, in the resolver: where the definition comes from. It never
  answers what the role may do. The name-pool position counts the items that carry it.
- `extra.model` is unchanged.
- Nothing new is stored on an item, and nothing enters the index that the files cannot rebuild.

> **Note 2026-10-15 (ADR-1007):** these keys are top-level: `tech` and `model` are declared role
> attributes, pinned by the loader, and `is_dev` is lifted by the 0.16 runner and then removed by
> this decision's contribution. `tech` is declared with `settable = false`, since `sq dev add` is
> its only writer. See ADR-1007 decisions 3, 4 and 9.

### 5. Slugs

- Existing slugs stay (ADR-971, ADR-979). `python-dev` keeps its name, its pointer and its history.
- A new developer's slug is proposed as `<slugified tech>-dev`, or given with `--slug`. An explicit
  slug follows ADR-979's reserved-slug rules and is compared exactly, as `sq operator add --slug`
  is. A second developer for one tech becomes possible.
- The suffix is a default spelling. No read path consults it.

### 6. A slug that names no role resolves to nothing

The spelling fallback for a `<tech>-dev` slug with no roster item is withdrawn.

- `sq role <slug> show` and `sq override scaffold --role <slug>` for a developer not yet added
  exit 1 with the ordinary unknown-role error, in place of a generated preview.
- A partial `.overrides/roles/<slug>.toml` for a slug with no item and no catalog entry is reported
  by `sq check`, whatever the slug's spelling. `sq dev add` still merges such a file at creation.

This narrows ADR-754 decision 2, whose precedence was "a stored fact first, a naming convention
only where no stored fact exists". The first half stands.

### 7. Generated text names roles from the roster

- No template and no bundled guide states a slug pattern. The section template's sentence about
  `<tech>-dev` goes: the roster printed above it already gives every slug.
- Delegate examples and the example assignee are concrete slugs of live roles, computed in Python
  and handed to the template. The section template's curated list of bundled slugs goes with the
  `<tech>-dev` placeholder.
- Bundled playbook prose replaces `<tech>-dev` with a placeholder that names no spelling.

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

**Behaviour that changes on upgrade.**

- A project role whose slug ends in `-dev` and which `sq dev add` did not create stops receiving
  the `*dev` guidance until its file declares `capabilities = ["dev"]`.
- The two exit-1 paths and the `sq check` report of decision 6.
- An existing developer picks up a project's `[dev]` override on the next `sq sync`.

**Migration and schema.**

- **No second schema bump.** This relies on the 0.15 to 0.16 step ADR-979 decides: a build that no
  longer writes `extra.is_dev` must not share a squad with one that reads it. If that step left
  0.16, this decision would need it for that reason alone.
- The deterministic part is the removal of `extra.is_dev` from every role item. The key joins the
  closed list of retired role keys that the rebuild at the end of `sq migrate up` already strips
  (read), so the runner needs no code of its own for it (inferred, not driven).
- A build with this decision reads an un-migrated squad correctly, because every developer item
  already carries `extra.tech` (read).
- `sq migrate` rewrites no override. The runner reports each project role that ends in `-dev`
  without the template parameter, and the step's manual text names the remedy. A migration runner
  is the one place that may know the retired spelling.
- Unreleased 0.16 has one open step with three contributors: comment headers (ADR-979), origin
  stamping (FEAT-976) and this. Whichever lands first creates the runner and the others amend it.
- This repository's squad has two developer items and no overrides (driven). Both lose the key.

**Frozen surfaces.**

- **Role catalog document.** `capabilities` joins the closed key space of a role and of `[dev]`. An
  older package refuses a document that carries it (read). Bundled `roles.toml` changes bytes, so a
  stamped catalog override reports drift (inferred; the drift path was not traced).
- **Playbook.** The subject grammar widens from `*dev` to `*<name>`. An existing override that names
  `*dev` loads unchanged; what it addresses changes from a spelling to a declaration. Bundled
  playbook prose changes bytes, so a stamped playbook override reports drift (inferred).
- **`--json`, additive.** `capabilities`, an array always present, on `role catalog`, `role list`,
  `role <addr> show` and each `roster[]` row of the `playbook` view payload. `lane.roles[].slug`
  keeps its type and still carries `*dev` (read). `extra.is_dev` leaves the `extra` object of the
  generic `show` and `list` payloads, whose inner keys the stability document does not name.
- **CLI.** `sq dev add --slug`, and the exit codes of decision 6.
- **`docs/stability.md` needs a refresh:** Tier 1 for the role document key and the `*<name>` subject
  (the playbook override is not described there today), Tier 3 for the new key. `docs/roles.md`,
  `docs/overrides.md`, `docs/internals.md`, `docs/agents.md` and the README follow.
- **VS Code client.** No source change.

**Other decisions and features.**

- ADR-754 decision 2 is narrowed by decision 6. ADR-971 decision 2 calls `extra.tech` "an input to
  the generated template and nothing else"; it gains one reading, that its presence selects the
  template. Both take a dated narrowing in place.
- ADR-981's `[defaults]` and this decision's `capabilities` extend the same closed key space and the
  same models. They do not interact in meaning and should not be built in parallel.
- FEAT-976 stamps "dev roles (`<tech>-dev`)" as `system`. Under this decision that reads "a role item
  carrying `extra.tech`", and a declared developer is `project`.

**Tests.** 82 files under `tests/` mention `-dev` (driven), most as an ordinary slug, which stays
legal. The convention itself is asserted where a test names `is_dev`, `*dev`, `is_dev_slug` or
`dev_base_for_slug`: 7, 10, 3 and 5 files (driven).

## Order of work

1. **An import-graph guard** in `tests/meta` (REV-956 finding 16), seeded from the graph as it is.
   The next two steps change package edges, and the guard makes each one a deliberate line.
2. **Move `RoleView` and `OperatorView` to `_roles/`** (finding 2). The two structural protocols
   go. No behaviour change.
3. **Move role-to-type, role-to-skill and lane derivation out of `_interactions/__init__.py`** into
   a named module: the part of finding 5 that this change rewrites. No behaviour change.
4. **Declare and resolve.** `capabilities` on the spec, the definition and the view;
   `[dev].capabilities`; the template read from the active catalog; required arguments on that path
   (the part of finding 6 this change touches). The additive `--json` keys appear. No consumer is
   switched.
5. **Switch the consumers** and delete the spelling sites (decisions 1, 2 and 7). Tests are a table
   of role shape by surface. Shapes: templated, declared with the capability, suffixed `-dev`
   without it, bundled. Surfaces: pointer skills, shared section, create lane, `sq dev list`,
   generated text.
6. **Storage and fallbacks** (decisions 4, 5 and 6), the migration contribution, and this
   repository's squad.
7. **Docs, changelog and the stability refresh.**

Steps 1 to 3 can merge before any behaviour changes. Not preconditions, and not made harder by
this: extracting the roster projection from `ServiceCore` (finding 3), the rest of findings 5
and 6, and a single composition function (finding 15).

## Left out

- **The template's prose as data in `[dev]`.** Title, mission and responsibilities stay composed in
  Python. Moving them needs a placeholder grammar, which is a new frozen surface, and no spelling
  depends on it.
- **`extra.model` stamped at creation.** `sq dev add` without `--model` stores the catalog default
  (driven), so a later change to `[dev].model` does not reach that developer. It is the stamped
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
<!-- sq:discussion:end -->
