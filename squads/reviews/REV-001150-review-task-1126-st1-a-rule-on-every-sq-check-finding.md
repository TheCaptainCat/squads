---
id: REV-1150
sequence_id: 1150
type: review
title: 'Review TASK-1126 ST1: a rule on every sq check finding'
status: Approved
author: reviewer
refs:
- TASK-1126
description: 'Review of commit 61b1f474: CheckIssue.rule, the rule registry, the meta
  guard and the per-source --json table.'
subentities:
- local_id: F1
  title: A misfiled binding rule passes the guard and every test
  status: Verified
  severity: medium
- local_id: F2
  title: 'Binding-rule liveness test is vacuous: it reads the registry'
  status: Verified
  severity: low
- local_id: F3
  title: Guard misses aliased, attribute, replace and delegated shapes
  status: Verified
  severity: low
- local_id: F4
  title: is_binding is dead and wrong for the common core
  status: Verified
  severity: low
- local_id: F5
  title: sq import --json drops the rule from the same findings
  status: Verified
  severity: low
- local_id: F6
  title: overrides_sound folds several distinct defects into one rule
  status: Verified
  severity: info
created_at: '2026-10-25T20:18:11Z'
updated_at: '2026-10-25T21:14:01Z'
---
<!-- sq:body -->
## Scope

Commit 61b1f474 (TASK-1126 ST1): the `rule` field on `CheckIssue`, the registry in `_services/_check_rules.py`, the meta guard, the per-source `--json` table and the regenerated golden.

## What holds

- Every `CheckIssue(` construction under `src/` passes a rule, and every catalog member files its findings under its own declared name (AST listing of all sites, read). The helpers outside members (`on_disk_not_indexed`, `not_on_disk`, `backend_entry_missing`, `backend_entry_drift`) carry their member's name.
- The override tuples are stamped `overrides_sound` at the one site that converts them. A broken workflow or playbook override reports once, under `workflow_loads` or `playbook_loads`, not also under `overrides_sound` (driven, scratch squad).
- `corpus_scans` is reachable: a corrupt `.squads.json` reports it in `--json` with exit 3 (driven).
- No message-text matching is left in the check path. The `startswith("on disk but not in index")` filter is now `rule == "index_reconciled"`, and the only remaining `.message` reads are display and the sort key.
- The golden diff adds only `rule` to each object. That is additive, as `docs/stability.md` Tier 3 promises.
- `sq repair` emits no check findings, so it has no rule surface to name.
- The new comments and docstrings are short, in the present tense, and free of ticket IDs.

## Findings

F1 to F6 below. The test gaps are F1 to F3. F4 is a dead, inaccurate registry helper. F5 is `sq import --json`, which drops the rule. F6 is the granularity of `overrides_sound`.

## Verdict

Request changes on F1, then F2 to F5. F6 is a judgment call.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1150 add-finding "…" --severity medium`; track with `sq review 1150 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A misfiled binding rule passes the guard and every test

<!-- sq:finding:F1:body -->
Driven: a mutated copy of the source, run through `PYTHONPATH`, in a scratch squad.

The guard only cross-checks the rule inside a catalog member's own function. The 20 non-catalog sites in `_services/_check.py` and `_cli/_main.py` are checked only for *being registered*, so a site that files its finding under the wrong binding rule passes the guard. The per-source table (`tests/cli/test_check_json_names_the_rule_of_each_source.py`) is the only other net, and it plants one defect for 11 sources. It plants nothing for `view_target_resolves`, `view_tag_in_region`, `seeded_view_resolves`, `body_regions_present`, `file_readable`, `id_present`, `id_well_formed`, `fields_valid`, `timestamps_present`, `numbers_unique` or `corpus_scans`. The task asked for a row for the config-load path, and `corpus_scans` has none.

**Failure scenario, measured.** I changed `_check.py` so that the malformed-id site passes `"id_present"` and the `fields_valid` site passes `"numbers_unique"`. The guard reports no problems on the mutated file. The meta guard, the per-source table, `tests/cli/test_json_output_shape.py` and the one other test that reads `.rule` all pass (60 passed). At runtime, `sq check --json` on a file with `id: garbage` reports `"rule": "id_present"`. A tool told to match by rule now reads a malformed id as a missing one, and a frontmatter type error as a shared counter number.

**Fix.** Either give every binding rule a planted-defect row in the table (it is one table, and each rule is its own branch), or pin each non-catalog site to its rule statically: a table of (function, message-producing call) to rule that the guard checks. The first is simpler and also proves that the rule reaches `--json`.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T20:35:03Z] `python-dev` Elias Python:
  - Fixed: the per-source table now plants a defect for every binding rule (24 rows); a misfile of id_well_formed, fields_valid, view_target_resolves, corpus_scans or override_current turned the table red.
- [2026-10-25T20:57:35Z] `reviewer` Paul Reviewer:
  - Reopened at 12ce57b2. The fix pins one site per rule, but five binding rules are filed from more than one site, and the extra sites are still unpinned.
    
    What holds (driven, mutated copies via PYTHONPATH): swapping `id_well_formed` and `id_present` reddens the "no id" and "bad id" rows. Misfiling `id_well_formed` as `id_present` and `fields_valid` as `numbers_unique` reddens two rows and the liveness test.
    
    What fails (measured): in `_overrides/_service.py` I misfiled three sites. The roles-catalog-invalid site (line 1406) went from `override_loads` to `override_stamped`, the template missing-marker site (1529) from `override_loads` to `override_current`, and the role-override read-error site (1586) from `override_loads` to `override_stamped`. The static guard passes, and so do all 240 test files that mention override rules or `.overrides` (4495 passed). The 4 failures in that run are `tests/meta/test_bundled_docs_registry.py`, which reads docs relative to the copied package (inferred, not related).
    
    Unpinned sites: `override_loads` at 1406, 1505, 1529 and 1586 (only the role does-not-load site, 1676, has a row). `override_stamped` from a role (1597) and the error branch of `_stamp_issue` (workflow, playbook, roles catalog). `override_current` for a template (1558) and a role (1608). `view_tag_in_region` from a template override (1511).
    
    Fix: one row per site, not per rule. That is about eight more rows in the same table.
- [2026-10-25T21:03:49Z] `python-dev` Elias Python:
  - Fixed: every override site has its own table row, the guard pins a function-to-rules table so a new or moved site fails, the variable-rule allowance is limited to the override forwarding comprehension, and rebinding, type(x)(...) and __class__(...) are refused; all 30 sites were misfiled one by one and each turned red.
- [2026-10-25T21:13:27Z] `reviewer` Paul Reviewer:
  - Verified at 3e7c5a83, measured with mutated copies through PYTHONPATH.
    
    - **Override misfilings.** I misfiled four sites, one at a time: 1406 to `override_stamped`, 1505 to `override_current`, 1529 to `override_current` and 1586 to `override_stamped`. Each fails exactly its own row in the per-source table (catalog override invalid, template unreadable, template markers, role unreadable). The three together also fail the `_SITES` pin in the static guard.
    - **New site.** An unlisted new construction in `_check.py`, filed under the registered rule `markers_balanced`, fails `test_every_construction_site_files_under_its_pinned_rule`.
    - **F3 shapes.** The guard now refuses `CI = CheckIssue`, `type(issue)(...)` and `issue.__class__(...)`. It also refuses a variable rule anywhere other than the comprehension over `check_override_issues` in `check` in `_check.py`, including a generator, a nested comprehension, another function and another module. The legitimate forward still passes.
    - **Unmutated tree.** The guard and the table pass (42 passed).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Binding-rule liveness test is vacuous: it reads the registry

<!-- sq:finding:F2:body -->
Read: `tests/meta/test_every_check_finding_names_a_registered_rule.py::test_every_binding_rule_is_constructed_somewhere`. Measured with an AST walk.

The test collects every string constant in every module under `src/squads` and asserts that `set(BINDING_RULES)` is a subset. The walk includes `_services/_check_rules.py`, whose `BINDING_RULES` dict keys are exactly those constants. An AST walk of `_check_rules.py` alone already satisfies the subset (`True`). So the test cannot fail: delete every construction of `id_well_formed` and leave the registry entry, and it stays green.

**Failure scenario.** A refactor drops the malformed-id branch, or folds it into `fields_valid`. `BINDING_RULES` keeps advertising `id_well_formed`, and the adopter docs table being written from it keeps documenting a rule that no code emits. Nothing goes red.

**Fix.** Exclude `_check_rules.py` from the walk, and better, collect only the rule argument of `CheckIssue(...)` calls (the guard's `_rule_literal`), not every string in the tree. Then falsify it by deleting one site.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T20:35:06Z] `python-dev` Elias Python:
  - Fixed: the liveness test collects only the rule argument of real construction sites and skips the registry module; dropping a site turned it red.
- [2026-10-25T20:57:37Z] `reviewer` Paul Reviewer:
  - Verified at 12ce57b2. The liveness test now counts only the rule arguments of real constructions and skips `_check_rules.py`. Falsified: dropping the only `id_well_formed` construction fails it with `{'id_well_formed'}`, and the misfiling mutant fails it with `{'fields_valid', 'id_well_formed'}`.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Guard misses aliased, attribute, replace and delegated shapes

<!-- sq:finding:F3:body -->
Read the guard, then ran it on probe sources (`_problems` imported from the test module).

The visitor matches only `ast.Name` calls whose id is `CheckIssue`. It is caught as a positional literal, a keyword literal, a variable and `*args`. It is missed as:

- `_results.CheckIssue("error", "x", "m", "nope")` (an attribute call)
- `from ... import CheckIssue as CI; CI(..., "nope")` (an aliased import)
- `dataclasses.replace(issue, rule="nope")` (restamping an existing finding)
- `functools.partial(CheckIssue, rule="nope")`
- a helper outside a member that a member calls and that files under a sibling's name: `def helper(): return CheckIssue(..., "parent_in")` called from `_dangling_ref`. The member-name cross-check keys on the enclosing function, so it does not see the delegation. The real code already delegates this way (`_index_reconciled` to `on_disk_not_indexed`/`not_on_disk`, `_backend_reconciled` to `backend_entry_*`), so this is a live shape, not a hypothetical one.

None of these shapes exists in `src/` today: every site is a bare `CheckIssue(` call, and none re-stamps a rule. The guard's docstring promises "every construction", though, and the delegation shape is the one that will be copied next.

**Fix.** Resolve the call target by what the module imports, not by spelling: match `CheckIssue` and any alias bound to it in the module, plus `Attribute(attr="CheckIssue")`. Treat `replace(...)` with a `rule=` keyword as a construction. For delegated helpers, either require that a helper outside a member is called only from the member whose name it files, or add the helper names to the table F1 proposes.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T20:35:08Z] `python-dev` Elias Python:
  - Fixed: the guard resolves aliases, attributes, replace(rule=) and partial(CheckIssue); helpers outside a member are pinned by a name table, and a helper called from a sibling member is refused. A variable rule is refused except the one forwarding site in check.
- [2026-10-25T20:57:40Z] `reviewer` Paul Reviewer:
  - Verified at 12ce57b2. Each shape I listed is now caught when run through `_scan`: attribute call, aliased import, `dataclasses.replace(rule=...)`, `functools.partial`, and a helper outside a member that files under a sibling's name. So are `**kw`, `*args`, a variable rule, `_issue` with a variable, and a conditional with an unregistered arm.
    
    Residual, not reopened: it still misses `CI = CheckIssue` assignment aliases, `type(issue)(...)`, and `issue.__class__(...)`. The forwarding exemption also accepts any variable rule inside `check` in `_check.py`, not just the override forward. None occurs in `src/` today.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — is_binding is dead and wrong for the common core

<!-- sq:finding:F4:body -->
Read, and confirmed by `uv run --all-extras vulture` (`unused function 'is_binding'`; `is_registered` is used only by the test).

`is_binding` has no caller in `src/` or `tests/`. Its docstring says "Whether no `validators` selection can turn *rule* off", and it returns `rule in BINDING_RULES or rule in ALWAYS_ON_SQUAD_GLOBAL_NAMES`. That is false for the per-item `COMMON_CORE` members (`item_status_valid`, `dangling_ref`, `ref_kind_valid`, `agent_registered`, `parent_acyclic`, `attribute_valid`), and for each category bundle's members on a type of that category. `effective_validator_names` documents the composition as an "extend-only floor — a type may add to a bundle, never subtract from it", so no selection can turn those off either. They can only be relevelled.

The ST1 handback carries the same error into ST2: "**Selectable:** every per-item catalog member … common core and category bundle". An adopter told that `dangling_ref` is selectable who tries to drop it from a type's `validators` list finds that it still runs.

**Failure scenario.** The first consumer of `is_binding`, for example a `--json` `binding` flag or a docs generator, reports `dangling_ref` as deselectable.

**Fix.** Delete `is_binding` (no consumer, and the registry docstring already says every entry is binding). Correct the selectable/binding note on the task for the writer: the common core and category bundles are always on and only relevellable. If a three-way classification is wanted (binding, relevellable floor, selectable), make it a decision rather than a helper.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-25T20:35:11Z] `python-dev` Elias Python:
  - Fixed: is_binding deleted. Correction for the docs is on TASK-1126: common core and category bundles are always on and can only be relevelled.
- [2026-10-25T20:57:42Z] `reviewer` Paul Reviewer:
  - Verified at 12ce57b2. `is_binding` is gone (vulture now flags only `is_registered`, which only the test uses). The handoff correction e44b241 on TASK-1126 states that the common core and category bundles are always on and can only be relevelled.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — sq import --json drops the rule from the same findings

<!-- sq:finding:F5:body -->
Read: `src/squads/_cli/_import.py:76-78`.

`sq import` returns the same `CheckIssue` objects that `sq check` reports, from the same catalog (`_services/_import.py::_board_debt_findings`). Its `--json` payload serialises them as `{"level", "item", "message"}` and drops `rule`. The change's whole stated purpose, which the writer's draft repeats ("a tool that reads this output should match a finding by `rule`, never by `message`"), therefore holds for one of the two `--json` surfaces that emit check findings and not the other.

**Failure scenario.** An importing pipeline gates on `subentity_body_written` findings after `sq import --json`. It has no rule key to match, so it falls back to the message-text matching this task exists to retire.

**Fix.** Add `"rule": f.rule` to the import `issues` objects. This is additive under the same Tier 3 promise. Add one assertion to an existing import `--json` test.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-25T20:35:13Z] `python-dev` Elias Python:
  - Fixed: sq import --json issues carry rule; the import json test asserts it.
- [2026-10-25T20:57:44Z] `reviewer` Paul Reviewer:
  - Verified at 12ce57b2. `sq import --json` issues carry `rule`. Falsified: removing the key from `_cli/_import.py` fails `test_the_json_payload_carries_the_level_and_still_says_it_applied`.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — overrides_sound folds several distinct defects into one rule

<!-- sq:finding:F6:body -->
Read: `_overrides/_service.py::check_override_issues`, and the stamp at `_services/_check.py:510`.

`overrides_sound` covers five sub-sources (template, role TOML, workflow, playbook and roles-catalog overrides) and at least three distinct defects at two levels: a shadowing override with no stamp (error), drift from the bundled base (warn), and a structurally broken or unloadable override (error). Every other source in this change gets one rule per defect (`id_present` and `id_well_formed` are separate, as are `ids_unique` and `numbers_unique`). This one collapses its defects into a single name because the producer returns bare tuples, so the stamp happens after the information is gone.

**Failure scenario.** A tool wants to auto-run `sq override update` on drift warnings only. Every `overrides_sound` finding looks the same by rule, so it has to parse the message to tell "drifted" from "does not load".

**Fix (judgment call).** Have `check_override_issues` return `CheckIssue`s (or 4-tuples) with per-defect rules, for example `override_stamped`, `override_current`, `override_loads`, which also brings these sites under the guard. If one rule per source is the intended grain here, say so in the registry docstring so that the inconsistency reads as a decision.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-25T20:35:16Z] `python-dev` Elias Python:
  - Fixed: overrides_sound split into override_stamped, override_current and override_loads, stamped at the override service, so they sit under the guard.
- [2026-10-25T20:57:47Z] `reviewer` Paul Reviewer:
  - Verified at 12ce57b2, driven in a scratch squad. A drifted workflow override reports `override_current` (warn). An unstamped shadowing workflow override reports `override_stamped` (error). A role override that does not load reports `override_loads`, and so do an invalid roles catalog and a template missing a marker. Falsified: swapping the stamped/current mapping in `_stamp_issue` reddens the "drifted" row.
    
    Note for the docs, no change asked: a workflow or playbook override that does not load reports `workflow_loads` or `playbook_loads`, not `override_loads`. Only role, roles-catalog and template overrides use `override_loads`.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T20:18:35Z] `reviewer` Paul Reviewer:
  - Review of 61b1f474 done: 6 findings (F1 medium, F2-F5 low, F6 info). Rule names, the overrides stamp, the config-load rules and corpus_scans are all correct in --json, the golden diff is additive only, and no message-text matching is left. F1 is measured: misfiling id_well_formed and fields_valid under other registered rules passes the guard and the per-source table (60 passed). F4 corrects the ST2 handback: the common core and category bundles cannot be deselected. Recommend request changes on F1-F5; F6 is a judgment call. @python-dev for fixes, @tech-writer note F4 before finishing the binding docs.
- [2026-10-25T20:19:14Z] `manager` Catherine Manager:
  - Fix F1-F6. F6 ruling: one rule per override problem (unstamped, drifted, does not load), like every other source. Also fix two defects the writer found: timestamps_present emits level "warning" instead of "warn"; workflow_loads on an unknown validator name gives no cause.
- [2026-10-25T20:57:56Z] `reviewer` Paul Reviewer:
  - Verified 12ce57b2: F2-F6 Verified, F1 reopened. F1: the per-source table pins one site per rule, but override_loads, override_stamped, override_current and view_tag_in_region are filed from several sites each. Misfiling three override sites passed 4495 tests (details on F1). The two extras hold, driven: timestamps_present is level warn (falsified, the row reddens on "warning"), and workflow_loads names both unknown validators. Not ready to approve until F1 is fixed. @python-dev
- [2026-10-25T21:13:28Z] `reviewer` Paul Reviewer:
  - All six findings Verified at 3e7c5a83. Recommend approval; I leave the transition to the approver.
- [2026-10-25T21:14:00Z] `manager` Catherine Manager:
  - Approved: F1-F6 Verified; full suite green at 3e7c5a83.
<!-- sq:discussion:end -->
