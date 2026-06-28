---
id: REV-000218
sequence_id: 218
type: review
title: 'FEAT-207 review: workflow externalized to bundled spec'
status: Approved
author: reviewer
refs:
- FEAT-000207
- TASK-000215
- TASK-000216
- TASK-000217
subentities:
- local_id: F1
  title: Loader does not enforce Status-enum completeness (ADR 5-6 partial)
  status: Open
  severity: low
created_at: '2026-06-25T14:52:56Z'
updated_at: '2026-06-25T15:17:07Z'
---
<!-- sq:body -->
## Scope

Independent review of FEAT-000207 / ADR-000214 F1: externalizing the hardcoded workflow into a bundled TOML WorkflowSpec, enums kept INTACT (no de-typing). New package src/squads/_workflow/ (_models.py, _loader.py, default_workflow.toml, __init__.py) replaces _workflow.py; one is->== fix in _services/_retype.py; new tests/test_workflow_spec.py. Reviewer did not write the code.

## Verdict: APPROVE-WITH-NITS

Behavior is byte-identical to the pre-change literals — verified independently (see below), not just trusted from the golden test. The one finding (F1, low) is a loader-contract gap that bites F3, not F1.

## Behavior-preservation (the core requirement) — VERIFIED

Reconstructed the original _workflow.py / _enums.py literals from git HEAD and diffed against the LOADED spec, exhaustively and including transition ORDERING (which the set-based shim cross-check does not assert, but test_golden_machines_initial_and_transitions DOES via ordered dict equality):
- All 6 named machines (work/adr/review/bug/guide/agent) + 3 sub-entity machines (subtask/story/finding): initial + transitions identical, order preserved.
- TERMINAL set: identical (11 statuses).
- ALLOWED_PARENTS: identical (task->feature, feature->epic; empty lists correctly omitted from the dict so parent_hint 'none' branch matches).
- prefix / folder / aliases: identical for all 10 types.
- STATUS_EMOJI badges: identical for all 23 statuses (9 carry badges).
- parent_hint: TASK special-case branch left verbatim (ADR §3), FEATURE/BUG outputs unchanged.

Existing tests UNCHANGED: confirmed no tracked test file is modified (git status); only test_workflow_spec.py is added. test_workflow / test_workflow_rules / test_bug_workflow / test_terminal_accepted_published / test_retype all pass green against the new package.

## The is->== retype fix — CORRECT and NECESSARY

_retype.py:95 _carry_or_reset_status. Previously EPIC/FEATURE/TASK shared the single _WORK object so 'is' held; the spec now builds a fresh Workflow per type, so 'is' is False even for value-equal machines, which would spuriously reset a carried status to the new type's initial on every work->work retype. Workflow is a frozen dataclass, so '==' compares (initial, transitions) by value — verified EPIC==FEATURE==TASK True, EPIC==BUG False, role==skill==operator True. Restores exact prior semantics. Hunted for OTHER identity comparisons on workflow/machine/spec objects across src/squads: this was the only one. No silent landmines remain.

## Loader & validation — SOUND, fail-closed

importlib.resources + tomllib; unknown ItemType/Status names raise SquadsError (verified); malformed TOML and unreadable bundled file both wrapped in SquadsError; pydantic model_validator runs §5 checks (initial declared, transition src/dst declared, terminal subset, reachability BFS, type cross-refs + prefix/folder/alias uniqueness, type-set == set(ItemType)) and raises SquadsError on any violation. The one gap: status-set completeness is not enforced (finding F1).

## Golden-lock test — GENUINE, non-circular

_MACHINE_SNAPSHOT / _SUBENTITY_SNAPSHOT are hand-transcribed literals independent of the spec — a real frozen snapshot, ordered-dict compared, so a wrong/missing transition fails the gate. prefix/folder/alias/parent/terminal/badge assertions compare against the _enums.py maps, which do NOT import from _workflow (verified) — so non-circular. Covers transitions/terminal/parents/prefixes/folders/aliases/sub-entity machines/badges + the WORKFLOWS/SUBENTITY_WORKFLOWS shim cross-check. Packaging: importlib-resources access test + a real 'uv build' wheel test asserting default_workflow.toml ships — both pass (not skipped).

## Invariants — CLEAN

No 'from __future__'. Import graph acyclic: _workflow imports only _models._enums + _errors + intra-package (no services/index/cli edge). SquadsError for all user/load errors. Module-level singleton _DEFAULT_SPEC loaded once at package import; the only import-time side-effect is reading bundled package data via importlib.resources (offline, no fs assumption) — safe. pyright strict + ruff check + ruff format all clean on the new code.

## Scope boundary — RESPECTED (F1 did not leak into F2/F3)

No model str de-typing (Item.type/status still enum-typed), no capability flags (is_meta/subentity_kind/ref_rules absent from TypeSpec), no project overrides, no custom vocabulary, no renderer change (sq workflow still renders the static cheatsheet — regression test green). parent_hint TASK branch left as-is.

## Known naming rename (noted, not a defect)

The 'machines' / 'subentity_machines' TOML keys + StateMachine usages + TypeSpec.machine field are slated to rename (operator dislikes 'machines'; -> lifecycle(s)), tracked on TASK-215. Mechanically contained to: (a) the TOML section keys, (b) the WorkflowSpec/TypeSpec field names + the parser keys in _loader._build_spec, (c) the _machine_for / machine_for / _MACHINE_BY_TYPE accessors in _models.py + test, (d) docstrings. No external consumer reads 'machines' directly — all access goes through machine_for()/the shims — so the blast radius is the _workflow package + its one test. A clean rename.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 218 add-finding "…" --severity high`; track with `sq review 218 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Loader does not enforce Status-enum completeness (ADR 5-6 partial) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Loader does not enforce Status-enum completeness (ADR 5-6 partial)

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
src/squads/_workflow/_models.py:222-233 (WorkflowSpec._validate, §5-6 enums-intact check).

The check enforces that the spec TYPE set equals set(ItemType), but does NOT enforce that every Status enum member is present in spec.statuses. ADR-000214 §5-6 states the spec 'may not omit or invent a name relative to the enums' — for statuses, only the 'invent' half is covered (coercion via Status(...) rejects unknown names); the 'omit' half is not. A spec can pass validation while declaring a strict subset of the Status enum.

Coupled risk: is_open() at _models.py:177 does 'self.statuses[status].terminal' — a bare subscript. A status enum member absent from spec.statuses would raise KeyError at runtime rather than fail-closed at load.

Impact for F1: NONE in practice. The bundled default declares all 23 statuses (verified set(spec.statuses)==set(Status)), and the golden test (test_golden_terminal_set / test_golden_status_badges) iterates 'for s in Status', so a missing status in the default would be caught. This is a loader-contract gap, not a live defect.

Why it still matters: F3 introduces project overrides that will run THIS validation against author-supplied specs. At that point an omitted status silently passes load and then KeyErrors deep in is_open. Cheap to close now: add a status-completeness assertion mirroring the type-set check (every Status member must appear in spec.statuses), and/or make is_open use .get with a fail-closed default. Recommend a one-line symmetric check now or a tracked F3 follow-up.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T14:54:13Z] Paul Reviewer:
  - VERDICT: APPROVE-WITH-NITS. F1 is the de-risking foundation of EPIC-000206 and it is solid: behavior is byte-identical to the pre-change literals (independently reconstructed from git HEAD and diffed exhaustively, transition ordering included — not merely trusting the golden test), existing tests pass unchanged, the is->== retype fix is correct/necessary and the only such identity comparison in the tree, loader is fail-closed with SquadsError, the golden-lock test is a genuine non-circular regression gate, imports are acyclic, and scope did not leak into F2/F3.
  - One LOW finding (F1): the §5-6 enums-intact check enforces type-set completeness but NOT Status-set completeness — a spec can omit Status enum members and pass load, then KeyError in is_open() (bare subscript). Zero impact in F1 (bundled default is complete, golden test iterates 'for s in Status'), but this validation runs against author specs in F3 — recommend closing now with a one-line symmetric check or tracking as an explicit F3 follow-up. Not a merge blocker.
  - Naming rename ('machines'->lifecycle, tracked on TASK-215) is mechanically contained to the _workflow package + its test; no external consumer reads the key directly. @tech-lead / @python-dev for the F1 nit disposition.
- [2026-06-25T15:15:50Z] Elias Python:
  - @manager REV-000218 nits implemented — vocabulary rename + symmetric status validator.
  - Changes:
  -   default_workflow.toml: [machines.*]+[subentity_machines.*] merged into [lifecycles.*]; [types.*] renamed to [items.*]; type field 'machine' renamed to 'lifecycle'.
  -   _models.py: StateMachine → Lifecycle; TypeSpec → ItemSpec; ItemSpec.machine → .lifecycle; WorkflowSpec.types → .items; WorkflowSpec.machines+.subentity_machines → .lifecycles: dict[str, Lifecycle]; added §5-6b symmetric status check (spec status set must equal set(Status)); _check_machine_statuses/_check_reachability/_check_type_refs renamed accordingly.
  -   _loader.py: updated to parse [lifecycles.*] and [items.*]; uses ItemSpec/Lifecycle; passes single lifecycles map to WorkflowSpec.
  -   __init__.py: imports ItemSpec/Lifecycle; backward-compat aliases StateMachine=Lifecycle, TypeSpec=ItemSpec added; SUBENTITY_WORKFLOWS built from _DEFAULT_SPEC.lifecycles via concrete _SUBENTITY_KINDS set; ALLOWED_PARENTS from _DEFAULT_SPEC.items.items(). All public API names (WORKFLOWS, SUBENTITY_WORKFLOWS, TERMINAL, ALLOWED_PARENTS, free functions, Workflow shim) unchanged.
  -   test_workflow_spec.py: field accesses updated (spec.items, spec.lifecycles, ts.lifecycle); _MACHINE_SNAPSHOT renamed _LIFECYCLE_SNAPSHOT; added test_golden_status_set; importlib test updated to check [lifecycles.work] + [items.task].
  - Behavior byte-identical: all existing tests pass UNCHANGED (not modified). Golden-lock (test_golden_lifecycles_initial_and_transitions + test_golden_subentity_lifecycles) and full 16-test suite all green.
  - Gates: pytest -q exit 0 (all tests pass, 1 skip); pyright 0 errors; ruff check clean; ruff format --check 128 files already formatted.
- [2026-06-25T15:17:06Z] Catherine Manager:
  - Nits addressed and verified. Rename: spec layer now [items.*] + a single merged [lifecycles.*] table (StateMachine→Lifecycle, ItemSpec, .lifecycle); sub-entity kinds are lifecycle entries by kind-name; public API (WORKFLOWS/TERMINAL/can_transition/…) and back-compat aliases unchanged so existing tests untouched. LOW fix: validator now requires set(statuses)==set(Status), fail-closed. Verified: 'machines'/'types' gone from the spec, behavior byte-identical (transitions/initials/terminal=11/parents/sub-entity kinds), golden-lock + full suite green, pyright/ruff clean. Approving.
<!-- sq:discussion:end -->
