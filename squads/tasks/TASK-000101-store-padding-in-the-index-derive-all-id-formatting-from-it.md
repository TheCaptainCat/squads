---
id: TASK-000101
sequence_id: 101
type: task
title: Store padding in the index, derive all ID formatting from it, and guard create
  against exhaustion
status: Done
parent: FEAT-000027
author: tech-lead
assignee: python-dev
refs:
- ADR-000104
- REV-000105:addresses
subentities:
- local_id: ST1
  title: Store padding in index; ID formatting derives from it
  status: Done
  story: US1
created_at: '2026-06-14T20:56:35Z'
updated_at: '2026-06-23T09:58:29Z'
---
<!-- sq:body -->
Make ID width an explicit, stored part of the on-disk format.

## Scope
- Add `padding: NonNegativeInt = 6` to `SquadsDB` (`_models/_index.py`) — alongside `counter`. It is authoritative index state (NOT item-frontmatter-derived).
- Add a single formatting helper (e.g. `SquadsDB.format_id(item_type, sequence)` or a module helper taking the width) and route ALL ID formatting through it. Remove every hard-coded `:06d`:
  - `Item.id` computed_field (`_models/_item.py:85`) — the Item must format against the active padding. Item has no back-pointer to the DB, so thread the width in (e.g. a class/context width or format at the index/service boundary). Pick the cleanest approach and note it for review.
  - `SquadsDB.allocate_id` (`_models/_index.py:52`).
- **Exhaustion guard** in `allocate_id`: when the next counter value would exceed capacity (10**padding - 1; 999999 at width 6), raise a `SquadsError` stating the index is full and naming the fix — `sq migrate repad <width>`. Never emit an ID wider than the padding.
- `repair` must PRESERVE the stored padding across a rebuild (like it preserves the counter high-water mark) — padding is carried forward, not recomputed from filenames. Backfill `padding=6` for any pre-existing index that lacks it (model default handles new reads; ensure repair writes it).

## Out of scope
- The repad command itself (TASK-000102) and read-side tolerance (TASK-000103).

## Invariants
- Default width stays 6 — golden-file tests keyed to width-6 IDs MUST stay green.
- Global-counter rules unchanged; allocation only inside `transaction()`.

## Tests
- Service + CLI: allocating at capacity raises the index-full error naming `sq migrate repad`; nothing wider than padding is emitted. A squad with an explicit non-6 padding formats IDs at that width.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 101 add-subtask "<title>"`; track with `sq task 101 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Store padding in index; ID formatting derives from it | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Store padding in index; ID formatting derives from it

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a squad owner whose counter hits the cap, I want create to fail with a clear index-full error naming the fix, so that the format never silently grows a digit
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Padding stored in index; all ID formatting derives from it; allocate_id raises index-full at capacity naming sq migrate repad.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-14T21:13:15Z] Elias Python:
  - Implementation complete. All 554 tests pass; pyright and ruff are clean.
  - **Formatter seam chosen**: Added `format_item_id(prefix, sequence_id, padding)` as a module-level helper in `_models/_item.py`. `SquadsDB.format_id(item_type, seq)` wraps it using `self.padding`. `Item.id` uses an `id_padding` field (pydantic `Field(exclude=True)`) defaulting to 6, threaded in from `db.padding` by the service layer at item-construction time. Items loaded from disk via `from_frontmatter` retain the default (6), which is correct for TASK-000101 scope; TASK-000103 handles width-tolerant equality.
  - **Files changed**: `src/squads/_models/_item.py` (DEFAULT_ID_PADDING, format_item_id, id_padding field), `src/squads/_models/_index.py` (padding field, format_id, allocate_id exhaustion guard), `src/squads/_services/_base.py` (thread id_padding=db.padding at Item construction), `src/squads/_services/_maintenance.py` (repair carries padding with max(floor, max_filename_width), _renumber_plan uses format_item_id), `src/squads/_cli/_common.py` (3 error messages use format_item_id instead of :06d).
  - **Tests added**: 8 service/model tests (test_index.py, test_service.py) covering default=6, format_item_id widths, db.format_id, allocate_id at non-default padding, exhaustion guard at capacity, id_padding excluded from serialization, repair floor carry-forward, backfill write, create-at-capacity error. 2 CLI smoke tests (test_cli.py) covering repair holds padding floor after file deletion and create exits 1 naming sq migrate repad at capacity.
  - **Note for TASK-000102 (repad command)**: the seam is clean. `SquadsDB.padding` is the single source of truth; updating it in a transaction and renaming all item files is all that's needed. `format_id` produces IDs at the new width once padding is bumped. Nothing in the current implementation needs to change for repad.
  - **Note for TASK-000103 (width-tolerant equality)**: `from_frontmatter` items use default padding (6), so after a repad the `item.id` from a loaded item will be at width 6 even if the frontmatter id is width 7. TASK-000103 should focus on `split_ref`/resolver normalisation (strip leading zeros to compare sequence numbers) not on `Item.id` equality. The `number_for_id` helper in `_paths.py` already does `rsplit + int()` which is inherently width-tolerant.
  - @reviewer please review the formatter seam in _item.py and _index.py and the repair padding logic in _maintenance.py.
- [2026-06-14T21:19:07Z] Paul Reviewer:
  - Reviewed in REV-000105 → Approved (ready to merge). Gate re-run clean: 554 passed/1 skipped, pyright 0 errors, ruff check + format clean.
  - Three LOW findings (non-blocking): F1 _renumber_plan formats at default width-6 ignoring db.padding (_maintenance.py:246); F2 the filename-recompute arm of repair's max(floor, filename-width) is untested; F3 dead guard in the padding computation (_maintenance.py:204-208). Recommend folding F1/F2 into TASK-000102/103 rather than reopening this foundation. @manager for the merge call.
<!-- sq:discussion:end -->
