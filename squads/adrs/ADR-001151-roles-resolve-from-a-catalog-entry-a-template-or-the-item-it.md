---
id: ADR-1151
sequence_id: 1151
type: decision
title: Roles resolve from a catalog entry, a template, or the item itself
status: Accepted
author: architect
refs:
- ADR-754
- ADR-777
- ADR-1128
- TASK-1137
- ADR-984
description: 'A role item is identity plus verb-set values; its definition projects
  one base: catalog, [templates.<name>], or the item'
created_at: '2026-10-25T20:43:13Z'
updated_at: '2026-10-25T22:06:44Z'
---
<!-- sq:body -->
## Context

A role item today stores its identity and a few operator settings: `slug`, `status`, the stored
name in `title`, `is_default`, `pronouns`, `origin`, and for a developer `tech` and `model`. Its
definition (job title, one-line description, mission, responsibilities, agreements, colour,
`can_spawn`, capabilities) is resolved on every read by `resolve_role_for_item`, from one of three
sources (read, `_roles/_resolver.py`, `_roles/_catalog.py`, `_services/_roster.py` on
`release/0.17`, 2026-10-25):

- **A catalog entry.** The bundled `roles.toml` with `.overrides/roles.toml` merged in, then the
  per-slug `.overrides/roles/<slug>.toml` merged over it.
- **The dev generator.** `dev_role_from_pool(tech, catalog().dev, …)`. The `[dev]` table holds only
  the name pool, model, colour and capabilities. The title, description, mission and
  responsibilities are Python string literals built around `tech`, so a project cannot change
  them in one place. The role counts as "templated" when it stores `tech` (`attrs.is_templated`),
  and that boolean decides the base, the skew exemption, the stored-key sweep, the origin and the
  name-pool position.
- **A per-slug file alone.** A custom role is a `.overrides/roles/<slug>.toml` for a slug no
  catalog declares, and that file must carry every required field. Without the file the item
  falls back to `RoleDef.from_item`, which takes the title for the job title and the stored
  `description` for the mission, and no finding reports it.

**What fails.**

1. **A custom role has to be defined in an override.** Overrides exist to modify a bundled
   document, so the file a team writes to *create* a role is classified, stamped, drift-checked
   and diffed as a modification of something that does not exist. ADR-754's 2026-10-25 amendment
   had to rule on whether a partial file for an unknown slug is a new role or a modification;
   the file cannot say which. op-pierre, 2026-10-25: going through overrides for custom roles is
   wrong.
2. **The dev template is half data, half code.** A second template (a security reviewer per
   stack, a writer per language) cannot be declared: `[dev]` is the only table, and its prose is
   hard-coded.
3. **"Templated" is a boolean read off a parameter.** With a second template, the presence of
   `tech` cannot say which template built the role, and a template without a parameter would
   leave no trace at all.
4. **The stored `description` is a sync-refreshed copy of the mission.** `RoleDef.to_item_fields`
   projects `mission` onto the item's `description`, and `sq sync` rewrites it whenever the
   resolved mission changes (`_services/_maintenance.py`, `_refresh_catalog_attributes`). It is
   not "copied at creation and never read again": it is read by the generic surfaces that do not
   resolve roles, among them the VS Code client's `@mention` hover, which reads the `description`
   field of `sq list -t role --json` (read, `clients/vscode/src/domain/roleDirectory.ts`). It is
   also the wrong field, because the generated pointer uses the definition's one-line
   `description`, not the mission.
5. **The playbook loader checks a guide's role slug at load time** against the catalog plus the
   per-slug override files (`project_role_slugs`), because those can be read before the index.
   A role defined in its item cannot be seen there.

TASK-1137 fixes four role-resolution bugs in the same seam. ST1 (a stored `is_default` on a
catalog-less role) and ST2 (a stored `model` on any role, per op-pierre's ruling on BUG-1065) are
the per-item precedence this decision assumes. ST3 (`init --roles` against the project catalog)
is orthogonal. ST4 (reserved slugs in `sq override scaffold --new`) is affected by decision 5.

## Decision

op-pierre ruled the eight open points on 2026-10-25, and each ruling is written into the decision it belongs to: the kind marker is the stored `mission` (1); placeholders, naming and the refusal of a legacy `[dev]` (2); the stored `description` and `job_title` (3); `--from` and `--job-title` (4, 5); retiring `sq override scaffold --new` (5); a per-slug file with no role under it is an error, and orphans are reported, never guessed (6).

### 1. A role is an identity over one base

A role item holds its identity and the values that dedicated verbs set. Its definition is a
projection of exactly one **base**, resolved on every read. There are three kinds of base.

| Base | Where the definition comes from | Decided by |
|---|---|---|
| **Catalog** | The slug's entry in the bundled `roles.toml`, with `.overrides/roles.toml` merged in. Unchanged. | Neither of the next two |
| **Template** | A `[templates.<name>]` table of the same merged catalog, instantiated with the item's `tech` | The item stores `template` |
| **Item** | The item's own definition fields | The item stores `mission` |

The kind is decided **from stored facts only, in that order: `template`, then `mission`, then
the catalog.** The catalog is never consulted to decide the kind. If it were, a later bundled
release or a project `[[roles]]` entry declaring a custom role's slug would silently swap that
role's definition. A role storing both `template` and `mission` is a finding (decision 8).

Resolution is the same for all three kinds:

1. build the base;
2. merge `.overrides/roles/<slug>.toml` over it when present, as ADR-754 and ADR-777 describe:
   field-wise, with the shared engine and the typed `RoleSpec`;
3. apply the item's stored per-role values last: the name (pinned, as today), `is_default`,
   `model` and `pronouns`. A stored value wins over every layer (TASK-1137 ST1/ST2).

The `[templates.<name>]` tables and the item-defined fields are read from documents already in
hand. Resolution adds no load, so ADR-1128's load-once rule holds unchanged.

### 2. Template grammar

`[dev]` becomes the first entry of a keyed `[templates]` section of the role catalog document.
The bundled table carries what `dev_role_from_pool` hard-codes today:

```toml
[templates.dev]
slug = "{tech}-dev"
name = "{first} {Tech}"
name_pool = ["Elias", "Ada", "Linus", "Grace", "Dennis", "Margaret", "Alan", "Barbara", "Ken", "Edsger", "Radia", "Donald"]
title = "{Tech} developer"
description = "Implements {Tech} code following the project's guides and standards."
mission = "Implement assigned tasks in {Tech}, following the project's guides, with tests."
responsibilities = [
  "Implement tasks in {Tech}",
  "Write tests for changes",
  "Follow the relevant guides; ask the architect when unsure",
]
model = "sonnet"
color = "green"
capabilities = ["dev"]
```

- **Keys.** The key space is closed: `title`, `description`, `mission`, `responsibilities`,
  `agreements`, `model`, `color`, `can_spawn` and `capabilities`, each with the meaning and
  validation it has on a `[[roles]]` entry, plus three template-only keys. `slug` is the
  proposed slug pattern. `name` is the name pattern. `name_pool` is the list `{first}` draws
  from. `title`, `description` and `mission` are required. `full_name` and `is_default` are
  refused: the name is chosen at activation and the designation belongs to an item.
- **Placeholders.** Exactly three: `{tech}` (the value given to `--tech`), `{Tech}` (the same
  with its first letter upper-cased) and `{first}` (a pool entry, valid in `name` only). `{{` and
  `}}` escape a literal brace. Any other `{…}` is refused at load, naming the template and the
  key. A template that uses `{tech}` or `{Tech}` anywhere takes a parameter: activation requires
  `--tech` and refuses it otherwise. In `slug`, the substituted value is slugified.
- **Name.** At activation, `--name` wins. Otherwise a `full_name` in a per-slug file present at
  that moment wins. Otherwise the `name` pattern applies, drawing `{first}` from `name_pool` at
  the position given by the count of roles that already store this template. Without a `name`
  pattern, `--name` is required. The stored name is then the role's name (ADR-777, note of
  2026-10-16).
- **Where templates are declared.** In the bundled catalog or in `.overrides/roles.toml`. An
  override adds a template, or changes one field-wise with splat-refs (`responsibilities =
  ["$(*self)", "Run the {Tech} linters"]`). Splat-refs resolve against the bundled document
  first; placeholders are substituted when a role is instantiated, so the two never interact.
  `[selected]` gains `templates` beside `roles` and `bundles`.
- **A legacy `[dev]` table is refused, with no alias** (op-pierre, 2026-10-25). `[dev]` leaves
  the catalog document's key space, so a `.overrides/roles.toml` that still carries it fails to
  load, on the closed-key refusal every spec document has. The message names the file and the
  rename: `.overrides/roles.toml: [dev] is not a key of the role catalog; rename it to
  [templates.dev] (its name_pool, model, color and capabilities keys are unchanged)`. Every role
  command fails until the table is renamed, which is a one-line edit.
- **What `sq dev` keeps.** `sq dev list` lists the live roles that hold a capability
  `[templates.dev]` declares (ADR-984 decision 3, re-keyed). If a squad drops the `dev`
  template, `sq dev add` exits 1 naming the declared templates.

### 3. What the item stores

| | Every role | Template role | Item-defined role |
|---|---|---|---|
| Identity | `id`, `slug`, `status`, `title` (the name), `author`, timestamps, `origin`, the discussion | | |
| Per-role values, when a verb set them | `is_default`, `model`, `pronouns` | | |
| Base | | `template` (the template's name); `tech` when the template takes it | `job_title`, `mission`, `description` (core key: the one-line description); optional `responsibilities`, `agreements`, `color`, `can_spawn`, `capabilities` |

- Item-defined fields are declared role attributes (`settable = false`), so they are typed,
  `sq check`-validated and written only by role verbs. The item's core `description` *is* the
  definition's one-line description: one value, stored once. The job title is stored as
  `job_title` because the core `title` key holds the name (ADR-766).
- **On a catalog or template role, nothing is stored in `description`.** The projection of the
  mission into it is removed (`RoleDef.to_item_fields` and `_ITEM_FIELD_PROJECTION` go). The
  resolved one-line description is added to `sq role list --json` rows, and the VS Code client's
  mention hover reads it there. Every other generic surface keeps reading the core field: an
  item-defined role's value, or empty.
- `origin` stays required. It is `system` when the base is declared by the bundled document (a
  bundled catalog entry or a bundled template, overridden or not), else `project`. That is
  `role_origin` re-keyed from "templated" to "built from a bundled template".
- A template role's `model` is stored only when `--model` was given. Without it, the model
  follows the template, so a change to the template's `model` reaches existing roles.
- Nothing new enters the index that the files cannot rebuild.

### 4. One creation path per base kind, one service seam

```
sq role activate <slug> [--name …] [--model …] [--pronouns …]                    # catalog
sq role activate [<slug>] --from <template> [--tech …] [--name …] [--model …] [--pronouns …]
sq role add <slug> --name … (--file <toml> | --job-title … --desc … --mission …)
            [--capabilities a,b] [--model …] [--pronouns …]
sq dev add --tech <t> [--slug …] [--name …] [--model …] [--pronouns …]          # alias
```

- `activate` builds from a base declared elsewhere. `add` declares the base in the item, as
  `sq skill add` and `sq operator add` do. All three go through one service method with one
  reserved-slug check, one duplicate-slug check and one materialisation path. `add_dev` and
  `resolve_dev_role` fold into it.
- `--from` makes `<slug>` optional when the template declares a `slug` pattern. Otherwise
  `<slug>` is required.
- `sq dev add --tech x [--slug s]` is exactly `sq role activate [s] --from dev --tech x`: same
  messages, same result. Its help says so.
- `--file` reads the per-slug override grammar (`RoleSpec` keys, with `full_name` for the name
  and `title` for the job title), so a file written for an override can be passed unchanged.
  Flags given beside `--file` win over its keys. Missing required fields are named in one
  message, exit 1, nothing written.
- `sq role activate <slug>` for a slug that only a per-slug file declares exits 1 and names the
  command: `sq role add <slug> --file .overrides/roles/<slug>.toml`.

### 5. `update` edits an item-defined definition and refuses it elsewhere

`sq role <slug> update` takes:

| Flag | Catalog role | Template role | Item-defined role |
|---|---|---|---|
| `--title` (the name), `--pronouns` | yes | yes | yes |
| `--model` (blank clears) | yes | yes | yes |
| `--job-title`, `--desc`, `--mission`, `--capabilities`, `--color`, `--can-spawn yes\|no` | refused | refused | yes |
| `--file <toml>` (field-wise delta, the same grammar and engine as an override; `$(*self)` resolves against the item's current definition) | refused | refused | yes |

- **A refusal names the tool that does the job:** exit 1, nothing written, and the message
  gives the override path and its scaffold command, e.g. `architect's mission comes from the
  role catalog; set it in .overrides/roles/architect.toml (sq override scaffold --role
  architect)`. A template role's message adds that a change for every role built from the
  template goes in `[templates.<name>]` of `.overrides/roles.toml`.
- `tech` and `template` are not updatable: they choose the base, and a different one is a
  different role. `--file` refuses `slug`, `full_name` and `is_default`, naming `update
  --title` and `set-default`.
- When a per-slug file sets a field that `update` writes, the write still happens and the
  command warns that the file wins (decision 8 reports it too).
- `sq import` events that set item-defined fields are refused on the same terms.
- `sq override scaffold --new` is retired: `sq role add` replaces it and exits 1 with that
  pointer.

### 6. Existing custom roles defined only by an override file

**The unreleased 0.16→0.17 migration moves the definition into the item. The file stays, as a
layer.**

- For each role item that has no `tech`, no entry in the catalog the run resolves, and a
  per-slug file that loads as a complete role, the runner writes the file's `title`,
  `description`, `mission`, `responsibilities`, `agreements`, `color`, `can_spawn` and
  `capabilities` into the item (as `job_title`, the core `description`, and so on). It writes
  the file's `model` as the stored per-role model. The stored name is untouched.
- The file is not touched (`sq migrate` never rewrites overrides). It now merges over identical
  values, so nothing resolves differently. `sq check` warns that it shadows the item's
  definition (decision 8). Deleting the file is the remedy.
- A file that does not load is left alone and listed in the run's report. Its role is then
  unresolvable and reported (decision 8), with the same remedy as an orphan.
- An orphaned custom item (no file, no catalog entry) is not guessed into a definition. It is
  reported, and `sq role <slug> update --job-title … --desc … --mission …` makes it
  item-defined.
- A project `[[roles]]` entry in `.overrides/roles.toml` is a catalog base and is not migrated.
- A per-slug file whose slug has no role item and no catalog entry is a layer with no base.
  `sq check` reports it at error (decision 8), whether it is partial or complete. This narrows
  the 2026-10-25 amendment of ADR-754: its second flow ("write a complete override first") now
  works only once the role exists. `sq role add <slug> --file <that file>` turns such a file
  into a role in one command.

### 7. `is_templated` becomes the stored template name

- The same runner writes `template: dev` on every role item that stores `tech`. `tech` stays as
  the template's parameter (ADR-984 decision 4, narrowed: the presence of `tech` no longer
  decides the base; `template` does).
- `attrs.is_templated(item)` becomes `attrs.template(item) is not None`. Its readers (the
  resolver, the skew exemption in `_itemfile.py`, the stored-key sweep, `item_origin`, the
  name-pool count) read `template`, and the pool position counts the roles that store the same
  template.
- A developer's stored `model` is kept as written. It may be an operator setting, and keeping it
  changes nothing. `update --model ""` clears it, after which the role follows the template.
- The stored `description` on catalog and template roles is cleared by the same runner
  (decision 3).
- 0.17 is unreleased, so this extends its migration with no schema bump.
- **A legacy `[dev]` table stops the migration before its first runner.** `sq migrate up`
  checks `.overrides/roles.toml` first and, if it carries `[dev]`, exits 1 with decision 2's
  message and writes nothing. It does not rename the table, because `sq migrate` never rewrites
  overrides (`docs/stability.md`). Refusing up front means a squad never ends up half-migrated
  behind a roles document that will not load. The adopter renames the table and runs `sq migrate
  up` again. The 0.17 migration notes (`sq migrate chlog`, the runner's `manual` text) and the
  CHANGELOG tell adopters to rename `[dev]` to `[templates.dev]` before upgrading.

### 8. `sq check`

| Rule | Change |
|---|---|
| `role_base_resolves` (new, squad-global, error) | A live role whose base does not resolve: a catalog role whose slug the catalog no longer declares (today rendered silently from `RoleDef.from_item`); a template role naming an undeclared template; a template role missing the `tech` its template requires, or carrying one it does not take; an item-defined role missing `job_title`, `description` or `mission`; a role storing both `template` and `mission`. `sq sync` keeps materialising such a role from what it stores, and this finding is what reports it. |
| `override_loads` | A per-slug file with no role under it (no item, no catalog entry) is reported as a layer with no base, with the remedy `sq role add <slug> --file <path>` or "create the role first". This replaces "missing required fields for new slug". |
| `override_stamped` | A per-slug file must carry the stamp when its base comes from the bundled document (a bundled catalog entry or a bundled template). Over an item-defined role, or a project-declared entry or template, it needs none. |
| `role_definition_shadowed` (new, squad-global, warn) | A per-slug file sets a field that an item-defined role stores, so `update` of that field has no effect. Names the file and the fields. |
| `playbook_guide_role_live` | Also reports a guide naming a slug that no role holds. The playbook loader's role-slug check becomes grammar-only (decision 9). |
| `override_loads` (catalog document) | A `[dev]` table in `.overrides/roles.toml` is reported with the load refusal of decision 2, naming the file and the rename. |
| `attribute_valid`, `frontmatter_key_undeclared` | Cover the new declared role attributes (`template`, `job_title`, `mission`, `responsibilities`, `agreements`, `color`, `can_spawn`, `capabilities`) with no rule change. |

### 9. Capabilities and the playbook

- Capabilities resolve onto `RoleDef`/`RoleView` exactly as ADR-984 decision 2 says, from
  whichever base holds them: the catalog entry, the template, or the item. They are validated
  against `CAPABILITY_NAME_PATTERN` at the write for an item-defined role. A `*<capability>`
  guide addresses an item-defined holder like any other.
- A playbook guide's subject slug is checked at load **for grammar only**. Whether a role holds
  that slug is reported by `playbook_guide_role_live`, on the terms a `*<name>` guide with no
  holder already is (ADR-984 decision 1). `project_role_slugs` and the loader's override-file
  scan are removed. The rejected alternative is to have the loader read role item files: that
  makes a spec-document load depend on the corpus, which ADR-1128's resolution order does not
  allow before the index is open.

### 10. What `docs/stability.md` freezes for 1.0

- The three base kinds, and that the kind is decided from stored facts in the order `template`,
  `mission`, catalog.
- The resolution order: base, then the per-slug file, then stored per-role values (name,
  `is_default`, `model`, `pronouns`).
- The `[templates.<name>]` key space, the three placeholders and their escape, and `templates`
  as a `[selected]` section of `roles.toml`. The catalog document's top-level key space becomes
  `roles`, `bundles`, `templates`, `defaults`, `selected`.
- The stored role keys and their meanings: `template`, `tech`, `job_title`, `mission`,
  `responsibilities`, `agreements`, `color`, `can_spawn`, `capabilities`, `model`, and
  `description` as the item-defined one-line description. The closed set `sq repair` removes
  from a role shrinks to `full_name`, `skills` and `is_dev`. The other definition keys become
  declared attributes.
- The CLI: `sq role activate <slug>`, `sq role activate [<slug>] --from <template>`, `sq role
  add`, `sq dev add` as an alias, and `update`'s per-kind table with its exit-1, nothing-written
  refusals.
- Not frozen: the bundled templates' prose and pools, and the Python seams.

## Consequences

- Making a custom role no longer touches `.overrides/`. Overrides go back to modifying a base,
  so the stamp, drift and diff rules stop special-casing "a file that defines a new role".
- A project can declare a template with no code change, and change the dev template's prose in
  one table.
- `sq check` starts reporting two states it was silent on: an orphaned or deselected role
  (`role_base_resolves`) and a migrated custom role whose old file still shadows it
  (`role_definition_shadowed`). A per-slug file written before its role exists is an error
  whether partial or complete.
- `sq list -t role --json` rows of catalog and template roles stop carrying the mission in
  `description`, and `sq role list --json` gains `description`. The VS Code client's hover moves
  with it. Both sides change together.
- A squad whose `.overrides/roles.toml` carries `[dev]` cannot load its role catalog after the
  upgrade, and `sq migrate up` refuses until the table is renamed. The migration notes and the
  CHANGELOG say so.
- A typo'd role slug in a playbook override becomes an `sq check` finding instead of a load-time
  hard stop.
- TASK-1137 ST1 and ST2 land as written and are the per-role precedence of decision 1. ST4's
  reserved-slug refusal moves to `sq role add`, which shares `activate`'s check by construction,
  and `sq override scaffold --new` goes. ST3 is unaffected.
- Narrowed by this decision, each to carry a dated narrowing naming it: ADR-754's 2026-10-25
  amendment, flow 2 (decision 6); ADR-777 §3, the catalog document's key space (`dev` becomes
  `templates`); ADR-984 decisions 3 and 4 (the base is chosen by `template`, and `tech` is only
  its parameter).
- Docs owed by the tech writer: `docs/roles.md` (three kinds, `sq role add`, templates),
  `docs/overrides.md` (custom roles leave it; the layer-with-no-base finding), `docs/stability.md`
  (decision 10), and the CHANGELOG.

## Falsification the implementation owes

- **Kind is stored, not looked up.** An item-defined `sre`, then a project `[[roles]]` entry
  `sre` with a different mission: `sq role sre show` and the pointer keep the item's mission.
  Make the resolver consult the catalog first and the test must go red.
- **Template text is data.** A `.overrides/roles.toml` changing `[templates.dev].mission`
  reaches an existing developer on the next `sq sync`. With the Python literals restored, red.
- **Placeholder shapes**, one table: `{tech}`, `{Tech}`, `{first}` in `name` and outside it,
  `{{tech}}`, an unknown `{x}`, a template with no placeholder given `--tech`, one with a
  placeholder given none.
- **`update` per kind × field**, one table over decision 5's matrix, asserting exit code, stored
  frontmatter and the message naming the override path.
- **Migration**, one table: a complete file-only custom role (definition moved, file untouched,
  `sq role show` identical before and after, `role_definition_shadowed` warns), a broken file, an
  orphan, a `[[roles]]` project entry, a developer (`template: dev` written, `model` kept), a
  catalog role (`description` cleared). `sq repair` after the run rebuilds the same index.
- **Playbook.** A playbook override naming an item-defined role loads, and the role preloads the
  skill. A typo'd slug loads and is reported by `playbook_guide_role_live`.

## Rejected

- **Keep custom roles in per-slug files.** This is today's shape, and failure 1.
- **Store the definition in the body.** Capabilities, colour and `can_spawn` are values that
  `sq check` must type. Prose in the body beside values in the frontmatter would split one
  definition across two stores.
- **A nested `definition` mapping attribute.** The attribute grammar has no mapping kind, and
  adding one to a frozen grammar for a single type costs more than the eight flat keys.
- **An explicit `base: item` marker.** `mission` is required on an item-defined role and is
  written only by the role verbs, which refuse it elsewhere, so a marker would duplicate it.
- **Arbitrary template parameters.** Each would be a stored map per item, and no template has
  been asked for that `tech` does not cover.
- **An alias for a legacy `[dev]` table.** It would keep two spellings of one table loading until 1.0, for an edit of one line (op-pierre, 2026-10-25).
- **Deciding the kind by catalog lookup.** A catalog change would swap a live role's definition
  (decision 1).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T20:43:45Z] `architect` Robert Architect:
  - - Drafted from the 2026-10-25 direction (op-pierre with the manager). Code read on release/0.17; nothing driven. The manager's note that the stored `description` is "copied at creation and never read again" does not hold: `sq sync` refreshes it from the mission, and the VS Code mention hover reads it from `sq list -t role --json`. Decision 3 drops it on catalog and template roles and moves the hover to `sq role list --json`.
    - @op-pierre, open questions. Each has my recommendation, and the body is written to that recommendation.
      1. Kind marker. Recommend deriving "item-defined" from a stored `mission` (stored facts only, order `template` > `mission` > catalog). Alternative: an explicit `base` attribute.
      2. Stored `description` on catalog and template roles. Recommend dropping it, adding `description` to `sq role list --json` and moving the client hover there. Alternative: keep a copy that sync refreshes, set to the one-line description rather than the mission.
      3. An existing `[dev]` in `.overrides/roles.toml`. Recommend accepting it as an alias of `[templates.dev]` with an `override_current` warning, removed before 1.0. Alternative: refuse it at load, which fails every role command until the file is renamed.
      4. A per-slug file with no role under it. Recommend an error for both partial and complete files. This narrows the second flow of ADR-754's 2026-10-25 amendment (write a complete override first). Alternative: a complete file keeps loading as a new role, which keeps two ways to define a custom role.
      5. Template placeholders. Recommend exactly `{tech}`, `{Tech}` and `{first}`. Alternative: declared arbitrary parameters, stored as a map per item.
      6. Naming. Recommend `[templates.<name>]` in roles.toml with `--from` ("role template" in the docs, against the Jinja `.overrides/templates/`), and `job_title` / `--job-title` for the job title, since `update --title` is the frozen rename.
      7. `sq override scaffold --new`. Recommend retiring it in favour of `sq role add`. TASK-1137 ST4 then lands on `sq role add` (it shares activate's reserved-slug check) or is dropped.
      8. Orphaned custom roles (no file, no catalog entry) at migration. Recommend leaving them and reporting `role_base_resolves`, remedy `update --job-title/--desc/--mission`. Alternative: convert them from the item's title and description, which is a guess.
    - Refs added at both ends (ADR-754, ADR-777, ADR-984, TASK-1137). The dated narrowings in ADR-754, ADR-777 §3 and ADR-984 §3-4 are not written yet. I write them when you rule.
- [2026-10-25T21:04:49Z] `op-pierre` Pierre Chat:
  - Rulings on the eight questions:
  - Q1: a custom role is recognised by its stored mission; no base attribute.
  - Q2: drop the stored description on catalog and template roles; sq role list --json exposes it and the VS Code hover reads it there.
  - Q3: refuse a legacy [dev] table in .overrides/roles.toml; no alias.
  - Q4: a per-slug override with no role under it is an error, partial or complete.
  - Q5: template placeholders are exactly {tech}, {Tech} and {first}.
  - Q6: [templates.<name>], --from, "role template" in the docs; job title is job_title / --job-title.
  - Q7: retire sq override scaffold --new in favour of sq role add.
  - Q8: migration reports orphaned custom roles; it never guesses a definition.
- [2026-10-25T21:06:49Z] `architect` Robert Architect:
  - Folded the op-pierre rulings of 2026-10-25 into the body. Q3: a legacy [dev] in .overrides/roles.toml is refused at load with no alias, and the error names the file and the rename to [templates.dev]. sq migrate up refuses before its first runner, writing nothing, and does not rename the table, because migrate never rewrites overrides. The migration notes and the CHANGELOG tell adopters to rename the table before upgrading.
  - Dated narrowings written into ADR-754 (flow 2), ADR-777 section 3 and ADR-984 sections 3 and 4. @tech-writer the migration notes and the CHANGELOG owe the [dev] rename step.
- [2026-10-25T21:12:29Z] `manager` Catherine Manager:
  - Accepted: read in full; decisions 1-10 carry the operator rulings of 2026-10-25.
- [2026-10-25T21:13:41Z] `op-pierre` Pierre Chat:
  - This ships in 0.17.
- [2026-10-25T22:06:44Z] `tech-lead` Olivia Lead:
  - Broken down into TASK-1153 (nine subtasks, Draft). TASK-1137 now carries only its ST3.
<!-- sq:discussion:end -->
