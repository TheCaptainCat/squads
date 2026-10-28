---
id: FEAT-1202
sequence_id: 1202
type: feature
title: Check rule test suite
status: Done
author: product-owner
refs:
- MILE-1051:targets
- ADR-1201
description: Breach tests for every sq check rule, with param and level cases and
  a guarded coverage marker.
subentities:
- local_id: US1
  title: Harness, guard and baseline
  status: Done
- local_id: US2
  title: Parent and ref rules
  status: Done
- local_id: US3
  title: Sub-entity and prose rules
  status: Done
- local_id: US4
  title: Attribute and roster item rules
  status: Done
- local_id: US5
  title: Roster config rules
  status: Done
- local_id: US6
  title: Work policy rules
  status: Done
- local_id: US7
  title: Corpus integrity rules
  status: Done
- local_id: US8
  title: Config load rules
  status: Done
created_at: '2026-10-28T08:34:00Z'
updated_at: '2026-10-28T10:41:23Z'
---
<!-- sq:body -->
## Problem

`sq check` is the largest uncovered block of `src/squads`: about 1,200 lines across the validators, the check service and the validity clauses check members call. The CLI surface tests give the command five cases, one per parameter, and nothing exercises the rules it reports.

## Scope

Test every rule `sq check` reports, as ruled by ADR-1201: one breach test per rule of `CATALOG` (30), `SQUAD_GLOBAL_CATALOG` (17) and `BINDING_RULES` (22), through `sq check --json`, each with its in-test clean pre-state and near-miss sibling; param and level cases derived from the name tables; a `breaches` marker with a `tests/meta` guard that derives the required declarations from the tables. The rules (whole-array assertions, exit codes, opt-in members enabled by a minimal override, only `sq check` output counts, falsification, layout) are ADR-1201's and are not restated here.

Deliverables:
- the harness: `tests/check/conftest.py` (`check_json`, `select_validators`, the `breaches` teardown), `tests/_check_surface.py`, the guard, the registered marker, `test_baseline.py`;
- the modules of ADR-1201 section 7 under `tests/check/`, one story per group.

## Out of scope

- Unit tests of member functions.
- Gate refusals on create, update, retype and import: held by the CLI surface cases.
- Why a spec or override is refused at load (`_workflow/_loader.py`, `_specmerge.py`): a separate decision. Only one malformed override per load rule is reported here.

## Acceptance criteria

- Every rule of the three tables has a breach test with a clean pre-state; every param case (`name:param`) and level case (`name@level`) the tables derive exists.
- The `breaches` guard in `tests/meta` is green with no missing or stale declaration, and stays valid under `-k`, `--lf` and xdist.
- Each test was shown red three ways when written (breach, clean, param or level), then restored.
- The suite stays fast: the full local run is about 25 s today and must stay in the same order; every CI test job under 10 minutes, Windows full suite at most 15.
- pyright, ruff and `sq check` are clean.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1202 add-story "As a <role>, I want … so that …"`; track with `sq feature 1202 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Harness, guard and baseline

<!-- sq:story:US1:body -->
## Scope

The foundation the rule stories build on.
- `tests/check/conftest.py`: `check_json` (runs `sq check --json`, records the reported rule and level pairs), `select_validators` (writes the minimal override with splat references and records what it selected) and the `breaches` teardown.
- `tests/_check_surface.py`: the derivation of required declarations from the three rule tables, with no stored list of rules.
- The `breaches` pytest marker, registered, and the `tests/meta` guard over `tests/check/`.
- `test_baseline.py`: the `minimal` squad under the bundled spec reports `[]`.

## Acceptance

- The guard fails on a seeded missing, stale or undeclared rule, param or level, and passes on the tree.
- A test that declares `breaches` without `check_json` fails; a declaration no run honours fails that test at teardown.
- The guard and teardown stay valid under `-k`, `--lf` and xdist.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Parent and ref rules

<!-- sq:story:US2:body -->
## Scope

Breach tests in `test_parent_rules.py` and `test_ref_rules.py` for every parent, hierarchy and ref rule of `CATALOG`, with their param and level cases. Gated breaches are arranged by writing the item file and running `sq repair`.

## Acceptance

- Each rule has a breach test asserting the whole JSON array and the exit code, with the in-test clean pre-state and a near-miss sibling where the rule has a boundary.
- Each param and level case the tables derive for these rules exists.
- The guard reports none of these rules as undeclared.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Sub-entity and prose rules

<!-- sq:story:US3:body -->
## Scope

Breach tests in `test_subentity_rules.py` and `test_prose_rules.py`: sub-entity rules (bodies, containers, markers, parent rules) and prose rules (titles, bodies, descriptions, status banners), with their param and level cases, including the title-length param separated from the default.

## Acceptance

- Each rule has a breach test with the in-test clean pre-state and near-miss sibling.
- Each param and level case derived for these rules exists, with a param value the default would judge differently.
- The guard reports none of these rules as undeclared.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Attribute and roster item rules

<!-- sq:story:US4:body -->
## Scope

Breach tests in `test_attribute_and_roster_item_rules.py` for the attribute rules and the per-item rules on roster types (roles, skills, operators), with their param and level cases.

## Acceptance

- Each rule has a breach test with the in-test clean pre-state; opt-in members are enabled by a minimal override through `select_validators`.
- Each param and level case derived for these rules exists.
- The guard reports none of these rules as undeclared.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Roster config rules

<!-- sq:story:US5:body -->
## Scope

Breach tests in `test_roster_config_rules.py` for the always-on squad-wide members: roster, display, language and view members.

## Acceptance

- Each member has a breach test asserting the whole array and exit code, with the in-test clean pre-state.
- Always-on members get no level case, as ADR-1201 rules.
- The guard reports none of these rules as undeclared.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Work policy rules

<!-- sq:story:US6:body -->
## Scope

Breach tests in `test_work_policy_rules.py` for the selectable squad-wide members and the opt-in per-item work policy, including the time-dependent member aged with the frozen clock, with their param and level cases. Required-param members have only their param case, which is their breach case.

## Acceptance

- Each member has a breach test with the in-test clean pre-state, enabled through `select_validators`.
- Each param case (including the multi-selection union) and each selectable level case exists.
- The guard reports none of these rules as undeclared.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Corpus integrity rules

<!-- sq:story:US7:body -->
## Scope

Breach tests in `test_corpus_integrity_rules.py` for the file-load, raw-text, duplicate-id and cross-source rules and the reconciliation members (index, frontmatter, backend, id and number uniqueness, view tag placement). Drift breaches are arranged by the file write alone, without a repair.

## Acceptance

- Each rule has a breach test asserting the whole array and exit code, with the in-test clean pre-state.
- Binding rules, which cannot be deselected, get no level case.
- The guard reports none of these rules as undeclared.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — Config load rules

<!-- sq:story:US8:body -->
## Scope

Breach tests in `test_config_load_rules.py` for the override and config-load rules, including one malformed override each for the workflow, playbook and override load rules.

## Acceptance

- Each rule has a breach test with the in-test clean pre-state.
- The guard is green on the full tree, with no missing or stale declaration.
- The full local run stays in the order of 25 s.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T08:39:45Z] `tech-lead` Olivia Lead:
  - Rule-to-task assignment: 69 rules (CATALOG 30, SQUAD_GLOBAL_CATALOG 17, BINDING_RULES 22), each in exactly one task; TASK-1203 (US1) owns the harness, guard and baseline and no rule.
    
    | Task | Rule | Table |
    |---|---|---|
    | TASK-1204 (US2) | `parent_in` | CATALOG |
    | TASK-1204 (US2) | `no_parent` | CATALOG |
    | TASK-1204 (US2) | `parent_present` | CATALOG |
    | TASK-1204 (US2) | `parent_acyclic` | CATALOG |
    | TASK-1204 (US2) | `dangling_ref` | CATALOG |
    | TASK-1204 (US2) | `ref_kind_valid` | CATALOG |
    | TASK-1204 (US2) | `supersedes_incoming` | CATALOG |
    | TASK-1204 (US2) | `ref_rule_target_present` | CATALOG |
    | TASK-1204 (US2) | `ref_rule_target_typed` | CATALOG |
    | TASK-1205 (US3) | `subtask_story_mapping` | CATALOG |
    | TASK-1205 (US3) | `subentity_status_valid` | CATALOG |
    | TASK-1205 (US3) | `subentity_container_marker` | CATALOG |
    | TASK-1205 (US3) | `subentity_body_written` | CATALOG |
    | TASK-1205 (US3) | `subentity_title_max` | CATALOG |
    | TASK-1205 (US3) | `subentity_deferral_resolved` | CATALOG |
    | TASK-1205 (US3) | `subentities_settled_with_parent` | CATALOG |
    | TASK-1205 (US3) | `no_status_banner` | CATALOG |
    | TASK-1205 (US3) | `item_title_max` | CATALOG |
    | TASK-1205 (US3) | `body_written` | CATALOG |
    | TASK-1205 (US3) | `description_present` | CATALOG |
    | TASK-1205 (US3) | `external_id_not_in_title` | CATALOG |
    | TASK-1206 (US4) | `item_status_valid` | CATALOG |
    | TASK-1206 (US4) | `agent_registered` | CATALOG |
    | TASK-1206 (US4) | `attribute_valid` | CATALOG |
    | TASK-1206 (US4) | `frontmatter_key_undeclared` | CATALOG |
    | TASK-1206 (US4) | `pronouns_valid` | CATALOG |
    | TASK-1206 (US4) | `item_skill_shadowed` | CATALOG |
    | TASK-1207 (US5) | `roster_config_integrity` | SQUAD_GLOBAL_CATALOG |
    | TASK-1207 (US5) | `default_designation_duplicated` | SQUAD_GLOBAL_CATALOG |
    | TASK-1207 (US5) | `roster_slug_valid` | SQUAD_GLOBAL_CATALOG |
    | TASK-1207 (US5) | `role_base_resolves` | SQUAD_GLOBAL_CATALOG |
    | TASK-1207 (US5) | `role_definition_shadowed` | SQUAD_GLOBAL_CATALOG |
    | TASK-1207 (US5) | `playbook_guide_role_live` | SQUAD_GLOBAL_CATALOG |
    | TASK-1207 (US5) | `display_config_valid` | SQUAD_GLOBAL_CATALOG |
    | TASK-1207 (US5) | `working_language_valid` | SQUAD_GLOBAL_CATALOG |
    | TASK-1207 (US5) | `view_transform_resolves` | SQUAD_GLOBAL_CATALOG |
    | TASK-1208 (US6) | `type_has_live_author` | SQUAD_GLOBAL_CATALOG |
    | TASK-1208 (US6) | `children_settled_with_parent` | SQUAD_GLOBAL_CATALOG |
    | TASK-1208 (US6) | `dependency_acyclic` | SQUAD_GLOBAL_CATALOG |
    | TASK-1208 (US6) | `wip_limit` | SQUAD_GLOBAL_CATALOG |
    | TASK-1208 (US6) | `unassigned_active` | SQUAD_GLOBAL_CATALOG |
    | TASK-1208 (US6) | `stale_active` | SQUAD_GLOBAL_CATALOG |
    | TASK-1208 (US6) | `assignee_present` | CATALOG |
    | TASK-1208 (US6) | `blocked_has_blocker` | CATALOG |
    | TASK-1208 (US6) | `settled_requires_discussion` | CATALOG |
    | TASK-1209 (US7) | `index_reconciled` | SQUAD_GLOBAL_CATALOG |
    | TASK-1209 (US7) | `backend_reconciled` | SQUAD_GLOBAL_CATALOG |
    | TASK-1209 (US7) | `markers_balanced` | BINDING_RULES |
    | TASK-1209 (US7) | `view_target_resolves` | BINDING_RULES |
    | TASK-1209 (US7) | `view_tag_in_region` | BINDING_RULES |
    | TASK-1209 (US7) | `seeded_view_resolves` | BINDING_RULES |
    | TASK-1209 (US7) | `body_regions_present` | BINDING_RULES |
    | TASK-1209 (US7) | `block_in_container` | BINDING_RULES |
    | TASK-1209 (US7) | `file_readable` | BINDING_RULES |
    | TASK-1209 (US7) | `frontmatter_parses` | BINDING_RULES |
    | TASK-1209 (US7) | `id_present` | BINDING_RULES |
    | TASK-1209 (US7) | `id_well_formed` | BINDING_RULES |
    | TASK-1209 (US7) | `fields_valid` | BINDING_RULES |
    | TASK-1209 (US7) | `timestamps_present` | BINDING_RULES |
    | TASK-1209 (US7) | `skill_type_declared` | BINDING_RULES |
    | TASK-1209 (US7) | `ids_unique` | BINDING_RULES |
    | TASK-1209 (US7) | `numbers_unique` | BINDING_RULES |
    | TASK-1209 (US7) | `frontmatter_matches_index` | BINDING_RULES |
    | TASK-1210 (US8) | `override_stamped` | BINDING_RULES |
    | TASK-1210 (US8) | `override_current` | BINDING_RULES |
    | TASK-1210 (US8) | `override_loads` | BINDING_RULES |
    | TASK-1210 (US8) | `workflow_loads` | BINDING_RULES |
    | TASK-1210 (US8) | `playbook_loads` | BINDING_RULES |
    | TASK-1210 (US8) | `corpus_scans` | BINDING_RULES |
    
    Per task: US2 9, US3 12, US4 6, US5 9, US6 9, US7 18, US8 6. Derived extra cases: 7 param (US2 1, US3 3, US6 3; the 5 required-param members fold into their breach test) and 34 level (US2 8, US3 11, US4 6, US6 9; `parent_acyclic` and `subentity_container_marker` have none, always-on and binding rules none).
    Judgment calls: `ref_rule_target_typed` sits with the ref rules (US2) though it is a work policy member; `item_title_max`, `body_written`, `description_present` and `external_id_not_in_title` sit with the prose rules (US3); `item_status_valid` and `agent_registered` with the field rules (US4); `index_reconciled` and `backend_reconciled` with corpus integrity (US7); `skill_type_declared` (orphaned skills) in US7; `corpus_scans` (config load) in US8.
- [2026-10-28T10:41:21Z] `manager` Catherine Manager:
  - CI on release/0.17 head e7a6e366, run 40672997897, all green: Ubuntu job 1m18s (pytest 63s), macOS 2m23s (118s), Windows 7m17s (343s). Previous head bc959422, run 40671806921: Ubuntu 2m22s, macOS 2m20s, Windows 8m25s. Targets held (each job under 10 min, Windows at most 15).
  - Local: 1536 tests in ~30 s (-n 6). Branch coverage of src/squads 72% -> 76%; _validators.py 50% -> 89%, _check.py 50% -> 79%.
  - Closed under op-pierre's delegation of the full loop: tasks 1203-1210, 1212, 1214 Done; REV-1211 and REV-1213 Approved; 69 rules, 7 param and 34 level cases declared and guarded.
<!-- sq:discussion:end -->
