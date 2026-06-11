---
id: TASK-000042
sequence_id: 42
type: task
title: Fix counter regression and sequence-number reuse (BUG-000022)
status: Done
author: tech-lead
assignee: python-dev
priority: high
refs:
- BUG-000022:fixes
subentities:
- local_id: ST1
  title: 'Repair keeps high-water mark: counter = max(previous counter, max found
    on disk)'
  status: Todo
- local_id: ST2
  title: 'Load-time counter validation: repair upward when stored counter is below
    max item sequence'
  status: Todo
- local_id: ST3
  title: Report items missing from disk vs the previous index in repair/check
  status: Todo
- local_id: ST4
  title: Regression tests (service + CLI) covering both regression routes
  status: Todo
created_at: '2026-06-11T12:14:51Z'
updated_at: '2026-06-11T13:00:51Z'
---
<!-- sq:body -->
## Goal

Make the global counter monotonic so an item's sequence number is never reused, even after a file is lost and `repair` rebuilds the index. Restores the core invariant: "one monotonic counter; an ID's number is globally unique."

## What to change

1. **Repair high-water mark** — `_services/_maintenance.py` (around the rebuild, ~line 111-126). Today `repair` sets `counter = max sequence found on disk`, ignoring the previous counter. Change it to `counter = max(previous counter, max found on disk)` so deleting the highest-numbered item's file can no longer regress the counter.
2. **Load-time counter validation** — `_index/_store.py`. On `load`, if the stored counter is below the max item sequence in the index, repair it upward (raise the counter to the max) rather than trusting a regressed value. A hand-edited index that regressed the counter must not silently allocate a reused number. Allocation still happens only inside `IndexStore.transaction()` (invariant 2).
3. **Missing-items reporting** — `repair`/`check` should surface items present in the *previous* index but absent from disk. A deletion is an event worth flagging, not silently absorbing. Wire the report through the existing result dataclasses (`_services/_results.py`) and the CLI surface in `_cli/`.

## Notes / invariants

- Frontmatter stays the source of truth; the counter is the one piece of index state that is NOT reconstructable from a single file, which is exactly why it must not regress (invariant 1 + 2).
- Use `SquadsError` for any user-facing error; raise through `@handle_errors`.
- Related: FEAT-000023 (sanctioned removal) would give operators a removal tool that preserves the high-water mark — out of scope here, but keep the reporting shape compatible.

## Acceptance

- Service-level tests: repair after deleting the top item keeps the counter (no regression); the next allocate yields max+1, never a reused number. Load with a regressed stored counter repairs upward. Missing-items are reported by repair/check.
- CLI smoke tests: `sq repair` and `sq check` over a squad with a deleted top item — counter held, missing item surfaced, exit codes correct.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 42 add-subtask "<title>"`; track with `sq task 42 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Repair keeps high-water mark: counter = max(previous counter, max found on disk) |  |
| ST2 | Todo |  | Load-time counter validation: repair upward when stored counter is below max item sequence |  |
| ST3 | Todo |  | Report items missing from disk vs the previous index in repair/check |  |
| ST4 | Todo |  | Regression tests (service + CLI) covering both regression routes |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Repair keeps high-water mark: counter = max(previous counter, max found on disk)

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Load-time counter validation: repair upward when stored counter is below max item sequence

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Report items missing from disk vs the previous index in repair/check

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Regression tests (service + CLI) covering both regression routes

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T12:30:54Z] Elias Python:
  - Implemented fix for BUG-000022 — three changes across four files.
  - **_index/_store.py** — load() now checks db.counter < max(sequence_ids) and silently raises it under the lock before returning. Prevents a hand-edited regressed counter from surviving to the next allocation.
  - **_services/_maintenance.py** — repair() snapshots the previous counter before rebuilding, then sets counter = max(previous_counter, max_found_on_disk). Also collects IDs that were in the old index but whose files are gone (missing_ids). Returns RepairResult instead of SquadsDB.
  - **_services/_results.py** — added RepairResult dataclass (db, missing_ids) used by the repair pathway.
  - **_cli/_main.py** — sq repair now prints a warn line for each missing ID. All callers of repair() updated to use result.db.
  - **Tests** — 5 new service-level tests (test_repair_keeps_counter_after_top_item_deleted, test_allocate_after_repair_never_reuses, test_load_corrects_regressed_counter, test_repair_reports_missing_ids, test_check_flags_index_item_with_no_file) and 2 CLI smoke tests (sq repair counter hold + sq check missing-item exit-1). 219 passed, 1 skipped.
  - pyright clean on changed files; ruff check/format clean (pre-existing F401s in _items.py/_cli/__init__.py unchanged). @tech-lead ready for review.
- [2026-06-11T12:50:22Z] Olivia Lead:
  - Review PASS — Done. Counter monotonicity restored and verified live: deleting the highest-numbered item's file then `sq repair` holds counter=4 and emits 'warn BUG-000004: indexed but no markdown file found (deleted?)'; the next create yields TASK-000005, never reuses 4. load() raises a regressed stored counter to max(sequence_id) under the lock (write-back on a query path — acceptable: it's idempotent self-healing, only fires on corruption, and is the cheapest place to enforce invariant 2).
  - Allocation still only inside transaction() (invariant 2 intact). New RepairResult(db, missing_ids) dataclass; all repair() callers (CLI repair, adopt) updated. check()'s 'in index but no markdown file found' was already present on HEAD; the genuinely-new part is repair-side missing_ids reporting + the regression tests. 7 new tests, all green. pyright/ruff clean on changed files. Frontmatter-as-truth and SquadsError conventions respected.
- [2026-06-11T12:56:40Z] Pierre Chat:
  - Decision: load() must stay strictly read-only — no write-back on a regressed counter. Corrections happen only in repair and transaction. Reopening for rework.
  - Suggested shape: load() corrects the counter in memory (so allocate never reuses) without persisting; transaction persists the corrected value naturally on its next save; repair keeps the explicit high-water-mark logic. @python-dev
- [2026-06-11T12:58:21Z] Elias Python:
  - Reworked load() to be strictly read-only per Pierre's decision.
  - load() still corrects a regressed counter in memory (so no subsequent allocate_id can ever reuse a sequence number), but the lock/write-back is gone — the file is not touched. The corrected value reaches disk only when the next transaction() saves (e.g. a create or any mutation), or when sq repair is run explicitly.
  - transaction() calls load() internally, so it automatically receives the in-memory correction and persists it as part of its normal write-back. No extra code needed there.
  - repair keeps its explicit max(previous_counter, max_found) logic unchanged.
  - Updated test_load_corrects_regressed_counter: now asserts the file still has counter=1 after load(), the returned db has counter=3, and the subsequent create both allocates sequence 4 and persists counter=4 to disk.
  - All gates green: 247 passed 1 skipped, pyright 0 errors, ruff clean. @tech-lead ready for review.
- [2026-06-11T13:00:50Z] Olivia Lead:
  - Re-review PASS (targeted, post-rework). Verified against Pierre's design decision: load() is now strictly read-only.
  - load() in _index/_store.py: corrects the regressed counter to max(sequence_id) **in memory only** and returns db — no write-back. Confirmed by reading the code, not just the claim.
  - transaction() persists genuinely: its internal self.load() returns the corrected db, allocate_id bumps from that base, and the unconditional _atomic_write(db) on commit writes the corrected counter to disk. repair unchanged.
  - Test test_load_corrects_regressed_counter asserts the full chain: file-untouched-after-load (disk counter stays 1), corrected-in-memory (loaded.counter==3), and next-create persists counter==4 allocating max+1=4. Honest setup.
  - Gates green repo-wide: 247 passed / 1 skipped; pyright 0 errors; ruff check + format clean.
  - Live spot-check in scratch squad: hand-regressed counter to 3 (max seq 8); 'sq list' left the file byte-identical (md5 unchanged, counter still 3); 'sq create' then allocated TASK-000009 (max+1, no reuse of 1-8) and persisted counter=9. 'sq check' clean (exit 0).
  - Moving to Done. Not committing per instruction.
<!-- sq:discussion:end -->
