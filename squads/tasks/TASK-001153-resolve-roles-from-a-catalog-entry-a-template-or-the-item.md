---
id: TASK-1153
sequence_id: 1153
type: task
title: Resolve roles from a catalog entry, a template or the item
status: InReview
author: tech-lead
assignee: python-dev
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
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Resolve the base from stored facts and let stored values win
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Create roles through activate --from, role add and dev add
  status: Done
  assignee: python-dev
- local_id: ST4
  title: Edit an item-defined role with update, refuse it elsewhere
  status: Done
  assignee: python-dev
- local_id: ST5
  title: Extend the 0.17 migration and refuse a legacy [dev] table
  status: Done
  assignee: python-dev
- local_id: ST6
  title: Report unresolved bases and shadowing files in sq check
  status: Done
  assignee: python-dev
- local_id: ST7
  title: Check playbook guide slugs for grammar only at load
  status: Done
  assignee: python-dev
- local_id: ST8
  title: Read the mention hover description from sq role list --json
  status: Done
- local_id: ST9
  title: Document role bases, templates, role add and the [dev] rename
  status: Done
created_at: '2026-10-25T22:01:52Z'
updated_at: '2026-10-26T08:51:57Z'
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
- [2026-10-25T23:28:55Z] `python-dev` Elias Python:
  - Role templates are data.
    
    - The bundled `[dev]` table is now `[templates.dev]` in `_specs/roles.toml` with the title, description, mission and responsibilities that were Python literals (`dev_role_from_pool` is gone; `instantiate_template` in `_roles/_catalog.py` reads only the table).
    - `_roles/_models.py` has `RoleTemplateSpec` (closed key space; `RoleCatalogSpec.templates`, `developer_capabilities()`); `_roles/_templates.py` holds the placeholder grammar (`{tech}`, `{Tech}`, `{first}` in `name`, `{{`/`}}`) and the substitution; `_roles/_loader.py` validates a template at load (required keys named in one message, `full_name`/`is_default` refused with their owner, placeholders, pool, model, capabilities) and takes `templates` as a top-level and `[selected]` section.
    - A legacy `[dev]` fails with the exact message of the ADR (`LEGACY_DEV_TABLE_MESSAGE`).
    - The slug pattern substitutes slugified values; the creation path also checks the earlier slug rule.
    
    Tests (new): `tests/unit/test_a_role_template_is_data_with_three_placeholders.py` (scanner, instantiation, parameter detection, 17 refusal rows, override shapes, legacy `[dev]`); the sync leg is `test_a_template_override_reaches_an_existing_developer_on_the_next_sync` in `tests/cli/test_a_roles_definition_follows_its_stored_base_cli.py`. Golden `tests/goldens/role_catalog_spec.json` rewritten by hand from the ADR, manifest and content store regenerated for 0.17.0 only.
    
    Reds seen then restored: legacy `[dev]` accepted (1), placeholder check off (4), `full_name` allowed (1), required-key message off (3), `[selected]` cannot drop templates (1), escape broken (1), pool does not wrap (1), template mission hard-coded (5).
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
- [2026-10-25T23:28:57Z] `python-dev` Elias Python:
  - The base is chosen from stored facts; stored values win.
    
    - `attrs.template(item)` replaces `is_templated`; role attributes `template`, `job_title`, `mission`, `responsibilities`, `agreements`, `color`, `can_spawn`, `capabilities` are declared in `[items.role.attributes]` (`settable = false`).
    - `_roles/_resolver.py`: `role_base_from_item` picks `template`, then `mission`, then the catalog and never looks the catalog up to decide the kind; `materialised_base` falls back to what the item stores; `resolve_role_with_base` merges the per-slug file over the base and then applies `StoredRoleValues` (name, default, model). A per-slug file alone is no base. This closes BUG-1075 and BUG-1065.
    - Removed: `to_attributes`/`to_item_fields`/`_ITEM_FIELD_PROJECTION`, `dev_base_from_item`, `resolve_dev_role`, `_refresh_catalog_attributes` (nothing left for sync to write), and the skew exemption (`PERMITTED_ATTRIBUTE_SKEW`): `model` is now an operator setting on every role, so a hand edit ahead of the index refuses like any other field. `RETIRED_ROLE_KEYS` is `full_name`, `skills`, `is_dev`.
    - `role_origin(slug, template=, item_defined=)`; a model outside the whitelist is refused at every write (`activate/add/dev add/update`, `update --set`, `sq import`); `model` joins `ROSTER_UPDATE_EXEMPT`.
    - `sq role list --json` rows carry `description`; `sq list -t role --json` shows the stored one only. `show` prints an advisory when a role's base does not resolve.
    
    Tests (new): `tests/unit/test_a_role_resolves_from_one_base_chosen_by_its_stored_facts.py`, and in `tests/cli/test_a_roles_definition_follows_its_stored_base_cli.py` the tables for kind by layer, kind stored not looked up, stored default (item-defined, previous default archived, bundled, moved away), stored model (incl. `opuss`, `Sonnet`, a long name by import: refused, nothing written), JSON surfaces, origin. Reworked: the role/dev/skew/sync tests that asserted the removed mirror, helpers `add_role_from_toml`, `write_role_file`, `add_role_from_file` in `tests/_helpers.py`.
    
    Reds seen then restored: catalog consulted first (3), stored values dropped (22), stored default dropped (8), stored model dropped (11), description stored on catalog roles (2), origin ignoring the template (3).
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
- [2026-10-25T23:29:00Z] `python-dev` Elias Python:
  - One creation path.
    
    - `RosterMixin.activate_role(slug, name=, model=, pronouns=, from_template=, tech=)`, `add_role(...)`, `_create_role` (blank-name check, `create`, pointer): `add_dev` and `resolve_dev_role` are gone. Reserved slug (`check_role_slug`), catalog-declared slug, duplicate check (a retired role names `status <live>`), name precedence (`--name`, a per-slug `full_name`, the `name` pattern at the count of roles storing that template), `--tech` required or refused by whether the template uses it.
    - CLI: `sq role activate [<slug>] --from <template> --tech --name --model --pronouns`, `sq role add <slug> --file/--name/--job-title/--desc/--mission/--capabilities/--model/--pronouns` (flags win over the file; every missing field named in one message; `is_default` refused), `sq dev add` calls the same body and `--tech` is optional so the missing-tech refusal is identical. `sq dev list` re-keys on the capabilities `[templates.dev]` declares. `sq role activate <slug>` for a file-only slug names `sq role add <slug> --file ...`. `sq override scaffold --new` exits 1 pointing at `sq role add` (option hidden, `--can-spawn` removed, `scaffold_new_role` deleted). `add` joins `ROLE_GROUP_VERBS`.
    
    Tests (new): `tests/cli/test_roles_are_created_through_activate_add_and_dev_add_cli.py` (creation, pool position, name precedence, duplicates, alias equivalence on two fresh squads, dropped template, `role add` shapes, reserved slugs for `add` and `activate --from` including rows only an early check answers, pointers). Reworked: the slug-grammar, group-verb, blank-name, scaffold and roster fixtures.
    
    Reds seen then restored: reserved check removed from `add` (5) and from the template path (5), name precedence (2), pool position by any template (1), alias diverging (2), `--tech` accepted on a catalog role (1), missing fields unreported (3).
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
- [2026-10-25T23:29:02Z] `python-dev` Elias Python:
  - `update` per kind.
    
    - `RosterMixin.update_role` writes the name, pronouns, model and (for a role that defines itself) job title, description, mission, capabilities, colour, spawn authority or a `--file` delta in one transaction after every check has passed. The delta goes through `merge_definition_delta` (the override engine, `$(*self)` against the item's current definition); `slug`, `full_name`, `is_default` are refused naming `update --title` and `set-default`; `tech`/`template` are not options and not file keys.
    - Catalog and template roles refuse the definition flags: exit 1, nothing written, the message names `.overrides/roles/<slug>.toml` and `sq override scaffold --role <slug>`, and for a template role `[templates.<name>]` of `.overrides/roles.toml`. A role whose catalog entry is gone becomes self-defining with `--job-title --desc --mission` together. A write to a field the per-slug file also sets happens and warns that the file wins. A blank `--model` clears. Import events setting definition fields are refused by the same gate.
    
    Tests (new): `tests/cli/test_role_update_per_kind_and_field_cli.py` (every flag on every kind, refusal text and untouched tree, `--file` deltas and refused keys, `--tech`/`--template`, shadowing warning, orphan made self-defining, import refusal).
    
    Reds seen then restored: catalog refusal off (7), template refusal off (7), identity keys allowed in a delta (3), blank model not clearing (2), warning dropped (1).
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
- [2026-10-26T01:18:15Z] `python-dev` Elias Python:
  - Migration additions are in the unreleased 0.16 to 0.17 runner (`_migrations/_v0_16_to_v0_17.py`) and the pre-runner check in `run_pending_migrations`.
    
    - Developers: `template: dev` is stamped on every role storing `tech`; the stored `model` stays; the stored `description` goes.
    - A catalog role (including a project `[[roles]]` entry) loses its `description` and any mirrored `model`. A role built from a template loses its `description`.
    - A role with no `tech`, no catalog entry and a per-slug file that loads as a complete role takes the file's title (as `job_title`), description, mission, responsibilities, agreements, colour, spawn authority, capabilities and model into its item. The name and the file are untouched.
    - A broken file and an orphan are listed in the run's report and left as they were.
    - A `[dev]` table in `.overrides/roles.toml` stops `sq migrate up` before the index is reconciled: exit 1, the ADR message plus "Nothing was changed", no file touched, schema not stamped. MANUAL tells adopters to rename it first.
    - Tests: `tests/cli/test_the_0_17_migration_moves_roles_onto_their_base_cli.py` (file-only role, developer, catalog role, project catalog entry, broken file, orphan, repair and second run, `[dev]`) plus the F1 rows. Reds seen then restored: template stamp, description clear, definition move, model drop, legacy refusal, report.
    
    How the extended steps reach a squad already stamped 0.17: they do not, by design. `run_pending_migrations` applies the migrations whose target schema is above the stamp, so at 0.17 nothing runs, and ADR-1151 rules out a schema bump. Proposal, no new code: the runner is idempotent, so the operator (or an adopter on a pre-release build) sets `schema_version = "0.16"` in `.squads.toml` and runs `sq migrate up`; only the 0.17 step runs and the run stamps 0.17 again. The extended steps are not in the released tool, so the run needs a build that has them (the dev tree, or the release once cut). A dedicated flag to re-run a step was considered and left out: it adds a surface for a situation that only exists before the release.
    
    This repo, simulated on a copy (nothing was run here): after the edit above, `uv run sq migrate up` (dev build, from the repo) changes 10 role files and nothing else apart from the index and the reflog. The 8 catalog roles lose `description`; the two developers (ROLE-9 python-dev, ROLE-426 typescript-dev) gain `template: dev` and lose `description` (their `model`, if any, is kept). Nothing else differs, and `.squads.toml` ends at 0.17 again. Expected diff matches the expectation except that the developers also lose their stored description, which the subtask asks for on template roles.
- [2026-10-26T02:02:21Z] `python-dev` Elias Python:
  - Update: the step is now safe to re-apply. A catalog role's stored model is dropped only when it equals the resolved one, a different one is kept and reported, and orphans keep theirs. Re-apply procedure unchanged: set schema_version = "0.16" in .squads.toml and run sq migrate up from a build with the extended runner. Simulated diff for this repo stays 10 role files.
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
- [2026-10-26T01:18:18Z] `python-dev` Elias Python:
  - `role_base_resolves` (error) and `role_definition_shadowed` (warn) are squad-global members, always on, registered in `_validator_names.py` and implemented in `_services/_validators.py`; the pure part is `base_problems` in `_roles/_resolver.py`, which reads only the documents in hand.
    
    - `role_base_resolves`, for each live role: a catalog slug the catalog no longer declares; an undeclared template; a template that takes `tech` and none stored, or `tech` stored where the template takes none; a role defining itself without `job_title` or `description`; a role storing both `template` and `mission`. Each message ends with its remedy.
    - `role_definition_shadowed`: a per-slug file setting a field the role stores in its item (title, description, mission, responsibilities, agreements, colour, spawn authority, capabilities); model is excluded because the stored model wins.
    - One rule per condition: a file with no role under it stays at `override_loads` (the earlier reporting is that rule, with the wording "no role under it ... `sq role add <slug> --file`"); the stamp is owed only over a base the bundled document declares (`override_stamped`); a legacy `[dev]` is `override_loads` with the rename.
    - `role show`'s advisory now says `sq check` reports why, under `role_base_resolves`. The `playbook_guide_role_live` remedy for a slug with no role now names `sq role add <slug>` or, for a catalog role, `sq role activate <slug>`.
    - Tests: `tests/service/test_check_reports_a_role_whose_base_does_not_resolve.py`, one table per rule (7 broken states, 4 clean, shadow rows, layer-with-no-base rows, 7 stamp rows by base origin). The old corpora tests tolerate the orphan error (`check_is_clean_but_for_orphaned_roles`). Reds seen then restored: catalog-slug check, template tech check, shadow file read, layer-with-no-base.
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
- [2026-10-26T01:18:20Z] `python-dev` Elias Python:
  - The playbook loader checks a guide's subject for grammar only (`is_valid_slug`, or a well-formed `*<capability>`), reads no role file and takes no catalog: `project_role_slugs` and the `catalog` and `project_catalog` parameters of `load_playbook`/`resolve_playbook` are gone. `playbook_guide_role_live` reports a guide whose role nobody holds, as it already did for the slug that no role item holds.
    - Tests: `tests/integration/test_a_playbook_guide_may_name_a_role_that_exists_only_in_its_item.py` (an item-defined role named by a guide loads and preloads the skill in the pointer and `role show`, a typo'd slug loads and is reported once, a bad subject is refused, a `*capability` guide reaches an item-defined holder). The per-slug-file workarounds are removed from the playbook tests; the loader tests that expected "not in role catalog" now expect the grammar refusal or a loading playbook. Red with the old restriction restored (2 of the rows).
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
- [2026-10-26T02:35:25Z] `typescript-dev` Ada Typescript:
  - Done. The @mention hover now reads name (full_name) and description from sq role list --json; the sq list -t role fetch is gone from itemPreviewManager. Changed: roleDirectory.ts (buildRoleDirectory takes SqRosterIdentity rows, skips rows without id/full_name, doc comment names the new source), types.ts + sqAdapter.ts (SqRosterIdentity and isSqRosterIdentity gain optional full_name/description), itemPreviewManager.ts. Tests in roleDirectory.test.ts: an it.each table over a catalog, a template and an item-defined role, an empty description and an omitted one; plus a canary feeding the sq list -t role row shape, which yields no entry and no description. markdown/previewDocument test fixtures moved to the roster row shape. Gates in clients/vscode: npm run lint clean, npm test 742 passed, tsc --noEmit and prettier clean.
- [2026-10-26T02:45:00Z] `typescript-dev` Ada Typescript:
  - REV-1157 findings F1-F3 fixed in clients/vscode: hidden-status roles excluded from the mention directory, role-row type and guard, canary and guard tests. lint clean, npm test 746 passed, role-list canary passes on the dev build.
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
- [2026-10-26T02:54:38Z] `tech-writer` Theo Writer:
  - Docs updated against the behaviour I drove on scratch squads with the dev build: docs/roles.md (three bases, role templates, sq role add, update per kind, dev add as an alias), docs/overrides.md (a per-slug file is a layer, layer-with-no-base error, scaffold --new retired, [templates.<name>] and [selected] templates, stamp rule, eleven always-on checks), docs/stability.md (Role bases frozen bullet, catalog top-level keys, stored role keys, repair set full_name/skills/is_dev, CLI creation and update), docs/migration.md (0.17 section rewritten: [dev] rename first, what the step rewrites, re-apply on a squad a pre-release stamped 0.17), internals, adoption, faq, workflow, README.
  - CHANGELOG 0.17.0: fixed the orphaned-guide remedy (catalog slug names sq role activate <slug>; otherwise sq role add / activate --from), the show trailer, the scaffold --role note, the migration model report (dropped when equal, kept and named when different); added the sq import refusal and the layer-with-no-base check. Doc guards and tests/meta pass (1004).
  - Behaviour that looks off, not fixed (no source edits): (1) the remedy text `sq role add <slug> --file .overrides/roles/<slug>.toml` in sq check and in the activate refusal does not work from the project root or with -C: --file resolves against the process cwd, so the path must be squads/.overrides/...; (2) sq override scaffold --role <slug> for a slug with no role writes a file that sq check then reports at error; (3) the show trailer on catalog and template roles still sends the model to an override file although a stored model wins over it; (4) sq role --help epilog lists group verbs (catalog, activate, list) without add; (5) the migration report for a broken file quotes the old "role override for new slug ... missing required fields" wording. @manager
- [2026-10-26T03:19:56Z] `tech-writer` Theo Writer:
  - Docs aligned with the five fixes, each re-driven on a scratch squad: remedy path relative to cwd (overrides.md quotes and the workaround sentence), scaffold --role refusal for a slug with no role (overrides.md, CHANGELOG), the new show trailer (roles.md, CHANGELOG). The migration report and role --help epilog are not quoted anywhere.
  - Narration sweep: overrides.md "is now stored" -> "is stored", "can no longer be activated" -> "cannot be activated", "a catalog role the catalog no longer declares" -> "whose slug the catalog does not declare"; _services/_maintenance.py docstring "the [dev] table the catalog document no longer has" -> "a [dev] table, which is not a key of the catalog document". No ticket ids or phase/round language found; migration runner and CHANGELOG history left as is. Guards pass, sq check clean. @manager
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T22:06:38Z] `tech-lead` Olivia Lead:
  - Drafted from ADR-1151 (Accepted; op-pierre: ships in 0.17). No open feature fits as parent (FEAT-986, ADR-984's feature, is Done in 0.16), so the task targets MILE-1051 with no parent.
  - TASK-1137 ST1/ST2 are carried by ST2 and ST4 by ST3, with their test tables and bug refs; TASK-1137 keeps ST3 alone, because init --roles is a different surface that ADR-1151 does not touch.
  - ST1 to ST7 are one python-dev pass in order (shared _roles/, _services/_roster.py, role CLI). ST5 hands the live-squad migrate command back to the operator rather than running it. Draft until dispatch.
- [2026-10-25T23:29:15Z] `python-dev` Elias Python:
  - ST1 to ST4 are in the working tree, uncommitted, for review. ST5 to ST7 are untouched. Gates: pyright, `ruff check .` and `ruff format --check .` clean; the unit, service, cli, integration, meta and tui directories pass (the slow scale tests are skipped by default). Generated agent files on a pinned roster with a developer: `.claude/` and CLAUDE.md are byte-identical before and after; only the role item files differ (the stored `description` is gone from every role, and the developer stores `template: dev` and no `model`).
    
    Where the ADR is not buildable as written, or I chose:
    - The skew exemption in `_itemfile.py` is removed, not re-keyed on `template`: its only writer (`_refresh_catalog_attributes`) is gone and `model` is an operator setting on every role, so exempting it would mask a real hand edit.
    - Nothing is left for sync to write on a role, so `_refresh_catalog_attributes` is deleted. That also drops the old healing of a blank stored name; a blank name now reads as unset in every resolver.
    - Until ST5 stamps `template: dev`, a squad migrated from 0.16 has developers that store `tech` only and resolve as an unresolved catalog role (no capabilities). One migrate test now stamps the template by hand.
    - Until ST7, a playbook guide naming a role that exists only in its item is refused at load; the tests that need one keep a per-slug file beside the role. The playbook-guide check still says `sq role activate <slug>` for a slug with no role.
    - A layer with no base already reports at `override_loads` (error) from `_check_role_override_resolves`, and the stamp is no longer owed over a role that defines itself; the rest of ST6 is untouched.
    - `dev add --tech` is optional at the CLI so the missing-tech refusal matches `activate --from dev` exactly; `add` becomes a reserved role slug.
    - The VS Code hover reads `description` from `sq list -t role --json`, which is empty for catalog and template roles now: ST8 must land with this.
    - docs/overrides.md loses only the `--new ... --can-spawn` example line (the documented-commands meta test); the rest is ST9.
    
    Gate for the second increment: ST5 must stamp `template: dev` and clear the stored `description` on catalog and template roles, or migrated squads lose their developers' capabilities.
    
    @reviewer ST1 to ST4 are ready for review.
- [2026-10-26T00:04:21Z] `reviewer` Paul Reviewer:
  - REV-1155 is open on ST1 to ST4: two medium findings (F1 legacy mirrored model survives migration, F2 activate on a live non-catalog role) and seven low ones. F1 needs a step in the ST5 runner. @python-dev
- [2026-10-26T03:17:18Z] `python-dev` Elias Python:
  - Five defects found while driving the documented commands:
    - The remedy `sq role add <slug> --file .overrides/roles/<slug>.toml` fails from the project root and under `-C`.
    - `sq override scaffold --role <slug>` for a slug with no role writes a file that `sq check` reports as a layer with no role.
    - The `show` trailer on catalog and template roles points at an override file for the model, but a stored `--model` wins.
    - The `sq role --help` epilog omits `add` from the group verbs.
    - The migration report for a role file that does not load says "role override for new slug ... is missing required fields".
- [2026-10-26T03:17:20Z] `python-dev` Elias Python:
  - All five fixed, not committed. Each has a test that goes red when the change is reverted.
    - The remedy path is now spelled relative to the process directory (`path_from_process_dir` in `_paths.py`), used by the activate refusal and the check finding. Tested from the project root, the squad dir and under `-C`.
    - `override scaffold --role` refuses a slug with no role item and no catalog entry, naming `sq role add` and `sq role activate`; nothing is written.
    - The show trailer now adds "To change its model: `sq role <slug> update --model …`".
    - The epilog verb list is derived from `ROLE_GROUP_VERBS`.
    - The unloadable-file message now reads "the file for 'x' is a layer with no base (no role or catalog entry holds it) and lacks the required fields: …".
    - New row in the import-edge table: `_overrides -> _paths top`.
    - Gates and `sq check` clean.
- [2026-10-26T03:25:09Z] `manager` Catherine Manager:
  - All nine subtasks are Done; REV-1155, REV-1156 and REV-1157 are Approved; full suite 15160 passed at the last commit. Left InReview for @op-pierre: the VS Code mention hover (now read from sq role list --json, archived roles excluded) wants a dev-host look, and running the 0.17 role step on this repo's squad (set schema_version = 0.16, then sq migrate up; simulated twice on a copy: 10 role files change) is his call.
- [2026-10-26T08:51:57Z] `op-pierre` Pierre Chat:
  - Go to run the extended 0.17 role step on this repo's squad now.
<!-- sq:discussion:end -->
