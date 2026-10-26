---
id: REV-1156
sequence_id: 1156
type: review
title: 'Review TASK-1153 ST5-ST7: role migration, base checks, playbook grammar'
status: Approved
author: reviewer
refs:
- TASK-1153
description: 'Review of commit 137d5ec9: 0.17 role migration, role_base_resolves/role_definition_shadowed,
  grammar-only guide slugs.'
subentities:
- local_id: F1
  title: Re-running the 0.17 step on a squad at 0.17 drops operator-set models on
    catalog roles and orphans
  status: Verified
  severity: medium
- local_id: F2
  title: check_is_clean_but_for_orphaned_roles tolerates every role_base_resolves
    error, masking lost developer bases
  status: Verified
  severity: medium
- local_id: F3
  title: sq import creates a role with no base, exit 0, and role_base_resolves errors
    on it at once
  status: Verified
  severity: low
- local_id: F4
  title: Drift warning on a migrated custom role's file asks to re-stamp it while
    the shadow warning says delete it
  status: Verified
  severity: low
- local_id: F5
  title: role_base_resolves passes a whitespace job_title or mission and a malformed
    stored capability
  status: Verified
  severity: low
- local_id: F6
  title: A playbook guide for a reserved slug loads and its warning names a role add
    that is refused
  status: Verified
  severity: low
- local_id: F7
  title: Bundled playbook guide slugs are no longer checked against the bundled catalog;
    composition row deleted
  status: Verified
  severity: low
- local_id: F8
  title: CHANGELOG still says the 0.17 migration step changes no item file
  status: Verified
  severity: low
- local_id: F9
  title: Re-applying the 0.17 step silently drops an operator model pin equal to the
    catalog's model
  status: Verified
  severity: low
created_at: '2026-10-26T01:42:16Z'
updated_at: '2026-10-26T02:33:20Z'
---
<!-- sq:body -->
## Scope

Commit 137d5ec9 on `release/0.17`: TASK-1153 ST5 (the 0.16 to 0.17 migration additions and the legacy `[dev]` refusal), ST6 (`role_base_resolves`, `role_definition_shadowed`) and ST7 (the playbook loader checks guide subjects for grammar only), against ADR-1151. ST1 to ST4 were reviewed in REV-1155 and are out of scope except where this commit changes them.

## Method

- Squads at schema 0.16 and 0.15 were built with the released 0.16.0 and 0.15.0 tools (built from their tags in a scratch dir), then migrated with the dev build at 137d5ec9. The 0.16 squad held two developers (one with `--model opus`, one with a per-slug file), four catalog roles (one with a per-slug file), a project `[[roles]]` entry, a complete file-only custom role with every definition key, a broken file, an orphan and a retired file-only role. A copy carrying `[dev]` tested the refusal.
- A copy of this repo's `squads/` and `.squads.toml` was set back to 0.16 and migrated, to test the ST5 proposal.
- Mutations were made on a scratch clone of the code only, followed by targeted `pytest -n 4` runs.

## What holds

- Driven: nothing is lost on 0.16 or 0.15. Each file-only custom role (live or retired) takes every key of its file into the item, with the name untouched and the file unchanged. Developers gain `template: dev` and keep their model. Catalog roles and the project `[[roles]]` role lose only `description`. The broken file and the orphan are reported and left unchanged. Comparing `role show --json` before (0.16.0) and after (dev build) gave the same values for every role, except `capabilities = ["review"]` on the reviewer, which comes from the 0.17 bundled catalog.
- Driven: the `[dev]` refusal exits 1 and changes no file (git status is clean, ignored files included), and the schema stays at 0.16. A malformed roles.toml or one with an unknown key is also refused with nothing written.
- Driven: a second run after the stamp is set back is idempotent on the 0.16 squad: only the reflog changes, and a repair after it changes nothing.
- Driven: the ST5 proposal on a copy of this repo's squad changes 10 role files (8 catalog roles lose `description`; ROLE-9 and ROLE-426 gain `template: dev` and lose `description`), plus a rebuilt index (semantically identical apart from those 10 rows) and two reflog lines. `.squads.toml` ends at 0.17 byte-identical. Running the dev build's `sq check` on the migrated copy reports no role-rule finding. On the unmigrated copy, the dev build reports `role_base_resolves` errors on ROLE-9 and ROLE-426, so this repo's `sq check` gate goes red as soon as a build with this commit becomes the board tool, until the step is re-applied. No repo role stores a `model` on a catalog role, so F1 does not affect this repo.
- Mutations: removing the template stamp turns the new ST5 test and the corpus goldens red. Removing the "both template and mission" check turns its row red.

Findings follow. Recommended verdict: ChangesRequested on F1 and F2. The rest are low.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1156 add-finding "…" --severity medium`; track with `sq review 1156 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Re-running the 0.17 step on a squad at 0.17 drops operator-set models on catalog roles and orphans

<!-- sq:finding:F1:body -->
**What.** `_migrated` (`_migrations/_v0_16_to_v0_17.py`) runs `out.pop(AttributeKey.MODEL, None)` on every role with no `template`, `mission` or `tech`, before the catalog lookup. Under 0.16 a stored `model` on such a role could only be leftover from an earlier release's mirror. Under 0.17 it is an operator setting that `sq role <slug> update --model` writes (decision 1 of ADR-1151; BUG-1065). The ST5 handoff proposes reaching a squad already stamped 0.17 by setting `schema_version = "0.16"` and running `sq migrate up` again, and calls the runner idempotent. That holds only for squads with no such setting.

**Driven (scratch squad migrated to 0.17 with the dev build):** `sq role reviewer update --model haiku`, `sq role ops update --model haiku` (a project `[[roles]]` entry) and `sq role orphan update --model opus`. Then set the stamp to 0.16 and run `sq migrate up`: exit 0, "3 changed", and `model:` is removed from all three files. The report does not mention it.

**Failure scenario.** An adopter on a pre-release build, or this repo once someone sets a catalog role's model, follows the proposal and loses every per-role model choice made at 0.17 without being told. The test `test_a_repair_after_the_run_rebuilds_the_same_index_and_a_second_run_changes_nothing` misses this because its rows never set a model at 0.17 before the second run.

**Fix direction.** Drop a stored model only when it is mirror residue, e.g. when it equals the model the base resolves to: a mirror copied that value, so an operator choice that differs survives. Alternatively, record the proposal as unsafe when any catalog role stores a model. In both cases, add a second-run row that sets `--model` at 0.17 first. This repo is not affected today: no catalog role stores a model, and the simulated diff matches the handoff.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T02:02:02Z] `python-dev` Elias Python:
  - The 0.16 to 0.17 step is safe to re-apply: a catalog role's stored model is dropped only when it equals the model the catalog resolves, a different one is kept and reported, and orphan roles keep theirs. Table rows cover a re-run at the current schema for a catalog role and an orphan.
- [2026-10-26T02:16:10Z] `reviewer` Paul Reviewer:
  - Verified on a real 0.16 squad, migrated, then re-applied at 0.17: operator models set with update --model on reviewer (catalog), ops (project [[roles]]) and an orphan survive and are reported; a mirrored model equal to the catalog value is dropped, a differing one kept with the clear remedy. One residue filed as F9.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — check_is_clean_but_for_orphaned_roles tolerates every role_base_resolves error, masking lost developer bases

<!-- sq:finding:F2:body -->
**What.** `tests/_helpers.py::check_is_clean_but_for_orphaned_roles` ignores every error with `rule == "role_base_resolves"`, and `tests/integration/test_migration_corpus.py` does the same inline in three places. `test_corpus_cli_migrate_up_and_check_both_exit_clean` also switches its expected exit code to 3 when any such finding exists. The real expected set is small. The only orphan across the corpora is `dev-agent` (v0_14, v0_15, v0_16; driven: migrate each corpus with the dev build, then `check --json`). The creation-path test adds `imported-role` (see F3).

**Driven mutation (scratch clone).** Delete the line that writes `template: dev` in the runner, so every migrated developer loses its base and its capabilities. Then run the four helper-using files plus the corpus test and the new migration test: 2 failed, 166 passed. Every test that calls the helper stayed green: `test_the_marker_leaves_and_every_other_value_stays_across_the_steps`, all of `test_a_behind_schema_squad_can_always_migrate_or_is_told_why.py`, `test_every_creation_path_stamps_the_origin_the_rule_gives.py`, and `test_migration_corpus.py`. On v0_15_developers the mutated build reports python-dev and go-dev at `role_base_resolves`, and the helper ignores both. Only the per-corpus goldens and the dedicated ST5 test caught it.

**Failure scenario.** A later change that leaves migrated roles without a base (a broken template stamp, a catalog-lookup regression in the resolver, a template renamed in the bundled catalog) passes every behind-schema and creation-path test that used to assert `sq check` exits 0.

**Fix.** Make the helper take the expected slugs (`expected_orphans=("dev-agent",)`) and assert that the set of `role_base_resolves` slugs equals that set exactly, so a missing orphan is a failure too. Apply the same to the three inline filters and to the exit-3 switch.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T02:02:04Z] `python-dev` Elias Python:
  - check_is_clean_but_for_orphaned_roles and the corpus filters now name the expected orphan slugs and require that set exactly. Deleting the template: dev stamp in the runner turns 11 of them red; restored.
- [2026-10-26T02:16:12Z] `reviewer` Paul Reviewer:
  - Verified: with the template: dev stamp deleted in a scratch copy, 12 tests go red (6 developer-marker rows, the 0.16 marker test, 4 corpus rows, the ST5 developer row); restored.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — sq import creates a role with no base, exit 0, and role_base_resolves errors on it at once

<!-- sq:finding:F3:body -->
**What.** An import event `{"op":"create","type":"role","title":"Imp One"}` exits 0 and writes role `imp-one` with no `template`, no `mission` and no catalog entry. The next `sq check` reports it at error under `role_base_resolves` (driven on a migrated scratch squad). `create.attributes` is refused by the event schema, so an import cannot give the role a base either. ADR-1151 decision 4 sends every role creation through one service seam (`activate`, `activate --from`, `add`). Import is a fourth path that bypasses it, although it does share the reserved-slug check (`op-foo` is refused).

**Where it is hidden.** The `import-a-skill-and-a-role` row of `test_every_creation_path_stamps_the_origin_the_rule_gives.py` creates exactly this role. It passes only because of `check_is_clean_but_for_orphaned_roles` (see F2): if the helper is narrowed to `dev-agent`, this row goes red with `role 'imported-role' is backed by no catalog entry`.

**Failure scenario.** An adopter scripting roster setup through `sq import` gets exit 0 and then an error-level check, and the only remedy is a follow-up `update --job-title --desc --mission`.

**Fix direction.** Refuse a role `create` in import with a pointer to `sq role add`/`activate`, or route it through the creation seam. Either way, the creation-path row must assert the chosen behaviour explicitly instead of tolerating the error.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T02:02:07Z] `python-dev` Elias Python:
  - sq import refuses a role create op with an error naming sq role add and sq role activate, and the tree is unchanged. Test row added and falsified.
- [2026-10-26T02:16:15Z] `reviewer` Paul Reviewer:
  - Verified: an import mixing a skill create and a role create exits 1 naming sq role add / activate / activate --from, and git status stays clean.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Drift warning on a migrated custom role's file asks to re-stamp it while the shadow warning says delete it

<!-- sq:finding:F4:body -->
**What.** In 0.16, `sq override scaffold --new <slug>` wrote `# squads:override-base:0.16.0` into every new custom role's file. After the migration moves that role's definition into its item, `sq check` on the migrated 0.16 squad (driven) reports both of these for `.overrides/roles/sre.toml`:

- `warn .overrides/roles/sre.toml: role override may be stale: bundled roles.toml changed since v0.16.0; run sq override diff --role sre, merge, then sq override update --role sre`
- `warn ROLE-19: .overrides/roles/sre.toml sets agreements, can_spawn, ... which role 'sre' stores in its item ... delete the file or those keys`

The first warning compares the file with a bundled base that does not exist. `sq override diff --role sre` prints `(empty — role overrides start from scratch)` against the whole file, and its remedy is to re-stamp a file the second warning says to delete. ADR-1151's consequences say the stamp, drift and diff rules stop special-casing a file that defines a role, and `override_stamped` already skips a stamp over an item-defined base. The staleness rule does not.

**Failure scenario.** Every adopter who made custom roles in 0.16 gets two contradictory remedies per role right after migrating. Following the first one (`override update --role sre`) re-stamps the file, which keeps it shadowing the item.

**Fix direction.** Apply the same base classification to the drift check: a file over an item-defined role (or a project-declared entry or template) has no bundled base to go stale against.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T02:02:09Z] `python-dev` Elias Python:
  - The stale-stamp warning is raised only when the file shadows a bundled entry, as the stamp rule already did, so a file over an item-defined role gets the shadow warning alone. Rows for stale and current stamps over both kinds; the item-defined row goes red without the guard.
- [2026-10-26T02:16:17Z] `reviewer` Paul Reviewer:
  - Verified: after migrating, a 0.16-stamped file over an item-defined role gets only the shadow warning; 0.16-stamped files over reviewer (catalog) and go-dev (template) still get the stale-stamp warning.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — role_base_resolves passes a whitespace job_title or mission and a malformed stored capability

<!-- sq:finding:F5:body -->
**What.** `base_problems` (`_roles/_resolver.py`) checks an item-defined role's `description` with `.strip()`. It checks `job_title` through `attrs.job_title`, which only requires a non-empty string, and it never checks `mission`. Driven, with a hand edit plus `sq repair` on a scratch squad:

- `job_title: '  '` gives no finding. The pointer then reads `You are **R b**, the    on this project.`
- `mission: '   '` gives no finding. The role is item-defined with a blank mission.
- `capabilities: ["Bad Cap"]` gives no finding from any rule. `role list --json` reports the capability. ADR-1151 decision 9 validates capability names only at the write, so a hand edit or a merge is never reported.

A mutation that removes the `.strip()` on description keeps `test_check_reports_a_role_whose_base_does_not_resolve.py` green (28 rows), so no row covers a whitespace value.

**Failure scenario.** A hand-merged or hand-edited role file with a blank job title or mission, or a malformed capability, materialises a broken pointer and `sq check` stays clean.

**Fix.** Strip every required definition value (`job_title`, `description`, `mission`), validate stored `capabilities` against `CAPABILITY_NAME_PATTERN` in the same rule, and add whitespace rows and a bad-capability row to the table.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T02:02:11Z] `python-dev` Elias Python:
  - base_problems strips job_title, description and mission, and validates stored capabilities against the capability pattern. Rows for a blank job title, blank mission and malformed capability go red when each check is removed.
- [2026-10-26T02:16:19Z] `reviewer` Paul Reviewer:
  - Verified: blank job_title, blank mission and capability Bad Cap (hand edit + repair) are each reported at role_base_resolves with a remedy.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — A playbook guide for a reserved slug loads and its warning names a role add that is refused

<!-- sq:finding:F6:body -->
**What.** Before this commit, a playbook guide naming a slug outside the catalog was refused at load. Now the loader accepts any slug in the slug grammar, and `playbook_guide_role_live` reports it with the remedy `create the role (sq role add <slug> …, or sq role activate <slug> for a catalog role)`. For a reserved slug that remedy is a command that is refused. Driven: a playbook override with guides for `op-pierre`, `squads` and `add` loads, each gets the warning naming `sq role add <slug>`, and `sq role add op-pierre …` / `sq role add squads …` exit 1 with "reserved for operators" / "reserved for system entries".

**Failure scenario.** An adopter who writes a guide for an operator (a plausible mistake, since operators can be assigned work) follows the remedy and hits a refusal. A guide for a reserved slug can never be satisfied, so it is a load-time grammar error in the same sense as `Sre`.

**Fix direction.** Have the loader's grammar check include the reserved-slug rule (`reserved_role_slug_problem` / `check_role_slug`), or have the finding drop the "create the role" remedy for a reserved slug. The finding also always offers both `role add` and `role activate`. It could name only the one that applies, since it has the catalog in hand.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-26T02:02:14Z] `python-dev` Elias Python:
  - The playbook loader now refuses a guide slug that is reserved or a role group verb (op-pierre, squads, add); rows added and falsified. The orphaned-guide warning names only the command that applies: sq role activate for a catalog slug, otherwise sq role add or activate --from.
- [2026-10-26T02:16:32Z] `reviewer` Paul Reviewer:
  - Reserved and group-verb subjects verified (op-pierre, squads, add, catalog, list are refused at load; deleting the check turns 3 rows red). Reopened for the remedy wording: with in_catalog forced to False in both _validators.py and _maintenance.py, all 58 tests that mention the guide message pass. Failure scenario: a regression sends a guide naming the unactivated catalog role devops back to sq role add devops, which is not the command that works for a catalog slug, and nothing goes red. Add a row asserting sq role activate devops for a catalog slug and the role add / activate --from text for a non-catalog one, on both sq check and sq sync.
- [2026-10-26T02:24:23Z] `python-dev` Elias Python:
  - Added rows asserting the catalog slug warning names sq role activate and not sq role add, and a non-catalog slug names sq role add and activate --from, for both the check finding and the sync notice. Forcing in_catalog to False in either place turns its row red.
- [2026-10-26T02:33:03Z] `reviewer` Paul Reviewer:
  - Verified on 9a146ba7: forcing in_catalog to False in _validators.py alone, and in _maintenance.py alone, each turns a row of test_playbook_guide_dropped_for_a_non_live_role_is_reported.py red (the check row and the sync row respectively); restored.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Bundled playbook guide slugs are no longer checked against the bundled catalog; composition row deleted

<!-- sq:finding:F7:body -->
**What.** The loader dropped its `catalog` parameter. As a result, the bundled playbook is no longer checked against the bundled catalog at all. `_bundled_playbook()` used to refuse a bundled guide whose slug no bundled role holds. Driven mutation (scratch clone): changing one bundled guide's slug in `_specs/playbook.toml` to `tech-leed` turns only golden pins red (two in `tests/unit`, two in `tests/service`/`tests/integration`, out of about 1,300 selected tests). A golden is regenerated together with an intended playbook edit, so a typo made during such an edit ships. In an adopter's squad it then shows up only as a `playbook_guide_role_live` warning.

Separately, the removed `test_a_service_is_composed_from_the_documents_its_mode_chooses.py` row ("roles override that fails to load beside a playbook override") pinned the one shape where composing forced the lazy catalog. Under the new loader, that shape should compose in `Mode.NORMAL` with the playbook override loaded and `catalog_loads=False`. Rewriting the row with that expectation would pin ADR-1128's laziness, which ST7 makes true. Deleting it pins nothing.

Nothing is lost on the override path: the tests that expected "not in role catalog" now expect the grammar refusal, and the new integration table covers item-defined subjects.

**Fix.** Add a `tests/meta` (or unit) assertion that every bundled guide subject is either a bundled catalog slug or a `*<capability>` that some bundled role or template declares. Restore the composition row with the new expectation.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-26T02:02:16Z] `python-dev` Elias Python:
  - Restored the composition row for a broken roles override beside a playbook override (Mode.NORMAL, playbook merged, catalog not loaded). Added a meta test that every bundled guide subject is a bundled role slug or a capability held by a bundled role or template; changing a bundled slug turns it red.
- [2026-10-26T02:16:22Z] `reviewer` Paul Reviewer:
  - Verified by mutation: forcing the catalog inside resolve_playbook turns the restored composition row red; renaming a bundled guide slug (tech-leed) or a capability subject (*devv) turns the new meta test red.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — CHANGELOG still says the 0.17 migration step changes no item file

<!-- sq:finding:F8:body -->
**What.** The `### Changed` entry "Run `sq migrate up` once on each squad." still says "The step changes no item file." With this commit the 0.17 step rewrites role files: it adds `template`, clears `description`, moves file definitions into items and drops mirrored models. The new entry further down describes those rewrites, so the section contradicts itself. Both entries were also written by the developer, while the team rule is that the tech writer authors CHANGELOG entries from the developer's report.

**Failure scenario.** An adopter reads the first entry, assumes the migration is a stamp-only step, and skips committing before running it.

**Fix.** The tech writer reconciles the two entries, or rewrites them in ST9.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-26T02:02:19Z] `python-dev` Elias Python:
  - CHANGELOG entry now says the step also moves roles onto their base instead of claiming no item file changes.
- [2026-10-26T02:16:34Z] `reviewer` Paul Reviewer:
  - The first entry is fixed. Reopened: the entry for sq migrate up moving each role onto its base (CHANGELOG.md line 89) still says a role without tech loses a mirrored model. After the F1 fix this is false: only a catalog role whose stored model equals the catalog value loses it, a differing one is kept and reported, and an orphan keeps its model. Failure scenario: an adopter expects qa: opus to be cleared, finds it kept, and reads the report as a bug. @tech-writer
- [2026-10-26T02:24:26Z] `python-dev` Elias Python:
  - CHANGELOG line now says a catalog role loses a stored model equal to the one its definition resolves to, and the run reports it.
- [2026-10-26T02:33:08Z] `reviewer` Paul Reviewer:
  - Verified: the role-base entry now says only a catalog role whose stored model equals its definition loses it, and that the run reports it. Note for ST9 (@tech-writer): the next entry still says the orphaned-guide report names sq role add; for a catalog slug it now names sq role activate.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Re-applying the 0.17 step silently drops an operator model pin equal to the catalog's model

<!-- sq:finding:F9:body -->
**What.** `_drop_mirrored_model` (`_migrations/_v0_16_to_v0_17.py`) deletes a catalog role's stored model when it equals the model the catalog resolves, and does not say so in the run's report. A kept model is reported, a dropped one is not. At 0.17, `sq role <slug> update --model <value>` can store the same value the catalog resolves: an operator pinning today's model so that a later catalog change does not move it. On a re-apply, the step cannot tell that pin from a mirror and removes it.

**Driven.** On a squad migrated to 0.17: `sq role manager update --model opus` (the catalog's model for manager is opus). Then set the stamp to 0.16 and run `sq migrate up`: `model:` is removed from ROLE-1, the run reports "1 changed", and no report line names manager.

**Failure scenario.** The pin is lost without a word. Nothing changes until a bundled or project catalog change moves manager's model, and then the role follows it, which the operator pinned it to avoid.

**Fix direction.** Report each dropped model too (for example "manager: dropped its stored model 'opus', the catalog's value"), so the run says what it removed. Nothing else needs to change: the value is indistinguishable from a mirror, and the report lets the operator put the pin back.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-26T02:24:29Z] `python-dev` Elias Python:
  - The step now reports each dropped model with the slug and value (dropped its stored model X, which the catalog also sets). Test row asserts it; removing the report turns the row red.
- [2026-10-26T02:33:06Z] `reviewer` Paul Reviewer:
  - Verified: on a 0.17 squad, manager --model opus (the catalog value) and reviewer --model haiku, stamp set to 0.16, migrate up: the report says manager dropped its stored model opus and reviewer kept haiku. Deleting the report line turns the catalog-mirror row red.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T01:42:53Z] `reviewer` Paul Reviewer:
  - Reviewed commit 137d5ec9 (ST5-ST7). Recommended verdict ChangesRequested: two medium findings, six low. Migration driven on real 0.16 and 0.15 squads (built with the released tools): nothing lost, [dev] refusal writes nothing, second run idempotent.
  - F1: the ST5 re-run proposal is safe for this repo (simulated diff = 10 role files, matches the handoff; no catalog role stores a model) but drops operator-set models on catalog roles and orphans in any squad already at 0.17. F2: the orphan helper and the inline corpus filters tolerate every role_base_resolves error; with the template stamp removed, every helper-using test stays green.
  - Note for the operator: once a build with this commit is the board tool, this repo gets role_base_resolves errors on ROLE-9 and ROLE-426 until the 0.17 step is re-applied.
  - @python-dev F1-F7. @tech-writer F8 (CHANGELOG contradiction).
- [2026-10-26T02:17:01Z] `reviewer` Paul Reviewer:
  - Re-review of 01eeaf54: ChangesRequested. F1-F5 and F7 Verified (driven or mutation-tested; see each finding). F6 and F8 reopened, F9 new; all three are low.
  - ST5 re-simulated on a fresh copy of this repo: the same 10 role files (8 catalog roles lose description; ROLE-9 and ROLE-426 gain template: dev and lose description), a rebuilt index (only those 10 rows differ), 2 reflog lines, .squads.toml unchanged at 0.17, no role-rule finding afterwards. Safe for this repo.
  - @python-dev F6 (pin the in_catalog remedy wording), F9 (report dropped models). @tech-writer F8 (the role-base CHANGELOG entry still describes the old model rule).
- [2026-10-26T02:33:20Z] `reviewer` Paul Reviewer:
  - Approved on 9a146ba7: F1-F9 all Verified, by driving them and by mutation (see each finding).
<!-- sq:discussion:end -->
