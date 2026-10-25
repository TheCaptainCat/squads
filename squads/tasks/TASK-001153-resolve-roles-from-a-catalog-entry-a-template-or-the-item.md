---
id: TASK-1153
sequence_id: 1153
type: task
title: Resolve roles from a catalog entry, a template or the item
status: Ready
author: tech-lead
priority: medium
refs:
- MILE-1051:targets
- ADR-1151:implements
- BUG-1075:fixes
- BUG-1065:fixes
- BUG-1030:fixes
- TASK-1137
description: 'ADR-1151: three role bases, [templates.<name>], sq role add, per-kind
  update, migration, checks, playbook, client hover'
subentities:
- local_id: ST1
  title: Declare role templates as data in the role catalog
  status: Todo
- local_id: ST2
  title: Resolve the base from stored facts and let stored values win
  status: Todo
- local_id: ST3
  title: Create roles through activate --from, role add and dev add
  status: Todo
- local_id: ST4
  title: Edit an item-defined role with update, refuse it elsewhere
  status: Todo
- local_id: ST5
  title: Extend the 0.17 migration and refuse a legacy [dev] table
  status: Todo
- local_id: ST6
  title: Report unresolved bases and shadowing files in sq check
  status: Todo
- local_id: ST7
  title: Check playbook guide slugs for grammar only at load
  status: Todo
- local_id: ST8
  title: Read the mention hover description from sq role list --json
  status: Todo
- local_id: ST9
  title: Document role bases, templates, role add and the [dev] rename
  status: Todo
created_at: '2026-10-25T22:01:52Z'
updated_at: '2026-10-25T22:07:45Z'
---
<!-- sq:body -->
## Goal

Implement ADR-1151. A role item holds its identity and the values its verbs set; its definition is projected from exactly one base, chosen from stored facts in the order `template`, `mission`, catalog. A team creates a custom role with `sq role add` instead of an override file, declares role templates as `[templates.<name>]` data in the role catalog, edits an item-defined role with `update`, and `sq check` reports every role whose base does not resolve.

Read `sq decision 1151 show --full --comments` before starting a subtask: each body below cites the decision it implements and does not restate it.

## Parent

No open feature fits. ADR-984's feature (FEAT-986) is Done in the 0.16 milestone and TASK-1137 has no parent, so this task targets MILE-1051 with no parent.

## Carried from TASK-1137

ST2 carries TASK-1137 ST1 (BUG-1075, stored `is_default` on a catalog-less role) and ST2 (BUG-1065, stored `model` on any role) as the "stored values win" step of decision 1, with their test tables. ST3 carries TASK-1137 ST4 (BUG-1030): the reserved-slug refusal lands on `sq role add`, and `sq override scaffold --new` is retired. TASK-1137 keeps its ST3 (`init --roles` against the project catalog), which this decision does not touch.

## Read on release/0.17 HEAD (2026-10-25)

- `[dev]` in `_specs/roles.toml`; `dev_role_from_pool`, `RoleDef.from_item`, `RoleDef.to_item_fields` and `_ITEM_FIELD_PROJECTION` in `_roles/_catalog.py`; `role_base_from_item`, `dev_base_from_item`, `resolve_dev_role` and `project_role_slugs` in `_roles/_resolver.py`.
- `attrs.is_templated` (`_models/_attributes.py`) is read by `_roles/_resolver.py`, `_itemfile.py`, `_services/_maintenance.py`, `_services/_roster.py` and `_interactions/_skills.py`.
- `[items.role.attributes]` in `_specs/workflow.toml` declares `is_default`, `model`, `origin`, `pronouns`, `tech` only.
- `_refresh_catalog_attributes` (`_services/_maintenance.py`) rewrites the stored `description` from the resolved mission on `sq sync`.
- `add_dev` (`_services/_roster.py`, `_cli/_dev.py`); `scaffold_new_role` (`_overrides/_service.py`, `_cli/_override.py`).
- `project_role_slugs` is called by the playbook loader (`_interactions/_loader.py`).
- The 0.16 to 0.17 runner (`_migrations/_v0_16_to_v0_17.py`) rewrites nothing today.
- The VS Code mention hover reads `description` from `sq list -t role --json` (`clients/vscode/src/domain/roleDirectory.ts`).

## Owners and ordering

ST1 to ST7 python-dev, ST8 typescript-dev, ST9 tech-writer.

ST1 to ST7 share `_roles/`, `_services/_roster.py` and the role CLI, so one python-dev runs them in order in one pass rather than several devs in parallel: ST1, ST2, then ST3 and ST4, then ST5, ST6, ST7. ST8 starts once ST2 has landed the `description` field on `sq role list --json`, and ships in the same release as ST2 (decision 3: both sides change together). ST9 runs last, against the merged behaviour.

## The test suite rebuild

FEAT-1096 is rebuilding the suite. The tests added here go into today's tree; each subtask's handoff lists its new test names so the parity ledger (TASK-1111) carries them forward.

## Gates

`uv run --all-extras pyright`, `ruff check .`, `ruff format --check .`; `pytest -n 4` on the touched directories plus `tests/meta`, `tests/integration` and `tests/cli` (the change touches `_specs/` and the CLI). Grep each changed role message, JSON key and spec key across `tests/` and run that union. Regenerate the template manifest and goldens if a rendered template changes. Each test table is falsified before handoff: break the mechanism, watch the rows go red, restore. No ticket ids in source, tests or docs; comments one or two sentences, stating present truth. `~/.local/bin/sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1153 add-subtask "<title>"`; track with `sq task 1153 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare role templates as data in the role catalog

<!-- sq:subtask:ST1:body -->
Owner: python-dev. First. Implements ADR-1151 decision 2.

**Where.** `_specs/roles.toml` (`[dev]` becomes `[templates.dev]`, carrying the title, description, mission and responsibilities that are Python literals today); `_roles/_models.py` (a template spec model with the closed key space); `_roles/_loader.py` (the catalog document's top-level keys become `roles`, `bundles`, `templates`, `defaults`, `selected`; `[selected]` gains `templates`); `_roles/_catalog.py` (`dev_role_from_pool` gives way to one template instantiation that reads only the table).

**What.**
- Template keys: `title`, `description`, `mission` required; `responsibilities`, `agreements`, `model`, `color`, `can_spawn`, `capabilities` with their `[[roles]]` meaning and validation; template-only `slug`, `name`, `name_pool`. `full_name` and `is_default` refused.
- Placeholders `{tech}`, `{Tech}`, `{first}` (in `name` only), `{{`/`}}` escapes; any other `{…}` refused at load, naming the template and the key. A template using `{tech}`/`{Tech}` takes a parameter. The substituted `slug` is slugified.
- Templates declared in the bundled catalog or `.overrides/roles.toml`, field-wise with splat-refs; splat-refs resolve before placeholder substitution.
- A legacy `[dev]` table in `.overrides/roles.toml` fails to load with exactly decision 2's message (file, rename, unchanged keys). No alias.

**Tests** (one table each):
- Placeholder shapes: `{tech}`, `{Tech}`, `{first}` in `name` and outside it, `{{tech}}`, an unknown `{x}`, a template with no placeholder given `--tech`, one with a placeholder given none. Assert the instantiated value or the load refusal naming template and key.
- Key space: each required key missing, `full_name`, `is_default`, an unknown key, a bad `color`/`model`/capability name. Assert refusal text.
- Override shapes: a new template, a field-wise change, `responsibilities = ["$(*self)", "Run the {Tech} linters"]`, `[selected] templates` dropping `dev`, a legacy `[dev]` (the exact message).
- Falsification, "template text is data": a `.overrides/roles.toml` changing `[templates.dev].mission` reaches an existing developer on the next `sq sync`. With the Python literals restored, red. (The sync leg needs ST2's resolver; write the row here and make it pass in ST2.)
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Resolve the base from stored facts and let stored values win

<!-- sq:subtask:ST2:body -->
Owner: python-dev. After ST1. Implements ADR-1151 decisions 1, 3 and 7 (the read side), and carries TASK-1137 ST1 (BUG-1075) and ST2 (BUG-1065).

**Where.** `_specs/workflow.toml` `[items.role.attributes]` (declare `template`, `job_title`, `mission`, `responsibilities`, `agreements`, `color`, `can_spawn`, `capabilities`, `settable = false`); `_models/_attributes.py` (a `template` accessor; `is_templated` becomes `template(item) is not None`); its readers in `_roles/_resolver.py`, `_itemfile.py` (skew exemption), `_services/_maintenance.py` (stored-key sweep), `_interactions/_skills.py` (origin) and `_services/_roster.py` (name-pool position counts the roles storing the same template); `_roles/_catalog.py` (`to_item_fields` and `_ITEM_FIELD_PROJECTION` go; `RoleDef.from_item` stops being a silent fallback); `_services/_maintenance.py` `_refresh_catalog_attributes` (no `description` write); the `sq role list --json` row (`_cli/_role.py`).

**What.**
- The base kind comes from stored facts only, `template` then `mission` then catalog; the catalog is never consulted to decide it.
- Resolution: build the base, merge `.overrides/roles/<slug>.toml` over it, then apply the stored name, `is_default`, `model` and `pronouns`. A stored value wins over every layer, for every base kind.
- A role whose base does not resolve still materialises from what it stores (ST6 reports it).
- Catalog and template roles store no `description`; `sq role list --json` rows gain the resolved one-line `description`. `origin` is `system` when the base is a bundled entry or bundled template, else `project`.
- A template role stores `model` only when `--model` was given. The repair removal set shrinks to `full_name`, `skills`, `is_dev`.
- An invalid stored model is refused at the write with the resolver's whitelist message.

**Tests** (one table each):
- Falsification, "kind is stored, not looked up": an item-defined `sre`, then a project `[[roles]]` entry `sre` with a different mission; `sq role sre show` and the pointer keep the item's mission. Make the resolver consult the catalog first: red.
- Kind × layer: catalog, template and item-defined role, each with and without a per-slug file and a stored model/default/pronouns; assert `role show --json` and the pointer.
- Stored default designation (TASK-1137 ST1): project role file only + `set-default`; previous default archived; bundled role; default moved away. Assert `role list` Default, `show --json`, CLAUDE.md line.
- Stored model on any role (TASK-1137 ST2): bundled reviewer haiku; project role whose file says sonnet, stored haiku; developer haiku; no stored model (catalog model); `opuss` via import (refused, nothing written).
- JSON surfaces: `sq list -t role --json` `description` empty on catalog and template roles and the stored value on an item-defined one; `sq role list --json` carries the resolved description for all three.
- Origin: bundled entry, overridden bundled entry, bundled template, project `[[roles]]`, project template, item-defined.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Create roles through activate --from, role add and dev add

<!-- sq:subtask:ST3:body -->
Owner: python-dev. After ST2. Implements ADR-1151 decision 4 and the scaffold retirement of decision 5; carries TASK-1137 ST4 (BUG-1030).

**Where.** `_cli/_role.py` (`activate --from`, `--tech`, new `add`), `_cli/_dev.py` (`dev add` as an alias, `dev list` re-keyed), `_services/_roster.py` (one creation method; `add_dev` and `resolve_dev_role` fold into it), `_models/_participants.py` (`reserved_role_slug_problem`, shared), `_cli/_override.py` and `_overrides/_service.py` (`scaffold --new` / `scaffold_new_role` retired).

**What.**
- `sq role activate <slug>` (catalog), `sq role activate [<slug>] --from <template> [--tech …]`, `sq role add <slug> --name … (--file <toml> | --job-title … --desc … --mission …)`, `sq dev add --tech <t> [--slug …]`. All go through one service method with one reserved-slug check, one duplicate-slug check and one materialisation path.
- `<slug>` is optional with `--from` only when the template declares a `slug` pattern. Name: `--name`, else a per-slug `full_name`, else the `name` pattern from `name_pool` at the count of roles storing that template; with no pattern, `--name` is required.
- `--file` reads the per-slug override grammar (`full_name` for the name, `title` for the job title); flags beside it win; every missing required field named in one message, exit 1, nothing written. Capabilities validated against `CAPABILITY_NAME_PATTERN`.
- `sq dev add --tech x [--slug s]` is exactly `sq role activate [s] --from dev --tech x`; its help says so. With the `dev` template dropped it exits 1 naming the declared templates. `sq dev list` lists live roles holding a capability `[templates.dev]` declares.
- `sq role activate <slug>` for a slug only a per-slug file declares exits 1 naming `sq role add <slug> --file .overrides/roles/<slug>.toml`. `sq override scaffold --new` exits 1 pointing at `sq role add`.

**Tests** (one table each):
- Creation: catalog activate; `--from dev --tech python`; `--from` with and without a slug pattern and with no slug given; `--tech` required, refused; each name-precedence leg; pool position with two templates; duplicate slug.
- Alias equivalence: `sq dev add` and `sq role activate --from dev` on the same inputs (success, missing `--tech`, duplicate, dropped template) give the same stdout, exit code and stored frontmatter.
- `role add`: flags only; `--file` only; `--file` plus overriding flags; missing fields (all named, nothing written); bad capability name.
- Reserved slugs (from TASK-1137 ST4), for `role add` and `activate --from`: `squads`, `operator`, `op-foo`, a role-group verb name, `sre` (control).
- Pointers: activate on a per-slug-only slug; `override scaffold --new`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Edit an item-defined role with update, refuse it elsewhere

<!-- sq:subtask:ST4:body -->
Owner: python-dev. After ST2; beside ST3. Implements ADR-1151 decision 5.

**Where.** `_cli/_role.py` (the role `update` verb and its flags), `_services/_roster.py` (the update service path), `_specmerge.py` (the field-wise delta for `--file`), `_services/_import.py` (import events that set item-defined fields).

**What.**
- `--title`, `--pronouns`, `--model` (blank clears) on every kind. `--job-title`, `--desc`, `--mission`, `--capabilities`, `--color`, `--can-spawn yes|no` and `--file <toml>` on an item-defined role only; `--file` is a field-wise delta through the shared merge engine, `$(*self)` resolving against the item's current definition.
- On a catalog or template role those flags exit 1, write nothing, and name the override path and its scaffold command (`sq override scaffold --role <slug>`); a template role's message adds `[templates.<name>]` of `.overrides/roles.toml` for a change to every role built from it.
- `tech` and `template` are not updatable. `--file` refuses `slug`, `full_name`, `is_default`, naming `update --title` and `set-default`.
- A write to a field a per-slug file also sets still happens and warns that the file wins.
- `update --job-title … --desc … --mission …` on an orphan custom role makes it item-defined (decision 6's remedy).
- `sq import` events setting item-defined fields are refused on the same terms.

**Tests.** Falsification, "`update` per kind × field": one table over decision 5's matrix (three kinds × each flag, `--file` with a delta, `--file` with `$(*self)`, each refused key), asserting exit code, stored frontmatter before and after, and the message naming the override path. Plus rows for the shadowing warning, the orphan made item-defined, `--model ""` on a developer (follows the template afterwards), and the import refusal.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Extend the 0.17 migration and refuse a legacy [dev] table

<!-- sq:subtask:ST5:body -->
Owner: python-dev. After ST3 and ST4. Implements ADR-1151 decisions 6 and 7 (the write side) and the migration leg of decision 2.

**Where.** `_migrations/_v0_16_to_v0_17.py` (runner, `SUMMARY`, `MANUAL`), the pre-runner check in `sq migrate up` (`_cli/_migrate.py` with `_services/_corpus_fit.py`, where the reconciled index is checked before the first runner). 0.17 is unreleased: extend this runner, no schema bump.

**What.**
- Before the first runner, `sq migrate up` reads `.overrides/roles.toml`; if it carries `[dev]`, exit 1 with decision 2's message and write nothing. The table is never renamed by the migration.
- For each role with no `tech`, no entry in the run's catalog, and a per-slug file that loads as a complete role: write the file's `title`, `description`, `mission`, `responsibilities`, `agreements`, `color`, `can_spawn`, `capabilities` into the item (`job_title`, the core `description`, …) and its `model` as the stored model. Name and file untouched.
- `template: dev` on every role storing `tech`; a stored developer `model` kept as written.
- The stored `description` cleared on catalog and template roles.
- A broken file and an orphan (no file, no catalog entry) are listed in the run's report and never guessed into a definition. A project `[[roles]]` entry is a catalog base and is not migrated.
- `MANUAL` and the changelog text tell adopters to rename `[dev]` to `[templates.dev]` before upgrading.
- This repo's own squad is brought up to date with the extended migration (no `.overrides/roles.toml` here; two developers gain `template: dev`, eight catalog roles lose the stored description). Running it on the live squad is the operator's call: hand back the exact command and the expected diff, do not run it.

**Tests.** Falsification, "migration", one table: a complete file-only custom role (definition moved, file byte-identical, `sq role show` identical before and after, `role_definition_shadowed` warns); a broken file (reported, untouched); an orphan (reported, untouched); a `[[roles]]` project entry (untouched); a developer (`template: dev` written, `model` kept); a catalog role (`description` cleared). After each run, `sq repair` rebuilds the same index. Plus a `[dev]` row: exit 1, the message, every file's hash unchanged and the schema not stamped.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Report unresolved bases and shadowing files in sq check

<!-- sq:subtask:ST6:body -->
Owner: python-dev. After ST5. Implements ADR-1151 decision 8.

**Where.** `_services/_check_rules.py` (the registered rules), `_services/_validators.py`, `_workflow/_validator_names.py` (new rule names), `_overrides/_service.py` (`override_loads` / `override_stamped` classification).

**What.**
- `role_base_resolves` (new, squad-global, error): a catalog role whose slug the catalog no longer declares; a template role naming an undeclared template; a template role missing the `tech` its template requires or carrying one it does not take; an item-defined role missing `job_title`, `description` or `mission`; a role storing both `template` and `mission`.
- `override_loads`: a per-slug file with no role under it (no item, no catalog entry), partial or complete, is a layer with no base, remedy `sq role add <slug> --file <path>` or create the role first. Replaces "missing required fields for new slug". A `[dev]` table in `.overrides/roles.toml` is reported with decision 2's message.
- `override_stamped`: the stamp is required only when the base comes from the bundled document (bundled entry or bundled template).
- `role_definition_shadowed` (new, squad-global, warn): a per-slug file sets a field an item-defined role stores; names the file and the fields.
- `playbook_guide_role_live`: also reports a guide naming a slug no role holds (the loader check moves here in ST7).
- `attribute_valid` and `frontmatter_key_undeclared` cover the new role attributes with no rule change.

**Tests.** One table per rule, each row a squad state and the expected finding or none, asserting rule name, severity, entry and remedy text: each `role_base_resolves` leg plus a clean row per kind; per-slug file with no base (partial, complete) and over each base kind; stamp present/absent over each base origin; shadowed field (one, several, none); `[dev]` reported; a typo'd guide slug. Each new rule appears in the named-rule registry (`tests/meta`).
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Check playbook guide slugs for grammar only at load

<!-- sq:subtask:ST7:body -->
Owner: python-dev. After ST6 (the finding that replaces the load-time check). Implements ADR-1151 decision 9.

**Where.** `_interactions/_loader.py` (the guide-subject check), `_roles/_resolver.py` (`project_role_slugs` and the override-file scan, removed).

**What.**
- A playbook guide's subject slug is checked at load for grammar only. Whether a role holds it is reported by `playbook_guide_role_live`, on the terms a `*<capability>` guide with no holder already is.
- `project_role_slugs` and the loader's scan of `.overrides/roles/` go. The playbook load reads no role item files.
- Capabilities resolve from whichever base holds them, so a `*<capability>` guide addresses an item-defined holder like any other.

**Tests** (falsification, "playbook", one table): a playbook override naming an item-defined role loads, and the role preloads the skill (pointer and `sq role show`); a typo'd slug loads and is reported by `playbook_guide_role_live`; a grammatically invalid subject is still refused at load; a `*<capability>` guide reaches an item-defined role declaring that capability. Restore the loader's slug check and the first two rows go red.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Read the mention hover description from sq role list --json

<!-- sq:subtask:ST8:body -->
Owner: typescript-dev. After ST2 lands `description` on `sq role list --json`; ships in the same release. Implements the client leg of ADR-1151 decision 3.

**Where.** `clients/vscode/src/domain/roleDirectory.ts` (the `@mention` hover's role directory); `clients/vscode/src/itemPreviewManager.ts`, which feeds it from `getList(… ['-t', 'role'])`; `clients/vscode/src/sqAdapter.ts`, whose `getRoleIdentities` already runs `sq role list --json` and whose `SqRosterIdentity` guard gains `description`.

**What.** The hover reads a role's one-line description from the `description` field of `sq role list --json` instead of `sq list -t role --json`, whose role rows no longer carry the mission on catalog and template roles. The doc comment above the read names the new source.

**Tests.** In the client suite, one table over role rows: a catalog role, a template role and an item-defined role, each with a description, and one with an empty description; assert the hover text. A canary that feeds the old `sq list -t role` shape must not produce a description (the hover is not reading the old surface). Gates: `npm run lint` and `npm test` in `clients/vscode`.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Document role bases, templates, role add and the [dev] rename

<!-- sq:subtask:ST9:body -->
Owner: tech-writer. Last, against the merged behaviour of ST1 to ST8. Implements the docs owed by ADR-1151's consequences and decision 10.

**Where and what.**
- `docs/roles.md`: the three base kinds and how the kind is decided; `sq role activate --from`, `sq role add` (flags and `--file`), `sq dev add` as an alias; role templates (`[templates.<name>]`, the three placeholders and their escape, the name rules); `update` per kind and its refusals.
- `docs/overrides.md`: custom roles leave overrides; a per-slug file is a layer over an existing role; the layer-with-no-base finding; `sq override scaffold --new` retired; `[selected] templates`.
- `docs/stability.md`: decision 10's frozen surface, including the catalog document's top-level keys (`roles`, `bundles`, `templates`, `defaults`, `selected`), the stored role keys, the shrunk repair removal set, and what is not frozen.
- `docs/migration.md` and the 0.17 `CHANGELOG.md` section: rename `[dev]` to `[templates.dev]` in `.overrides/roles.toml` before upgrading, or `sq migrate up` refuses; file-only custom roles move into their item and the file then shadows it until deleted; the stored `description` change on `sq list -t role --json`.
- `docs/internals.md`: any mention of `[dev]` or the dev generator.

**Check.** Every command and message quoted is driven on a scratch squad outside the repo with the dev tree, not copied from the ADR. Adopter-facing text carries no item ids and no build-process narration.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T22:06:38Z] `tech-lead` Olivia Lead:
  - Drafted from ADR-1151 (Accepted; op-pierre: ships in 0.17). No open feature fits as parent (FEAT-986, ADR-984's feature, is Done in 0.16), so the task targets MILE-1051 with no parent.
  - TASK-1137 ST1/ST2 are carried by ST2 and ST4 by ST3, with their test tables and bug refs; TASK-1137 keeps ST3 alone, because init --roles is a different surface that ADR-1151 does not touch.
  - ST1 to ST7 are one python-dev pass in order (shared _roles/, _services/_roster.py, role CLI). ST5 hands the live-squad migrate command back to the operator rather than running it. Draft until dispatch.
<!-- sq:discussion:end -->
