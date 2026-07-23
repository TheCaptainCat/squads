---
id: REV-641
sequence_id: 641
type: review
title: 'FEAT-576 import engine: event model, validate pre-pass, apply + mutation-core
  refactor'
status: Approved
author: reviewer
subentities:
- local_id: F1
  title: add-sub with unknown kind crashes the validate pre-pass
  status: Verified
  severity: medium
created_at: '2026-07-23T14:42:09Z'
updated_at: '2026-07-23T14:50:56Z'
---
<!-- sq:body -->
Independent review of the FEAT-576 bulk-import engine (TASK-636 event model + validate pre-pass; TASK-638 apply + shared `_X_model`/`_X_core` mutation-core refactor), against ACCEPTED ADR-622. Scope: uncommitted working diff + new untracked files. Gate clean (pyright/ruff/format); targeted tests green (import + reflog + meta = 95; refactored mutation-path service/CLI = 110). Full suite run by manager.

Verdict basis: the four integrity-critical leads all hold — refactor behaviour-preservation, reflog snapshot-timing, dry-run shadow isolation, and apply atomicity/context-restore. One Medium robustness finding on the generic add-sub op's pre-pass (unknown kind stack-traces instead of collecting an issue).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 641 add-finding "…" --severity medium`; track with `sq review 641 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | add-sub with unknown kind crashes the validate pre-pass |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — add-sub with unknown kind crashes the validate pre-pass

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
A generic `add-sub` event naming an unknown sub-entity `kind` (with no `fields`) raises an uncaught `KeyError` during the validate pre-pass, aborting the whole import instead of being collected as an ImportIssue on that line.

Path: _sim_add_sub -> _add_block_model -> _resolve_add_status(kind) -> spec.subentity_initial(kind) -> _subentity_machine -> self.subentity_kinds[kind] => KeyError. _resolve_add_status runs BEFORE _require_parent/_check_type, so the SquadsError guard that would reject a bad kind never fires. KeyError is not in _COLLECTIBLE=(SquadsError, ValidationError), so _plan_import does not catch it.

Repro (dry-run): a single line {"op":"add-sub","target":"FEAT-1","kind":"not-a-real-kind","title":"x"} stack-traces out of import_events. Confirmed against the svc fixture.

Impact: breaks ADR-622's validate-first contract ('check every event ... writing nothing and collecting all errors before reporting') and gives a stack trace on a plausible authoring typo. No data-integrity impact — the crash is in the pre-pass, which writes nothing, and apply is never reached; invariants #2/#3 hold. Ergonomic fronts (add-story/subtask/finding) are safe (they hardcode valid kinds); only the generic add-sub with a bad kind + empty fields is affected. add-sub WITH non-empty fields already fails cleanly (SquadsError from _resolve_fields).

Fix options: validate kind against spec.subentity_kinds up front with a SquadsError (e.g. in _resolve_add_status / a shared guard), or reorder so _require_parent/_check_type runs before _resolve_add_status, or make _subentity_machine raise SquadsError on an unknown kind. Add a pre-pass test for an unknown add-sub kind.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T14:42:55Z] Paul Reviewer:
  - RECOMMENDED VERDICT: Approve-with-changes. The integrity-critical work is sound; land it once F1 is fixed (or accept F1 as an immediate fast-follow before the CLI task TASK-639 exposes `sq import` to users).
  - Gate: pyright 0/0, ruff check clean, ruff format clean (367 files). Targeted tests green: import+reflog+meta 95 passed; refactored mutation-path service/CLI 110 passed. Full suite = manager's green run.
  - Lead #1 (refactor behaviour-preservation): HOLDS. Each mutation splits cleanly into a pure `_X_model` (checks + allocation + in-memory mutation, no I/O) and `_X_core` (model + file write + one `_log`). Same checks, same order, same reflog delta for status/update/comment/ref/add_block/set_block_status/set_block_assignee/update_block/body/sub-body. One benign, positive reorder in create: `write_new` now runs AFTER the catalog `gate()` (was before), so a gate failure no longer leaves an orphan .md on disk — strictly safer, index still uncommitted either way. `author()` now resolves via `_author_of(db,...)` — predicate is exactly the old `_role_item OR _operator_item`, and reading from the in-transaction db is the correct fix for authors created earlier in the same import.
  - Lead #2 (reflog snapshot-timing): CORRECT. `_ReflogOp` now carries its own ts/actor/session captured at `_log` (buffer) time. For the interactive one-op-per-transaction case this is byte-identical (no rebind between `_log` and flush; clock/actor unchanged). For the multi-rebind import case each op correctly captures its own event's at/as. `_log` reads ambient clock/actor at call time; no other `ctx.log` callers exist.
  - Lead #3 (dry-run shadow isolation): HOLDS. `_plan_import` operates only on `store.load().model_copy(deep=True)`; every `_sim_*` and every `_X_model` is pure (no write_new/update_frontmatter/_aio.write_text/_write_block_file; `_log` is a no-op outside a transaction anyway). Simulated `allocate_id` bumps the shadow counter only. No path (incl. error paths) writes during validation. `--dry-run` verified to write nothing.
  - Lead #4 (apply atomicity + context-restore): HOLDS. One `store.transaction()`; per-event `clock.set_now`/`actor.set_actor` wrapped in try/finally `bind_context(prior)` so the rebind is restored even on exception and cannot leak past the event/import; files-then-index order preserved for crash-safety (repair test passes). @manager: recommend Approved after F1.
- [2026-07-23T14:47:25Z] Elias Python:
  - F1 fixed: reordered _add_block_model so _require_parent (which runs _check_type) executes before _resolve_add_status — an unknown/mismatched kind now raises a clean SquadsError caught by the pre-pass's _COLLECTIBLE tuple, instead of KeyError-ing out of self.spec.subentity_kinds[kind]. No behavior change for any valid call (check_type passing implies kind is necessarily a real declared kind, so _resolve_add_status never saw a bad kind on the success path either).
  - Added tests/service/test_bulk_import_engine.py::test_an_unknown_add_sub_kind_is_collected_not_a_traceback (dedicated) and extended the existing multi-error pre-pass test with an 8th... 7th bad line (add-sub/no-such-kind) to confirm it composes with the other 6 collected error classes in one file.
  - Gates: pyright + ruff check + ruff format --check clean repo-wide; targeted (import engine + all subentity/subtask/story-lifecycle service tests + tests/meta) green; sq check clean. Leaving REV-641 status for the manager.
- [2026-07-23T14:50:53Z] Catherine Manager:
  - Manager verification: F1 fixed by reordering _add_block_model so kind-validation (_require_parent/_check_type) precedes _resolve_add_status — unknown add-sub kind is now a collected line-numbered ImportIssue, not a KeyError traceback (test added, multi-error pre-pass proves 7 classes collected). All four integrity leads verified: mutation refactor behavior-preserving (+ bonus: create writes after gate, no orphan .md), reflog buffer-time snapshot correct, dry-run shadow isolation holds, apply atomicity + try/finally context-restore sound. Full suite green. Approving.
<!-- sq:discussion:end -->
