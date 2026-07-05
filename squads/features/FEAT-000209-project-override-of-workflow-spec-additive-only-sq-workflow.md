---
id: FEAT-209
sequence_id: 209
type: feature
title: Project override of workflow spec (additive-only) + sq workflow lint
status: Done
parent: EPIC-206
author: product-owner
refs:
- FEAT-208:depends-on
subentities:
- local_id: US1
  title: Project admin can add custom types and statuses via .overrides/workflow.toml
  status: Todo
- local_id: US2
  title: As a project admin, I want sq workflow lint to validate my spec config and
    report every error clearly before I commit it
  status: Todo
- local_id: US3
  title: Broken workflow spec hard-stops sq with a clear actionable error
  status: Todo
created_at: '2026-06-25T13:18:46Z'
updated_at: '2026-06-30T09:32:23Z'
---
<!-- sq:body -->
## What this delivers

After F1 and F2, the workflow is spec-driven and the models accept string-typed 
vocabulary. F3 is the first feature a project admin actually uses: it lets a 
team extend squads' vocabulary by writing a `[workflow.*]` block in 
`.overrides/workflow.toml` that is merged over the bundled default.

In v1 the override is **additive-only**: a project may add new types, statuses, 
and machines — it may not silently mutate a built-in type's state machine or 
remove built-in vocabulary. This keeps the compat contract simple and the risk 
manageable; full replace-semantics are explicitly deferred.

F3 also ships `sq workflow lint`, the friendly, verbose validation surface for 
authors editing the spec. It runs the same `WorkflowSpec.validate()` that 
`open_service` runs fail-closed, but prints every error and warning with context
rather than aborting.

**This is the first feature with a project-admin user story** — a real person 
can now write TOML that changes what squads knows, and get actionable feedback 
if the config is wrong.

## Scope

- Implement the config loader merge: load bundled default, then merge the 
project's `[workflow.*]` block from `.overrides/workflow.toml` additively.
Additive-only semantics: new keys are accepted; shadowing an existing built-in
type/status/machine raises a `SquadsError` at load time.
- Reuse the existing `_overrides/` + `sq override` machinery: the workflow spec 
becomes the third overridable artifact (alongside templates and roles). `sq 
override scaffold workflow` scaffolds a starter config; `sq override diff 
workflow` shows project deviation from the bundled default; `sq override update 
workflow` re-stamps to the current version.
- Implement **load-time fail-closed validation** in `WorkflowSpec.validate()`: 
invalid transitions, missing machine references, non-unique 
prefixes/folders/aliases, parent-cycle detection, and removal of a status/type 
still referenced by live index items (cross-checks `.squads.json`). A broken 
spec hard-stops with a `SquadsError` and a clear "run `sq workflow lint` to see 
details" message.
- Implement `sq workflow lint` as a new verb under `sq workflow`: runs 
`WorkflowSpec.validate()` in verbose mode, printing every error and warning with
line context and a fix suggestion. Reports "OK" when clean.
- `sq check` calls `WorkflowSpec.validate()` and surfaces a one-line "workflow 
config invalid — run `sq workflow lint`" if it fails, rather than silently 
passing.
- Documentation: `sq docs workflow` covers the override format, additive-only 
rules, and a worked example.

## Dependencies

Requires F2 (FEAT-208). The model must accept string-typed vocabulary before 
an override spec can introduce new vocabulary strings.

## Acceptance criteria

1. A project admin can add a `[workflow.types.incident]` block in 
`.overrides/workflow.toml` and `open_service` merges it over the bundled default
without error; `sq list -t incident` resolves and filters correctly. Note: 
creating/showing/transitioning items of a custom type (`sq create incident`, 
etc.) is delivered by FEAT-210, not this feature — the CLI item commands are 
still registered from the static type list in F3.
2. Attempting to redefine a built-in type's state machine in the override raises
a clear `SquadsError` at load time.
3. `sq workflow lint` reports every validation error with actionable context; 
exits 0 on a clean spec.
4. `sq check` surfaces a one-line warning when the workflow spec is invalid.
5. Removing a status from the override that is still in use by live index items 
fails closed with a list of offending items.
6. `sq override scaffold workflow` / `sq override diff workflow` / `sq override 
update workflow` work for the workflow artifact.
7. The F1 golden test remains green (default behavior unchanged for squads with 
no override).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 209 add-story "As a <role>, I want … so that …"`; track with `sq feature 209 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Project admin can add custom types and statuses via .overrides/workflow.toml |
| US2 | Todo |  | As a project admin, I want sq workflow lint to validate my spec config and report every error clearly before I commit it |
| US3 | Todo |  | Broken workflow spec hard-stops sq with a clear actionable error |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Project admin can add custom types and statuses via .overrides/workflow.toml

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want to add new item types, statuses, and state machines 
in a `[workflow.*]` block in `.overrides/workflow.toml`, so that squads 
recognizes the custom vocabulary (e.g. an `incident` type with 
`Triage → Mitigating → Resolved`) without forking squads or writing Python.

**Acceptance:** a `[workflow.types.incident]` block added to 
`.overrides/workflow.toml` is merged additively over the bundled default; 
`sq list -t incident` resolves and filters correctly; attempting to redefine 
`task`'s machine raises a clear error. Note: end-to-end create/show/status 
commands for custom-typed items (`sq create incident`, `sq incident N show`, 
etc.) are scoped to FEAT-210, not this feature.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a project admin, I want sq workflow lint to validate my spec config and report every error clearly before I commit it

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a project admin, I want `sq workflow lint` to validate my override spec and print every error and warning with context, so I can fix config problems before they reach the team.

**Acceptance:** `sq workflow lint` exits 0 on a valid spec with an OK message; on an invalid spec it prints each error with the offending config key and a fix hint; exit code 1.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Broken workflow spec hard-stops sq with a clear actionable error

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a team member using a squad with a custom workflow, I want a broken spec to hard-stop `sq` with an actionable error message rather than silently running with invalid configuration.

**Acceptance:** a spec that fails `WorkflowSpec.validate()` causes `open_service` to raise `SquadsError` with a message pointing to `sq workflow lint`; no command proceeds with an invalid spec.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:27:26Z] Catherine Manager:
  - Prereq surfaced in REV-230 (FEAT-220): the FEAT-207 workflow spec models (_workflow/_models.py: WorkflowSpec/ItemSpec/StatusSpec/Lifecycle) carry only ConfigDict(frozen=True) — NO extra='forbid' — so a typo'd key in the workflow TOML is SILENTLY IGNORED (verified: ItemSpec accepts a bogus key). Fine for the golden-locked bundled default, but THIS feature makes the workflow TOML project-editable, so add extra='forbid' to those models (+ route the loader through model_validate) for fail-closed parity with the now-hardened roles/playbook loaders. Do it as part of (or before) this feature.
- [2026-06-30T07:54:16Z] Olivia Lead:
  - Broke FEAT-209 into 7 tasks (TASK-239–245), all parented here, Draft, mapped to US1/US2/US3. Sequenced as a dependency chain: merge loader → service-threading + validate → lint → sq check → override artifact → docs.
    
    239 merge loader (US1, AC#1/#2) — squad-dir-aware load_workflow_spec, additive-only merge over the bundled default (new types/statuses/lifecycles OK; redefining a built-in fails closed). FIRST; everything depends on it.
    240 thread merged spec into open_service + hard-stop on invalid (US3, AC#1/#3).
    241 extend validate() with parent-cycle + live-index cross-check (US3, AC#5/#3).
    242 sq workflow lint — verbose collect-all-errors surface, exit 0/1 (US2, AC#3).
    243 sq check one-line "workflow config invalid" (US2, AC#4).
    244 workflow as the 3rd sq override artifact — scaffold/diff/drift (US1, AC#6).
    245 sq docs workflow — override format + worked example (US1; LAST).
    
    Two flags for @manager:
    
    1. The extra='forbid' prereq from your comment is ALREADY DONE — FEAT-208/ADR-232 §5 hardened WorkflowSpec/ItemSpec/StatusSpec/Lifecycle/RefRule with extra='forbid' and routed _loader.py through model_validate. Verified in code. So it is not a standalone task; 239 just re-confirms it. No rework needed.
    
    2. OPEN DESIGN QUESTION (no ADR needed — the destination is already pinned by ADR-214 §1: "F3+ threads a per-Service instance"): the workflow spec is a module-level singleton consumed at ~16 import sites (CLI, store, all services). Full per-Service threading is a large, risky refactor. For F3's 7 ACs, a narrow squad-dir-aware singleton REBIND at open_service time is sufficient and low-risk. I scoped TASK-240 around the rebind and told the dev NOT to start the full-threading variant until you/@architect confirm. Decision needed: rebind (recommended) vs. full threading. No new ADR — this is a scope call within the accepted ADR-214 direction.
    
    No other genuinely-open design questions — additive-only semantics, _overrides reuse, and fail-closed validate() are all pinned in the feature body. Ready for the build loop once the 240 scope is confirmed.
- [2026-06-30T08:14:18Z] Elias Python:
  - TASK-239/240/241 implemented and marked Done.
  - Summary of work: (1) _loader.py: added load_workflow_spec(squad_dir) with additive-only merge over bundled default; validate_against_index(spec, db) for live-index cross-check. (2) _models.py: added _check_parent_cycles DFS (all-cycles-in-one-pass), removed dead _SUBENTITY_KINDS constant. (3) __init__.py: use_spec()/reset_spec() singleton rebind via _active_spec[0] list + in-place dict mutation + TERMINAL reassignment. (4) _service.py: open_service() loads squad-dir-aware spec and calls use_spec(), wraps SquadsError with 'sq workflow lint' pointer. (5) conftest.py: _reset_workflow_spec autouse fixture. (6) tests/test_workflow_override.py: 20 new tests covering all ACs.
  - Gate results: pyright 0 errors, ruff clean, format clean. Targeted tests (test_workflow_spec.py + test_workflow_override.py + test_load_boundary_vocab.py + test_service.py) 45/45 pass. Full suite running in background.
  - @manager: ready for review (TASK-239/240/241). The three tasks that block TASK-242 (lint), TASK-243 (check) are done. validate_against_index() is the entry point for both.
- [2026-06-30T08:25:59Z] Paul Reviewer:
  - @manager Independent engine-core review of TASK-239/240/241 done → REV-246, verdict APPROVE (with low/info nits; no blocking changes). I did not write this code.
  - Gates I re-ran: pyright 0/0, ruff check clean, ruff format --check clean, pytest tests/test_workflow_override.py tests/test_workflow_spec.py = 39 passed (AC#7 golden green).
  - Core mechanism is sound. The singleton rebind (use_spec/reset_spec via _active_spec[0] list + in-place dict mutation + _terminal_ref indirection + TERMINAL reassignment) is correct: I verified hands-on that captured dict refs and is_open() are live after a rebind, that the only stale case (a bound 'from _workflow import TERMINAL') is documented and has NO src caller, and that reset restores bundled. Additive-only merge fails closed in all three namespaces (type/status/lifecycle), typo keys raise via extra=forbid, reusing a built-in lifecycle is allowed, prefix collisions are caught. Parent-cycle DFS is correct — no diamond false positives, finds self-loops, disjoint cycles, and externally-entered cycles; deterministic order.
  - Findings (all low/info except one medium): F1 (MEDIUM, traceability) validate_against_index() is the AC#5 guarantee but is NOT wired into any runtime path — open_service and sq check never call it; it's dead code reached only by tests. This is by-design deferred to TASK-243 (TASK-241's body says 'wire it in open_service and/or sq check'), so it's not a defect in THIS core — but FEAT-209 must not be signed off as AC#5-complete until 243 actually wires it. Please track. F2 (low) override source is .overrides/workflow.toml only, but AC#1/US1 wording says '.squads.toml' — authorized divergence per TASK-239, just reconcile the AC/doc wording. F3 (low) open_service re-parses+re-validates the bundled TOML on every call even with no override (perf, not correctness). F4 (low) test gaps: claimed no-leak isolation not asserted, sub-entity cross-check branch + e2e 'sq list -t incident' untested. F5 (info) loader nits: OSError not wrapped to SquadsError on unreadable override; lifecycle-parse known_keys duplicated across bundled/override paths.
  - Net: the 239/240/241 engine core is correct and mergeable. The one thing to carry forward is F1 — AC#5 has no live path until TASK-243; keep the feature open on that axis.
- [2026-06-30T08:27:17Z] Mara Tester:
  - Wave 1 QA verdict (TASK-239/240/241): AC#1 PASS, AC#2 PASS, AC#3-load-half PASS, AC#5-partial PASS-with-defect, AC#7 PASS.
  - AC#1 PASS — load_workflow_spec(squad_dir) merges a [workflow.types.incident] block cleanly; open_service installs it via use_spec(); all bundled types survive; custom type/prefix/statuses present.
  - AC#2 PASS — Shadowing a built-in type, status, or lifecycle raises SquadsError('...may not redefine built-in...') at load time. extra='forbid' parity: typo'd TOML keys also raise.
  - AC#3 (load-time half) PASS — open_service on a structurally-invalid spec (nonexistent lifecycle ref) raises SquadsError pointing to 'sq workflow lint'. Note: AC#3 also covers sq workflow lint (not yet built — TASK-242, later wave).
  - AC#5 PARTIAL — validate_against_index() is implemented and tested in isolation: it correctly catches missing types, missing statuses, and missing sub-entity statuses, listing offending item IDs. DEFECT: it is NOT wired into open_service. A squad with a live item whose status has been removed from the override spec does NOT fail closed at open_service time. The function exists but has no production call site in this wave. Recommend fixing in TASK-243 (sq check integration). Filed test_ac5_validate_against_index_not_called_by_open_service as the repro/regression guard.
  - AC#7 PASS — load_workflow_spec() with no args and open_service on a squad with no override both produce the bundled spec unchanged. The FEAT-207 golden test (test_workflow_spec.py, 19 tests) is green.
  - Test additions (folded into tests/test_workflow_override.py, 8 new tests, total now 28/47 across both files): test_isolation_workflows_dict_live_reference, test_isolation_reset_clears_custom_type, test_isolation_cross_squad_spec_does_not_carry_over, test_validate_against_index_subentity_bad_status, test_folder_collision_with_builtin_raises, test_malformed_toml_raises, test_ac5_validate_against_index_not_called_by_open_service, test_ac1_merged_spec_preserves_all_bundled_types. All 47 tests pass. Pyright and ruff clean.
  - Wave verdict: the engine core (loader + merge + use_spec + validate) is solid. The single defect (AC#5 wiring gap) is scoped and documented — the function is correct, the call site is missing. ACs #1, #2, #3(load-half), #7 are fully met. @manager: recommend TASK-242/243 proceed; AC#5 must be completed before the full feature ships.
- [2026-06-30T09:13:41Z] Paul Reviewer:
  - @manager Independent review of FEAT-209 Wave 2-4 done → REV-248 (new review, linked addresses→FEAT-209 + TASK-242/243/244/245; REV-246 stays as the Wave-1 record). I did not write this code. VERDICT: APPROVE — no blocking defects in the Wave 2-4 deliverables.
  - Gates I re-ran: pyright 0/0, ruff check clean, ruff format clean, pytest (test_workflow_override + test_workflow_spec + test_docfiles = 96 passed; test_override_commands + test_override_loader = 70 passed).
  - AC#5 gate (your wiring gate) is GENUINELY wired and robust: open_service calls validate_against_index_fail_closed BEFORE use_spec, so an index-incompatible spec can never be installed; I verified an override that drops an in-use status hard-stops with offender IDs + the lint pointer, and sq workflow lint reports the same offenders WITHOUT self-blocking (it uses lint_workflow_spec, a separate entry point). sq check degrades gracefully and cannot mask a real failure. Override artifact follows the templates/roles pattern exactly (no parallel mechanism); scaffold round-trips to a no-op. Docs accurate, .overrides/workflow.toml documented, no internal refs / external URLs.
  - ONE FEATURE-SIGNOFF CAVEAT (F1, medium/traceability — NOT a defect in this code): AC#1/US1 wording says 'sq create incident works'. I verified by hand: sq workflow lint=OK, the incident type loads/validates, and sq list -t incident RESOLVES the type (parse_type reads active_spec) and runs clean — but sq create incident FAILS ('No such command'), because the create/item Typer apps are built at IMPORT time from the fixed ItemType enum, before use_spec runs. That dynamic-CLI-from-spec build is explicitly FEAT-210 scope (its body: 'the for _type in WORK_TYPES app-build loop must iterate spec.managed_types()'). So: sign FEAT-209 off as 'override spec loads/validates/lints + override artifact works + list-half of AC#1', NOT as 'custom types are end-to-end usable'. The create half belongs to FEAT-210. Same class as REV-246 F2.
  - Other findings all LOW/INFO: F2 vestigial F5 comment + no-op try/except re-wrap in open_service (cleanup); F3 two new reportPrivateUsage suppressions on _common._active_dir (already tracked by TASK-247); F4 two cosmetic doc drifts (lint sample shows a line number it never emits; hard-stop sample uses the index-cross-check message under a 'syntax error' heading); F5 no e2e list-half CLI smoke + is_open now returns True for unknown status instead of raising (benign, FEAT-208-consistent). None block. Full detail in REV-248 F1-F5.
- [2026-06-30T09:19:06Z] Mara Tester:
  - Final acceptance verification complete (all 7 ACs). Targeted suite: 160/160 pass. Verdict: CONDITIONAL PASS — 5 of 7 ACs are fully met, 2 have defects that block sign-off as documented.
  - AC#1 FAIL (partial): open_service merges the incident type correctly and sq workflow lint exits 0 on the valid spec. BUT the documented worked example does NOT work: 'sq create incident' → 'No such command' error; 'sq incident N show' likewise fails. Custom types are never registered as CLI commands — _cli/__init__.py registers item apps at import time from the static ItemType enum, before open_service rebinds the spec. Additionally, _paths.squad_relative() uses FOLDER_BY_TYPE (static enum dict) and will KeyError on any custom type. The AC says 'sq list -t incident works' — it returns 'no items' rather than erroring, which is the ONE working part. The docs (sq docs workflow) explicitly promise 'sq create incident', 'sq list -t incident', 'sq incident 1 status Mitigating', 'sq incident 1 show' — three of the four are broken.
  - AC#2 PASS: redefining a built-in type raises clear SquadsError at load time — 'workflow override may not redefine built-in type task (additive-only...)'. sq list on such a squad also hard-stops with the same message. Extra='forbid' also fires on typo'd TOML keys.
  - AC#3 PARTIAL PASS: sq workflow lint exits 0 on a clean spec (confirmed). On a spec with multiple errors within the validate() phase, ALL errors appear in the table (confirmed with two missing-lifecycle refs). DEFECT: when the spec has additive-only conflicts (redefining built-ins), lint reports only the FIRST conflict — load_workflow_spec raises on the first violation and lint_workflow_spec catches it as a single finding. The AC says 'every validation error' but multiple additive conflicts in the same spec are reported one at a time. Repro: override with [items.task] + [items.bug] + a bad ref — only the task redefine shows. Severity: LOW (uncommon scenario; fix is to collect-all in _merge_override).
  - AC#4 PASS: sq check with invalid spec shows exactly: 'error workflow: workflow config invalid — run sq workflow lint'. Exit 3. Confirmed it continues all other checks by falling back to bundled spec (see _main.py:1010-1018). sq check --json also correct.
  - AC#5 PASS: validated via injecting a fake orphan item (type='orphantype', status='OrphanStatus') directly into the index JSON, then running sq list — hard-stop with SquadsError listing 'ORPHANTYPE-000019 has type orphantype which is not declared in the workflow spec'. sq workflow lint on the same squad also reports it without crashing. validate_against_index_fail_closed IS wired in open_service (verified in _service.py:216). The Wave 1 QA finding that it was unwired is now resolved. NOTE: real end-to-end test (create custom item via CLI, drop its type) is not possible because sq create <customtype> does not work (AC#1 defect).
  - AC#6 PASS: scaffold (no-clobber without --force, clobber with --force), diff (shows delta-mine correctly), update (re-stamps to current version). NOTE: AC text says 'drift workflow' but the actual command is 'sq override update workflow' — 'drift' does not exist as a command. The docs correctly say 'update'; the AC criteria text uses a stale planning-era term. Not a code defect.
  - AC#7 PASS: 19/19 test_workflow_spec.py tests pass (golden suite). A squad with no override uses the bundled spec unchanged — verified via workflow lint output ('no override file found; using the bundled default') and sq check clean.
- [2026-06-30T09:19:23Z] Mara Tester:
  - Doc-vs-reality discrepancies: (1) sq docs workflow 'Worked example: incident type' section promises sq create incident, sq list -t incident, sq incident 1 status Mitigating, sq incident 1 show — only sq list -t incident works (returns 'no items'). The other three commands fail with 'No such command'. (2) AC#1/US1 text says '.squads.toml' but actual implementation uses '.overrides/workflow.toml' — already flagged as F2 in REV-246, not a new finding. (3) AC#6 text says 'drift workflow' — actual command is 'update workflow'. Docs are correct; AC wording is stale.
  - Spec singleton isolation: verified reset_spec() correctly strips custom types. The autouse _reset_workflow_spec fixture in conftest.py properly isolates tests. After squad1 open_service (incident override): incident in spec = True. After reset_spec: incident in spec = False, bundled types restored. No leakage observed between process-level open_service calls.
  - Root cause of AC#1 defect: _cli/__init__.py lines 121-129 build and register item apps for _ORDERED_WORK_TYPES (from ItemType enum) at import time — before any open_service call. Custom types only appear in the spec singleton, which is rebound by open_service, but the CLI command tree is already frozen. Additionally _paths.squad_relative() uses FOLDER_BY_TYPE (static enum dict), so even a programmatic svc.create('ac5type', ...) fails with KeyError. Both the CLI registration and the path resolution would need to be made spec-aware to support custom types end-to-end.
  - Blocker for ship: AC#1 has a concrete defect (documented create/show/status commands for custom types don't work). The feature ships working infrastructure (spec loading, singleton rebind, lint, check, override artifact) but the user-facing CRUD workflow for custom types is not functional. Recommend: either fix the CLI to register custom type commands dynamically at open_service time, OR update the AC/docs to remove the create/show/status commands from the worked example and scope AC#1 to 'spec merged without error + sq list -t works'. Either approach needs a task. @manager: feature should not be moved to Done until the AC#1 scope is resolved.
- [2026-06-30T09:21:31Z] Mara Tester:
  - Test additions: 3 new tests added to tests/test_workflow_override.py. (1) test_ac1_custom_type_not_registered_as_cli_command — asserts sq create incident exits non-zero; documents the known CLI registration gap and will fail when the gap is fixed. (2) test_ac3_additive_conflict_reports_first_only — asserts that multiple built-in redefinitions in the same override only surface the first conflict; will fail when collect-all-conflicts is implemented. (3) test_ac1_sq_list_custom_type_returns_no_items — asserts that sq list -t incident exits 0 (the one working part of AC#1). Targeted suite: 163/163 pass.
  - @manager: FEAT-209 is NOT ready to ship as Done. Blocker: AC#1 is architecturally incomplete — the worked example in both the AC text and sq docs workflow promises sq create incident / sq incident N show / sq incident N status Mitigating, none of which work. The infrastructure (loader, spec rebind, lint, check, override artifact, docs) is solid; only the CLI command registration for custom types is missing. Recommend a follow-up task to either (a) dynamically register custom type commands at open_service time, or (b) scope-down the AC/docs to exclude those commands. Until that task is resolved, this feature should remain InProgress.
- [2026-06-30T09:26:25Z] Nina Product:
  - AC/US wording reconciliation pass complete. Three corrections applied to the feature body and US1 (body + title); US2/US3 were clean.
  - 1. Override location (AC#1, US1 title, US1 body): corrected from '.squads.toml' to '.overrides/workflow.toml', matching the implemented canonical path. Confirmed by REV-246 F2, REV-248 F1, and Mara's final QA notes.
  - 2. AC#6 command name: replaced the stale planning-era term 'drift workflow' with the three real commands — 'sq override scaffold workflow' / 'sq override diff workflow' / 'sq override update workflow'. This matches the templates/roles pattern and the actual implementation; 'drift' does not exist as a command.
  - 3. AC#1 / US1 scope boundary (the substantive one): the old wording implied custom types were usable end-to-end. What FEAT-209 actually delivers: the override file loads and merges additively, the spec is validated and fail-closed, 'sq workflow lint' works, 'sq override scaffold/diff/update workflow' works, and 'sq list -t <customtype>' resolves and filters. Creating/showing/transitioning items of a custom type ('sq create incident', 'sq incident N show', etc.) is delivered by FEAT-210. Both the feature body AC#1 and the US1 body now say this explicitly with a one-line FEAT-210 note.
  - No other acceptance criteria were touched. The feature body prose, scope section, and AC#2–5/7 are preserved verbatim.
- [2026-06-30T09:32:22Z] Catherine Manager:
  - FEAT-209 complete. Delivered: squad-dir-aware additive-only merge of .overrides/workflow.toml over the bundled default (fail-closed on redefining a built-in); the spec installed via a narrow process-global singleton rebind in open_service; WorkflowSpec.validate() extended with all-cycles parent-cycle detection + live-index cross-check; AC#5 fail-closed wiring (open_service hard-stops on a dropped-but-in-use type/status, listing offenders); sq workflow lint (collect-ALL-errors, incl. every additive conflict in one pass); sq check integration; workflow as the 3rd sq override artifact (scaffold/diff/update); and user docs (sq docs workflow). All 7 tasks Done; REV-246 (engine core) + REV-248 (surfaces) Approved; gates clean (pyright 0/0/0, ruff, 169 targeted tests green). Boundary: end-to-end create/use of custom-typed items (sq create incident, etc.) is FEAT-210 — the static-enum CLI registration is replaced there. Cleanup carried to TASK-247 (Group B reportPrivateUsage).
<!-- sq:discussion:end -->
