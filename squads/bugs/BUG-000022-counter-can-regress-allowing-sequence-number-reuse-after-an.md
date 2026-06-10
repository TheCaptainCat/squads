---
id: BUG-000022
sequence_id: 22
type: bug
title: Counter can regress, allowing sequence-number reuse after an item file disappears
status: Ready
author: product-owner
priority: high
refs:
- FEAT-000019
description: Hand-edited or repair-rebuilt indexes accept a regressed counter, so
  deleted items' numbers get reused; repair sets counter to max-found, ignoring the
  previous high-water mark
created_at: '2026-06-10T13:51:32Z'
updated_at: '2026-06-11T07:54:56Z'
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
<!-- sq:discussion:end -->
