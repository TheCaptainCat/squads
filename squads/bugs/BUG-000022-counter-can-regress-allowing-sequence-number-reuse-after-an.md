---
id: BUG-000022
sequence_id: 22
type: bug
title: Counter can regress, allowing sequence-number reuse after an item file disappears
status: Done
author: product-owner
priority: high
refs:
- FEAT-000019
- FEAT-000023:relates
description: Hand-edited or repair-rebuilt indexes accept a regressed counter, so
  deleted items' numbers get reused; repair sets counter to max-found, ignoring the
  previous high-water mark
created_at: '2026-06-10T13:51:32Z'
updated_at: '2026-06-11T13:19:07Z'
---
<!-- sq:body -->
## Observed (live incidents, 2026-06-10, this very squad)

1. `TASK-000021` was created and later `Cancelled`.
2. The operator rolled it back manually — deleted the file and **hand-edited the index, regressing
   the counter to 20**.
3. The next `sq create bug` allocated **21 again** → `BUG-000021` now occupies the sequence number
   that `TASK-000021` held. Any surviving mention of `TASK-000021` (comments, prose, git history,
   people's memory) now points at an unrelated bug via the shared number.
4. Nothing objected at any point: the regressed counter was accepted silently, the reuse happened
   without a warning, and `sq check` reports no issues afterwards.

It then happened a second time, to **this very item**: the first BUG-000022 was deleted from disk
and `sq repair` rolled the counter back to 21 (`rebuilt index: 21 items, counter=21`); this refiled
copy reclaimed number 22. Harmless here — same content, same number — but it demonstrates the
repair pathway end-to-end on a real squad.

## Why this is high priority

"One monotonic counter; an ID's number is globally unique" is a core invariant, and number-based
addressing (`sq task 21`) plus the FEAT-000019 direction (bare numbers accepted everywhere) lean
on it hard. Reuse silently rebinds history. This also touches the 1.0 durable-format promise
(EPIC-000012): the on-disk format must not allow a squad to quietly recycle identities — and since
the `.md` files are the source of truth and the index is "just a rebuildable cache", operators
*will* touch these files and rerun `repair`; the invariant has to survive exactly that.

## Mechanism — two routes to the same regression

- **Hand-edited index**: nothing validates the counter against the items on load; a counter below
  the max existing sequence number is accepted and the next `create` reuses.
- **`repair` after file loss** (verified in code, `_services/_maintenance.py:111-126`, and live —
  see above): `repair` rebuilds a fresh DB and sets `counter = max sequence found on disk`,
  ignoring the previous counter. Delete (or lose, via any crashed file operation) the
  highest-numbered item's file, run `sq repair`, and the counter regresses.

## Expected

- The counter never regresses: `repair` keeps `max(previous counter, max found)`, and loading an
  index whose counter is below the max item sequence is repaired upward (or flagged) rather than
  trusted.
- Ideally `repair`/`check` reports items that were in the previous index but are missing from
  disk — a deletion is an event worth surfacing, not silently absorbing.
- Related: FEAT-000023 (sanctioned removal) would give operators a tool that preserves the
  high-water mark, removing the *reason* to hand-edit.

## Repro

In a scratch squad: create items up to N; delete item N's file; `sq repair`; `sq create …` →
observe N reused. (Both routes reproduced live in this squad.)
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-10T13:52:01Z] Nina Product:
  - Refiled after an authorized deletion test by op-pierre — the deletion itself exercised the repair pathway and this copy reclaimed number 22, which is the bug in action.
- [2026-06-11T12:12:11Z] Catherine Manager:
  - Triage 2026-06-11: confirmed high — first in the bug queue. Core invariant violation (counter monotonicity), already reproduced twice live in this squad. Scope: repair keeps max(previous counter, max found on disk); loading an index whose counter is below the max item sequence repairs upward (or flags); repair/check surfaces items present in the previous index but missing from disk. FEAT-000023 (sanctioned removal) linked as relates — it removes the reason to hand-edit the index.
- [2026-06-11T12:16:07Z] Olivia Lead:
  - Fix task created: TASK-000042 (high, @python-dev). Scope split into 4 subtasks — repair high-water mark, load-time counter validation, missing-items reporting, regression tests. First in the queue.
- [2026-06-11T12:51:03Z] Olivia Lead:
  - @qa Fix landed and reviewed (TASK-000042, Done). Counter is now monotonic: repair keeps max(previous counter, max-on-disk), and load() raises a regressed stored counter to the max sequence. Please verify: delete the highest-numbered item's .md, run `sq repair` (counter must hold + missing item warned), then create a new item (must be max+1, never the reused number); also hand-edit the index counter below the max and confirm load() repairs it upward. Changes are in the working tree, uncommitted. Bug stays open until you verify.
- [2026-06-11T13:19:07Z] Mara Tester:
  - Verified fix for BUG-000022 (TASK-000042) against working tree.
  - Scenario 1 (repair after file loss): created 3 tasks (seq 9-11), deleted TASK-000011 file, ran sq repair → counter held at 11 (not regressed to 10); new create allocated TASK-000012 (no reuse of 11); sq repair output: 'warn TASK-000011: indexed but no markdown file found (deleted?)'.
  - Scenario 2 (hand-regressed counter): manually set counter=8 in .squads.json (max seq=12); ran sq list → file NOT rewritten (counter still 8); ran sq create → allocated TASK-000013 (max+1=13) and persisted corrected counter=13.
  - Scenario 3 (sq check): deleted highest item file without repair → sq check exits 1 with 'error TASK-000011: in index but no markdown file found'. Missing items are surfaced.
  - All acceptance criteria met. Closing.
<!-- sq:discussion:end -->
