---
id: REV-246
sequence_id: 246
type: review
title: 'Engine core review: workflow override merge + singleton rebind + validate
  (TASK-239/240/241)'
status: Approved
author: reviewer
refs:
- FEAT-209:addresses
- TASK-239:addresses
- TASK-240:addresses
- TASK-241:addresses
subentities:
- local_id: F1
  title: AC#5 not enforced at any runtime boundary in this core
  status: Fixed
  severity: medium
- local_id: F2
  title: Override source is .overrides/workflow.toml only; FEAT AC#1 wording says
    .squads.toml
  status: Fixed
  severity: low
- local_id: F3
  title: open_service re-reads + re-validates the bundled TOML on every call, even
    with no override
  status: Fixed
  severity: low
- local_id: F4
  title: 'Test gaps: claimed no-leak isolation, sub-entity cross-check branch, and
    e2e sq list are not asserted'
  status: Fixed
  severity: low
- local_id: F5
  title: Two minor robustness/clarity nits in the loader
  status: Fixed
  severity: info
created_at: '2026-06-30T08:23:56Z'
updated_at: '2026-06-30T11:44:25Z'
---
<!-- sq:body -->
Independent engine-core review of FEAT-209 (TASK-239 merge loader, TASK-240 singleton rebind + open_service threading, TASK-241 validate() parent-cycle + index cross-check). Reviewer: Paul Reviewer; I did not write this code.

Verdict: APPROVE WITH NITS. The core mechanism (squad-dir-aware additive-only merge + process-global singleton rebind) is correct, fail-closed, and well-guarded by tests. No blocking defects. All findings are low/info — most are scope/traceability notes about work that legitimately lands in the not-yet-reviewed TASK-242/243.

Gates re-run by me: pyright 0 errors/0 warnings; ruff check clean; ruff format --check clean (138 files); pytest tests/test_workflow_override.py tests/test_workflow_spec.py = 39 passed (AC#7 golden green).

Behaviour I verified hands-on: (1) additive merge of an incident type + custom lifecycle/statuses; (2) redefining a built-in type/status/lifecycle each raise SquadsError; (3) typo key raises via extra=forbid; (4) reusing a built-in lifecycle from a custom type is allowed; (5) prefix collision caught by merged-spec uniqueness; (6) in-place dict mutation propagates to captured dict refs; (7) module TERMINAL + is_open() are live after use_spec(); a bound 'from _workflow import TERMINAL' is stale (documented, and no src caller does it); (8) reset_spec() restores bundled; (9) parent-cycle DFS: no false positive on diamonds, finds self-loops, both disjoint cycles, and 3-cycles reached via external entry edges.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 246 add-finding "…" --severity high`; track with `sq review 246 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | AC#5 not enforced at any runtime boundary in this core |
| F2 | 🟢 low | Fixed |  | Override source is .overrides/workflow.toml only; FEAT AC#1 wording says .squads.toml |
| F3 | 🟢 low | Fixed |  | open_service re-reads + re-validates the bundled TOML on every call, even with no override |
| F4 | 🟢 low | Fixed |  | Test gaps: claimed no-leak isolation, sub-entity cross-check branch, and e2e sq list are not asserted |
| F5 | 🔵 info | Fixed |  | Two minor robustness/clarity nits in the loader |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — AC#5 not enforced at any runtime boundary in this core

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
validate_against_index() (src/squads/_workflow/_loader.py:338) is the AC#5 guarantee (TASK-241: removing a status/type still used by live items must fail closed listing offenders). But it is NOT called anywhere in the runtime path — grep shows it is referenced only by tests. open_service() (src/squads/_services/_service.py:165) loads+validates the merged spec and calls use_spec(), but never calls validate_against_index(); sq check (_cli/_main.py:986) does not either.

Impact: as of TASK-239/240/241 alone, an override that OMITS a status/type still in use on disk does NOT fail closed at open_service. A user could install such an override and run commands. AC#5 is therefore unmet by this core.

Why it is only medium, not high: TASK-241's own body says 'Wire it where the merged spec meets the index: open_service (TASK-240) and/or sq check (TASK-243)'. Those wiring tasks (242 lint / 243 check) are still untracked/unimplemented, so the gap is by-design-deferred — but it must actually land in 243, and the function is currently dead code. Confirm 243 wires validate_against_index into open_service AND/OR sq check, and that the feature is not marked done until AC#5 has a live path.

Suggested fix: in TASK-243 (or a follow-up on 240), after use_spec(merged_spec) in open_service, open the index and call validate_against_index(merged_spec, db); if non-empty, raise SquadsError joining the offenders + the 'run sq workflow lint' pointer. Mind the import cycle (db typed Any in the loader is already set up for this).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-30T11:43:58Z] Catherine Manager:
  - Fixed: validate_against_index_fail_closed is now wired into open_service (TASK-243) — AC#5 fails closed at runtime listing offender IDs; verified live by QA on FEAT-209 and again on FEAT-250.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Override source is .overrides/workflow.toml only; FEAT AC#1 wording says .squads.toml

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
load_workflow_spec() reads ONLY <squad_dir>/.overrides/workflow.toml (_loader.py:29 WORKFLOW_OVERRIDE_FILENAME; the [workflow.*] block in .squads.toml is not read — SquadsConfig in _models/_config.py has no workflow field and the loader never opens .squads.toml).

FEAT-209 AC#1 and US1 acceptance literally say a project admin adds a '[workflow.types.incident]' block 'in .squads.toml'. The implementation diverges to a single canonical file. This divergence is AUTHORIZED — TASK-239's body explicitly recommended '.overrides/workflow.toml is primary' and treating dual sources as error-prone — so this is a doc/PO-traceability mismatch, not a code defect.

Suggested fix: reconcile the wording. Either (a) @product-owner edits AC#1/US1 to name .overrides/workflow.toml, or (b) TASK-245 (sq docs workflow) and the scaffold (TASK-244) clearly state the canonical path so admins are not misled by the original AC text. No code change needed; just don't let AC#1 read as a missed acceptance at sign-off.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-06-30T11:44:21Z] Catherine Manager:
  - Fixed: override location reconciled to .overrides/workflow.toml across AC#1/US1/scope (product-owner) and docs (TASK-245).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — open_service re-reads + re-validates the bundled TOML on every call, even with no override

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
load_workflow_spec() (_loader.py:50) calls _load_bundled_spec() unconditionally at the top — re-reading default_workflow.toml from importlib.resources, re-parsing, and re-running the full WorkflowSpec model validation — on EVERY open_service(), including the common no-override case. Then use_spec() rebuilds all derived constants (3 dicts + frozenset) each call. The already-cached _BUNDLED_SPEC in __init__.py is bypassed.

Impact: a small fixed per-command cost (one TOML parse + one full spec validate). Correctness is unaffected. Worth noting because every sq invocation now pays it where before it was import-time-once.

Suggested fix (optional): when no override file exists, return the cached singleton instead of reparsing — e.g. have open_service short-circuit to reset_spec() (which uses the cached _BUNDLED_SPEC) when <squad_dir>/.overrides/workflow.toml is absent, and only call load_workflow_spec(squad_dir) when it exists. Keep fail-closed semantics intact.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-06-30T11:44:22Z] Catherine Manager:
  - Fixed: open_service uses the bundled_spec() fast-path when no override is present — no TOML re-parse (TASK-243).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Test gaps: claimed no-leak isolation, sub-entity cross-check branch, and e2e sq list are not asserted

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
tests/test_workflow_override.py docstring line 12 claims to test 'use_spec rebind does not leak between tests' but there is no two-test sequence that installs an override in one test and asserts a later test sees the bundled spec. The autouse _reset_workflow_spec fixture is exercised implicitly only. (I verified reset works manually, so this is a coverage, not correctness, gap.)

validate_against_index()'s sub-entity branch (the 'for sub in item.subentities if sub.status not in known_statuses' loop, _loader.py:~368) is never exercised — both index tests cover item type/status only, and both use duck-typed _MockSpec objects rather than the real wired path (because nothing wires it yet — see F1).

test_open_service_picks_up_override asserts _active_spec[0].items contains 'incident' but does not run 'sq list -t incident' end-to-end, which is TASK-240's stated acceptance. The proxy is reasonable but the full e2e (create/list an incident item) is untested.

Suggested fix: add (a) a two-test leak guard or an explicit assert that after a prior override-using test the bundled spec is active; (b) a sub-entity-status case for validate_against_index; (c) a CLI smoke test that creates+lists a custom-type item through the override once F1's wiring lands.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-06-30T11:44:23Z] Catherine Manager:
  - Fixed: QA added the isolation, sub-entity cross-check, and override-merge assertions (FEAT-209 + FEAT-250 QA passes).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Two minor robustness/clarity nits in the loader

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🔵 Info
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
(a) _loader.py:60 wraps tomllib.TOMLDecodeError but not OSError — a workflow.toml that exists but is unreadable (permissions) would raise a raw OSError rather than a SquadsError. is_file() guards the missing-file case, so this is a narrow edge; consider widening the except or letting it surface as a non-SquadsError (it currently would not get the 'sq workflow lint' pointer either, since open_service only catches SquadsError).

(b) _parse_lifecycle_str (_loader.py:~227) hand-extracts known_keys={'initial','transitions'} and re-injects extras to trigger extra=forbid. This mirrors the bundled _parse_lifecycle exactly, which is fine, but the duplication means a future field added to Lifecycle must be updated in two places. Low risk; a shared helper would remove the drift surface. Not blocking.

Neither affects correctness or the gates; recording for the dev's awareness.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-06-30T11:44:24Z] Catherine Manager:
  - Fixed: OSError on the override read surfaces as SquadsError with the lint pointer; loader nits addressed.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
