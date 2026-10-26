---
id: REV-1155
sequence_id: 1155
type: review
title: 'Review TASK-1153 ST1-ST4: role bases, templates, role add, update'
status: Approved
author: reviewer
refs:
- TASK-1153
description: 'Review of commit d37899d4: role templates as data, base from stored
  facts, one creation path, update per kind.'
subentities:
- local_id: F1
  title: Migrating a pre-0.14 squad keeps each catalog role's mirrored model as a
    winning stored setting
  status: Verified
  severity: medium
- local_id: F2
  title: sq role activate on a live template or item-defined role exits 1 with a false
    message
  status: Verified
  severity: medium
- local_id: F3
  title: activate on a live role silently drops --model, --pronouns and --name and
    prints activated
  status: Verified
  severity: low
- local_id: F4
  title: sq role add refusals use override vocabulary and blame the file for a flag
    value
  status: Verified
  severity: low
- local_id: F5
  title: An orphan made self-defining by update keeps origin system
  status: Verified
  severity: low
- local_id: F6
  title: role show for a deselected bundled role hints at a per-slug scaffold that
    cannot fix it
  status: Verified
  severity: low
- local_id: F7
  title: Stale remedies and hints still describe the per-slug creation flow
  status: Verified
  severity: low
- local_id: F8
  title: Clearing a definition key and role add refreshing managed files survive mutation
  status: Verified
  severity: low
- local_id: F9
  title: An invalid stored role model is kept, dropped from the pointer, and unreported
  status: Verified
  severity: low
created_at: '2026-10-26T00:03:46Z'
updated_at: '2026-10-26T00:41:48Z'
---
<!-- sq:body -->
## Scope

Commit d37899d4 on `release/0.17`, TASK-1153 ST1 to ST4 against ADR-1151: role templates as `[templates.<name>]` data, the base chosen from stored facts, one creation path (`sq role activate --from`, `sq role add`, `sq dev add`), and `update` per kind. ST5 to ST9 are out of scope. Their absence is not a finding here.

## How it was reviewed

The diff was read in full: `_roles/` (`_templates.py`, `_loader.py`, `_catalog.py`, `_resolver.py`, `_models.py`), `_services/_roster.py`, `_services/_maintenance.py`, `_itemfile.py`, `_cli/_role.py`, `_cli/_dev.py`, `_cli/_override.py`, `_overrides/_service.py` and the spec files. Behaviour was driven on scratch squads with the dev tree, including a squad rebuilt in the pre-0.16 nested shape and migrated with both the dev tree and the released tool. Four mutations were run on a scratch copy of the tree against targeted test selections. The new test files pass (234 tests, `-n 4`), and `ruff check` and `ruff format --check` are clean.

## What holds

- **Kind from stored facts.** An item-defined `sre` keeps its own mission and pointer after a project `[[roles]]` entry `sre` with another mission is added. A stored `template` wins over a catalog entry of the same slug (driven).
- **Templates are data.** A `.overrides/roles.toml` changing `[templates.dev].mission` and appending to `responsibilities` with `$(*self)` reaches an existing developer's `show` on the next read (driven). The `{{`/`}}` escape renders a literal brace in the pointer description. The legacy `[dev]` table is refused with the exact ADR message. `[selected] templates = []` drops the dev template, and `sq dev add` then exits 1 naming the declared templates (none).
- **Creation.** Every shape tried did what the ADR says: no slug pattern, no name pattern, `--tech` required or refused, a catalog slug, a reserved slug (`add`, `op-x`), a bad slug, a blank name, an invalid model, a duplicate and the legacy slug spelling. Pool positions count the roles that store the same template. `role add` with flags, with `--file`, and with flags beside a file all work, and every missing field is named in one message.
- **Update per kind.** Definition flags and `--file` are refused on catalog and template roles: exit 1, nothing written, the override path and the scaffold command named. They apply to an item-defined role. `--model ""` clears the stored model. `--file` refuses `slug`, `full_name`, `tech` and `template`, and `$(*self)` resolves against the item. The shadowing warning fires when a per-slug file sets the edited field.
- **Stored values win.** A stored name, model and default beat the per-slug file for every kind. `set-default` on an item-defined role reaches `role list` and the CLAUDE.md default line.
- **Tests bite where the dev said.** Removing the catalog-slug refusal on `--from` turns four tests red, and dropping the legacy-slug duplicate check turns one red.
- **Conventions.** No ticket IDs in source or tests. Type aliases and attribute reads follow the project rules. The new comments are short.

## Documented deviations, judged against the ADR

- **Skew exemption removed rather than re-keyed.** Sound: no writer is left that writes outside a transaction.
- **`_refresh_catalog_attributes` deleted.** Sound, since nothing is left for sync to write. It has one side effect the dev did not list, recorded in F1: the repair sweep stops removing a mirrored `model`.
- **0.16 developers resolve as unresolved catalog roles until ST5.** Accepted as a gate on ST5, which the task already states.
- **Playbook guides for item-defined roles refused until ST7, and the VS Code hover until ST8.** Accepted as stated.
- **Import refuses definition fields on every kind, through the view authoring gate.** This is a reasonable reading of "on the same terms", because the refusal names `sq role <slug> update`. No finding.

## Findings

F1 to F9 below. F1 is a migration regression that ST5 does not plan to repair. F2 is a false refusal on a documented no-op. The rest are low: a silently ignored flag, error wording, a stale origin, stale hints and remedies, test gaps, and an unvalidated stored model.

## Verdict

Request changes on F1 and F2. F3 to F9 are small and can ride the ST5 to ST7 pass.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1155 add-finding "…" --severity medium`; track with `sq review 1155 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Migrating a pre-0.14 squad keeps each catalog role's mirrored model as a winning stored setting

<!-- sq:finding:F1:body -->
**What.** `RETIRED_ROLE_KEYS` shrinks to `full_name`, `skills` and `is_dev`, and `_retired_role_keys` no longer subtracts by shape, so the repair sweep at the end of `sq migrate up` stops removing `model` from a role that does not store `tech`. Releases up to 0.13 mirrored the resolved `model` (and `is_default`) onto every role under `extra` (`git show v0.13.0:src/squads/_roles/_catalog.py`, `_EXTRA_FIELD_KEYS`). The 0.15 to 0.16 flatten lifts `extra.model` to the top level, because its own `_RETIRED_ROLE_KEYS` leaves `model` to the sweep. With this commit nothing removes it, and ADR-1151 decision 1 makes that stored copy an operator setting that wins over the catalog, the template and the per-slug file.

**Failure scenario (driven).** On a scratch squad, the reviewer's frontmatter was rewritten in the 0.15 nested shape with `extra: {slug: reviewer, model: haiku, mission: old mirror, is_default: false}` and the schema stamped back to 0.15. `sq migrate up` with the dev tree leaves `model: haiku` on the reviewer. `sq role reviewer show --json` then says `haiku`, and `.overrides/roles/reviewer.toml` with `model = "sonnet"` has no effect. `sq check` reports nothing about it. The same squad migrated with the released tool ends without `model`. So an adopter who upgrades from 0.13 or earlier straight to 0.17 has every catalog role pinned to its old mirrored model, with no signal.

**Why it is not ST5's.** ST5 keeps a developer's stored model as written and clears `description`. It says nothing about a mirrored model on a role without `tech`, and the 0.15 to 0.16 runner is released and frozen.

**Remedy.** Have the unreleased 0.16 to 0.17 runner drop `model` from every role that has no `tech` and is not a per-slug-file custom role being moved into its item. At 0.16 such a value is residue by construction, because the 0.16 sweep removed it. Add a migration row for a 0.13-shaped catalog role carrying `extra.model`. Decide the same for a mirrored `is_default: false` while there.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T00:18:59Z] `python-dev` Elias Python:
  - The unreleased 0.16 to 0.17 runner now drops model from every role file that stores no tech (_migrations/_v0_16_to_v0_17.py). Test: a 0.15 nested role with extra.model driven through sq migrate up (catalog role, tech-less role with a role file, developer keeps its model). Red when the runner skips the drop. is_default is left alone: 0.16 legitimately stores an explicit False when set-default clears another holder, so a mirrored False cannot be told from it.
- [2026-10-26T00:29:55Z] `reviewer` Paul Reviewer:
  - Verified on c2467e30 (driven): a 0.15-shaped reviewer with extra.model haiku, migrated with the dev tree, ends with no model, and a per-slug model = "sonnet" now applies. Developers keep their stored model, whether it came from extra or the top level. I accept leaving the mirrored is_default as it is: 0.16 set-default writes an explicit False when it clears a holder (v0.16.0 _roster.py), so a mirrored False cannot be told apart from it, and set-default still moves the designation.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — sq role activate on a live template or item-defined role exits 1 with a false message

<!-- sq:finding:F2:body -->
**What.** `activate_role` resolves the catalog entry (`_catalog_role`) before it looks for an existing item. For a live role that is not a catalog entry, that lookup raises first. The help still says "Activating a live role does nothing."

**Failure scenario (driven).** On a squad with an item-defined `sre3` (made with `sq role add`), `sq role activate sre3` exits 1 with `no role 'sre3': the catalog does not declare it (known: …)`, yet `sq role sre3 show` works. On a squad whose template role `python-dev` has a `.overrides/roles/python-dev.toml` layer, `sq role activate python-dev` exits 1 with `role 'python-dev' is declared only by .overrides/roles/python-dev.toml … create the role with sq role add python-dev --file …`. That command then fails as a duplicate. Both messages are false: the role exists.

**Remedy.** Look up the existing item first. A live item is the documented no-op whatever its base, and a retired one is the revive refusal. Resolve the catalog only when no item exists. Add rows for `activate` on a live template role (with and without a per-slug file) and on a live item-defined role.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T00:19:01Z] `python-dev` Elias Python:
  - activate now looks up the existing item first: a live role of any base is the no-op, a retired one the revive refusal; the catalog is resolved only when no item exists. Rows: live catalog, template and item-defined role, each with and without a per-slug file. Red when the order is restored.
- [2026-10-26T00:29:57Z] `reviewer` Paul Reviewer:
  - Verified (driven): activate on a live item-defined role, and on a live template role with a per-slug layer, is the no-op and prints activated.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — activate on a live role silently drops --model, --pronouns and --name and prints activated

<!-- sq:finding:F3:body -->
**What.** `activate` now takes `--model`, but on an already-live catalog role the existing item is returned untouched. `--model`, `--pronouns` and `--name` are dropped without a word, and the command prints `activated …` and exits 0.

**Failure scenario (driven).** `sq role activate reviewer --model haiku` on a squad where `reviewer` is live prints `activated Paul Reviewer (reviewer) ROLE-4`, and the item stores no model. An operator reads that as done. The `update` verb is the one that writes the model.

**Remedy.** When the role is already live and any of these flags is given, either refuse and name `sq role <slug> update --model …`, or warn that the flags were not applied. The `init`/`adopt` no-op path passes none of them, so it is unaffected.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T00:19:03Z] `python-dev` Elias Python:
  - Activating a live role with a --name, --model or --pronouns that differs from what it stores now exits 1 naming the flag and sq role <slug> update <flag>; the same values are still a no-op, so init and adopt are unaffected. Rows for each flag on each kind. Red when the refusal is off.
- [2026-10-26T00:30:00Z] `reviewer` Paul Reviewer:
  - Verified (driven): activate on a live role refuses --model and --pronouns that differ from what it stores, naming update. A --name equal to the stored one is still the no-op.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — sq role add refusals use override vocabulary and blame the file for a flag value

<!-- sq:finding:F4:body -->
**What.** `sq role add` builds the role through `role_from_definition`, that is `_apply_override`, so its refusals use the override file's vocabulary and source label even when the value came from a flag.

**Failure scenario (driven).**
- `sq role add sre5 --name X --job-title '' --desc D --mission M` prints `invalid role override the role definition: field(s) blank or whitespace-only (omit the key instead to inherit): title`. There is no override, nothing to inherit, and the flag is `--job-title`, not `title`.
- `sq role add sre2 --file sre.toml --capabilities 'a,B c'` blames the file, `invalid role override …/sre.toml: capabilities entry 'B c' must match …`, though the bad value came from `--capabilities` and the file was valid.

The same wording reaches `update --job-title ''` on an orphan (`_self_definition`).

**Remedy.** Validate the flag values before merging them (blank text flags and `--capabilities`, as `update` does with `_refuse_bad_capabilities`), naming the flag. Use a creation-specific source label and message prefix for what remains.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T00:19:06Z] `python-dev` Elias Python:
  - role add and the orphan update validate the flag values first (blank --name, --job-title, --desc, --mission, malformed --capabilities) and name the flag. What reaches the file grammar afterwards comes from the file. Tests: blank --job-title, and a bad --capabilities beside a valid file. Red when the flag check is off.
- [2026-10-26T00:30:02Z] `reviewer` Paul Reviewer:
  - Verified (driven): a blank --job-title or --name and a bad --capabilities beside a valid file are each refused, naming the flag.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — An orphan made self-defining by update keeps origin system

<!-- sq:finding:F5:body -->
**What.** `origin` is stamped once at creation (`setdefault` in `_services/_base.py`) and never re-derived. ADR-1151 decision 3 makes origin a function of the base: system for a bundled entry or template, project otherwise. `update --job-title … --desc … --mission …` on a role whose catalog entry is gone (the decision 6 remedy) turns it item-defined, so `item_origin` would now say `project`. The stored value stays `system`.

**Failure scenario (driven).** Activate `qa`, deselect it in `.overrides/roles.toml`, then run `sq role qa update --job-title QA --desc Tests --mission "Test it"`. The item stores `mission` and still has `origin: system`. `sq role list` shows `system`, and `sq repair` and `sq sync` leave it.

**Remedy.** Restamp `origin` from `item_origin` in the same write when `_self_definition` changes the base kind. Add a row to the orphan-made-self-defining test.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T00:19:08Z] `python-dev` Elias Python:
  - The orphan made self-defining by update restamps origin to project in the same write. Test: a role stored as system, then updated with --job-title --desc --mission. Red without the restamp.
- [2026-10-26T00:30:04Z] `reviewer` Paul Reviewer:
  - Verified (driven): a deselected qa made self-defining is stored with origin project, and role list shows project.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — role show for a deselected bundled role hints at a per-slug scaffold that cannot fix it

<!-- sq:finding:F6:body -->
**What.** `_change_role_hint` takes the scaffold branch whenever the slug is in the bundled `PREDEFINED` set, even when `base_resolves` is false.

**Failure scenario (driven).** Deselect `devops` in `.overrides/roles.toml` while a `devops` role is live. `sq role devops show` prints the advisory that the definition could not be resolved, then ends with `To change its mission, responsibilities or model: sq override scaffold --role devops …`. That writes a per-slug file, which under ADR-1151 is a layer with no base and does not fix the role. The working remedy is the third branch (restore the catalog entry, or `update --job-title … --desc … --mission …`).

**Remedy.** Choose the scaffold branch only when the base resolves, and drop the `PREDEFINED` membership test. ST6's `role_base_resolves` covers the "run sq check" half of the advisory but not this hint.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-26T00:19:11Z] `python-dev` Elias Python:
  - The scaffold hint is chosen only when the base resolves; the PREDEFINED membership test is gone. Test: a deselected bundled role shows the advisory and the update remedy, not the scaffold. Red when restored.
- [2026-10-26T00:30:07Z] `reviewer` Paul Reviewer:
  - Verified (driven): a deselected devops shows the advisory and the update remedy, not the scaffold hint.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Stale remedies and hints still describe the per-slug creation flow

<!-- sq:finding:F7:body -->
**What.** Some guidance text still describes the per-slug-file creation flow, or points at a command that fails in the state it is shown in. These sites are read, not driven, unless marked otherwise.

- `_services/_validators.py`, the `_roster_slug_valid` role remedy: "rename the project role file to a compliant slug, run sq role activate <slug>, then … remove --purge". A custom role is now created with `sq role add`, and `activate` on a file-only slug exits 1. `add` joining `ROLE_GROUP_VERBS` makes this remedy reachable for any adopter role already slugged `add`. ST6 does not list this rule.
- `sq dev list` with the `dev` template deselected prints `no developers (try sq dev add --tech <t>)`, and that command then exits 1 (driven).
- `_models/_metadata.py`, `_refusal_hint`: `title` is in `_ROLE_DEFINITION_KEYS`, so `sq import` setting `title` on a role is told "a role's definition is set with sq role <slug> update (item-defined roles only)". On a role, `title` is the name, and `update --title` works on every kind (driven).
- The `_cli/_role.py` module docstring lists the role grammar without `add`, `activate --from` or `update`.

**Remedy.** Point the slug remedy at `sq role add <compliant slug> …`. Make the empty `dev list` hint depend on a `dev` template being declared. Give `title` its own hint naming `update --title`. Add the three verbs to the module grammar.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-26T00:19:13Z] `python-dev` Elias Python:
  - Fixed all four: the slug-breach remedy points at sq role add <compliant slug>; sq dev list prints the dev add hint only while a dev template is declared; title gets its own hint (update --title); the _cli/_role.py grammar lists activate --from, add and update. Tests for each (the remedy row in the slug-grammar service test, the empty dev list, the title hint).
- [2026-10-26T00:30:09Z] `reviewer` Paul Reviewer:
  - Verified (driven or read): the slug-breach remedy names sq role add; dev list drops the dev add hint when no dev template is declared; import of title on a role names update --title; the module grammar lists the new verbs.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Clearing a definition key and role add refreshing managed files survive mutation

<!-- sq:finding:F8:body -->
**What.** Two behaviours survived mutation on a scratch copy of the tree against `tests/cli`, `tests/service`, `tests/unit` and `tests/integration` (selected with `-k` on role, update, dev and roster).

- **Clearing a definition key.** In `_definition_fields`, `**{key: optional.get(key) for key in keys}` was replaced with `**optional`, so a cleared key is never removed. 2494 tests passed. `update --color ''`, `--capabilities ''` and `--can-spawn no` on an item-defined role would then silently keep the old value. The per-kind table only sets values and never clears one.
- **`sq role add` refreshing the managed files.** `await svc.refresh_managed()` was removed from the `add` command. 1678 tests passed. No test asserts that the CLAUDE.md or AGENTS.md roster gains a role created with `sq role add`.

**Remedy.** Add clearing rows (blank `--color`, blank `--capabilities`, `--can-spawn no` after `yes`) that assert the key leaves the frontmatter and the pointer. Add a `role add` row asserting the managed roster line and a clean `sq check`. Falsify both.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-26T00:19:15Z] `python-dev` Elias Python:
  - Added rows that clear a definition key (blank --color, blank --capabilities, --can-spawn no after yes) asserting the key leaves the frontmatter, and a role add row asserting the CLAUDE.md roster line and a clean sq check. Both mutations now go red (3 and 3 tests).
- [2026-10-26T00:30:12Z] `reviewer` Paul Reviewer:
  - Verified: on a scratch copy of c2467e30, removing key clearing in _definition_fields and removing refresh_managed from role add each turn 3 tests red.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — An invalid stored role model is kept, dropped from the pointer, and unreported

<!-- sq:finding:F9:body -->
**What.** `model` is now kept on every role and wins over every layer, but only the write paths validate it. A value that reaches the file another way (a hand edit, or a legacy mirror as in F1) goes into the resolved `RoleDef` unchecked. The 0.16 sweep removed such a value from a catalog role. Now it stays.

**Failure scenario (driven).** Add `model: gpt-5` by hand to a catalog role's frontmatter, then run `sq repair` and `sq sync`. `sq role reviewer show --json` reports `"model": "gpt-5"`, the generated pointer silently has no `model:` line, and `sq check` reports nothing.

**Remedy.** Report an invalid stored role model in `sq check` with the whitelist message, either in ST6's `role_base_resolves` or through `attribute_valid` with a choice constraint. Have the resolver or the backend not present an invalid value as the role's model.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-26T00:19:18Z] `python-dev` Elias Python:
  - Chose report plus read-as-unset, which is what the typed accessors already do for a value that fails its kind: attribute_valid now reports a stored role model outside the whitelist (error, existing rule), and the resolver treats it as unset so the template, file or catalog model applies. The ADR asks only for the write-time refusal, so a read-time refusal would make show fail on a hand edit. Tests: a hand-written gpt-5 on a catalog role and on a developer; both mutations red.
- [2026-10-26T00:30:14Z] `reviewer` Paul Reviewer:
  - Reopened. I accept the choice (attribute_valid reports the value and it reads as unset, with no refusal at read). The fix is incomplete for an item-defined role. stored_values drops an invalid model, but RoleDef.from_item, which is that role base, still reads attrs.model(item) unfiltered. Driven: model: gpt-5 written by hand on a catalog role, a developer and an sq role add role, then sq repair and sq sync. The catalog role and the developer resolve to opus and sonnet. The item-defined sre3 still shows "model": "gpt-5" in show --json, and its pointer has no model line. sq check does report all three. Remedy: apply the same model_problem filter in RoleDef.from_item (or one shared accessor), and add an item-defined row to the test.
- [2026-10-26T00:33:44Z] `python-dev` Elias Python:
  - RoleDef.from_item now reads the stored model through the same accessor as stored_values (stored_model in _roles/_catalog.py: a model outside the whitelist reads as unset). Test: a role made with sq role add and a hand-written model gpt-5 shows model null and is reported by check. Red (1 failed) with the filter removed from from_item.
- [2026-10-26T00:41:45Z] `reviewer` Paul Reviewer:
  - Verified on d106a180 (driven): with model: gpt-5 hand-written on a catalog role, a developer and an sq role add role, then sq repair and sq sync, the roles resolve to opus, sonnet and unset. show --json and the pointers agree, and sq check reports all three. A side effect I accept: a later definition edit (update --desc) on the sq role add role removes the invalid key from its file, which matches reading it as unset.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T00:04:20Z] `reviewer` Paul Reviewer:
  - Reviewed d37899d4 (TASK-1153 ST1 to ST4). Nine findings: F1 and F2 medium, F3 to F9 low. Recommend request changes on F1 (a 0.13-or-earlier squad migrated to 0.17 keeps every catalog role pinned to its mirrored model, and nothing reports it) and F2 (activate on a live template or item-defined role exits 1 with a false message). F3 to F9 can ride the ST5 to ST7 pass. The documented deviations hold against the ADR. @tech-lead @python-dev
- [2026-10-26T00:30:24Z] `reviewer` Paul Reviewer:
  - Re-verified c2467e30: F1 to F8 Verified, and the mirrored is_default choice in F1 is accepted. F9 is reopened: an item-defined role still resolves a hand-written invalid model, because RoleDef.from_item does not filter it. Changes requested on F9 only. @python-dev
<!-- sq:discussion:end -->
