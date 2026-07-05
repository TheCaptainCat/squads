---
id: REV-105
sequence_id: 105
type: review
title: Review of TASK-000101 — explicit ID padding foundation
status: Approved
parent: TASK-101
author: reviewer
refs:
- ADR-104
description: Padding stored in index, single formatter, exhaustion guard, repair floor
subentities:
- local_id: F1
  title: _renumber_plan emits DEFAULT-width IDs, ignoring db.padding (_maintenance.py:246)
  status: Open
  severity: low
- local_id: F2
  title: repair's filename-recompute arm (max stored_floor/filename_width) is untested
  status: Open
  severity: low
- local_id: F3
  title: Dead/redundant code in the repair padding computation
  status: Open
  severity: low
created_at: '2026-06-14T21:18:09Z'
updated_at: '2026-06-15T08:03:07Z'
---
<!-- sq:body -->
Review of TASK-101 (foundation of FEAT-27, explicit ID padding). Changes reviewed in the working tree (uncommitted).

VERDICT: Approved. The core implementation is correct and matches the spec, the architect's ruling, and ADR-104. Three low-severity findings recorded — all non-blocking (one borderline-scope width issue, one coverage gap, one clarity nit).

Checked: (1) single formatter — every :06d funnels through format_item_id; straggler grep clean. (2) id_padding seam — Field(exclude=True) strips it from every model_dump/model_dump_json path (--json in _items/_main/_create) and the index to_json; to_frontmatter_dict is an explicit allowlist that omits it; goldens unaffected; committed index has no id_padding. (3) exhaustion guard — fires at counter >= 10**padding-1, names sq migrate repad, never advances the counter; boundary correct (999999 is the last legal width-6 sequence, no off-by-one). (4) repair carry-forward — max(stored_floor, max_filename_width) per ADR-104, derives from filename digit-run not frontmatter, backfills 6, idempotent, mirrors the counter high-water-mark handling. (5) conventions — no datetime, SquadsError used, no import cycle (_errors has no imports), pyright/ruff clean. (6) tests — default/stored padding, format widths, exhaustion at cap, JSON exclusion, repair floor, backfill-write, create-at-capacity all covered.

Gate (re-run by reviewer): 554 passed / 1 skipped; pyright 0 errors; ruff check clean; ruff format clean.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 105 add-finding "…" --severity high`; track with `sq review 105 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | _renumber_plan emits DEFAULT-width IDs, ignoring db.padding (_maintenance.py:246) |
| F2 | 🟢 low | Open |  | repair's filename-recompute arm (max stored_floor/filename_width) is untested |
| F3 | 🟢 low | Open |  | Dead/redundant code in the repair padding computation |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — _renumber_plan emits DEFAULT-width IDs, ignoring db.padding (_maintenance.py:246)

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
`_renumber_plan` formats collision-renumber IDs at DEFAULT padding, not `db.padding`. `src/squads/_services/_maintenance.py:246` calls `format_item_id(item_type.prefix, next_free)` with no padding arg, so it always emits width-6 IDs. On a squad that has been repadded to width 7, a merge-collision `repair --renumber` would mint width-6 filenames into an otherwise width-7 corpus, re-introducing exactly the mixed-width state this feature exists to prevent. Borderline scope (renumber is merge-collision repair; the repad command is TASK-102), but the fix is one argument.

**Suggested fix:** thread the rebuilt `db.padding` into `_renumber_plan` (it is a `@staticmethod` with no db access today) and pass it as the third arg to `format_item_id`, OR document explicitly that renumber-width follows in TASK-103 width-tolerant work. Flagging so it is a conscious decision, not an oversight.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — repair's filename-recompute arm (max stored_floor/filename_width) is untested

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
No test exercises the filename-recompute arm of repair's `max(stored_floor, max_filename_width)`. Every padding test (`test_service.py:92-127`, `test_cli.py:1529`) only manipulates the STORED padding and keeps filenames at width 6; none creates item files whose digit-run is width 7 with a stored floor of 6 and asserts repair raises padding to 7. That recompute (`src/squads/_services/_maintenance.py:199-203`) is the heart of ADR-104 and the architect's explicit guard (read the digit-run width, ignore non-item files). It is currently unverified.

**Suggested fix:** add one test that renames a created item file to a width-7 name (`TASK-0000007-...md`), leaves the stored padding at 6, runs repair, and asserts `result.db.padding == 7` — the partial-corpus / post-repad-pre-repair scenario the floor+recompute pair is designed for.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Dead/redundant code in the repair padding computation

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Dead/redundant code in the repair padding computation. `src/squads/_services/_maintenance.py:204-208`: `max_filename_width if max_filename_width > 0 else 0` is a no-op (a value is already >0 or it is 0), and the following `if db.padding < DEFAULT_ID_PADDING: db.padding = DEFAULT_ID_PADDING` guard can never fire — `previous_padding` is seeded to `DEFAULT_ID_PADDING` (6) and carried as the floor, so `db.padding = max(>=6, ...)` is always >=6. Harmless but it obscures the actual invariant.

**Suggested fix:** collapse to `db.padding = max(previous_padding, max_filename_width)` and drop the trailing guard, with a one-line comment that `previous_padding` already floors at 6 via the model default. Clarity only.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-14T21:19:00Z] Paul Reviewer:
  - Approved. Core seam is correct and the gate is green (554 passed/1 skipped, pyright/ruff clean). Three LOW findings recorded, none blocking merge: F1 _renumber_plan emits width-6 IDs ignoring db.padding (borderline scope — renumber vs repad), F2 filename-recompute arm of repair is untested, F3 dead guard in the padding computation. @manager TASK-101 is approved / ready-to-merge. Recommend the three low findings be folded into TASK-102 (repad) and TASK-103 (width-tolerant reads) rather than blocking this foundation — F1 in particular naturally belongs with the repad work that introduces non-6 widths.
- [2026-06-15T08:03:07Z] Paul Reviewer:
  - Formatting amendment (no content change): the three findings had their entire write-up stuffed into the title field, leaving the summary table and finding headers as walls of text and the bodies as placeholders. Moved each finding's full prose into its body and trimmed the titles to scannable one-liners. Verdict (Approved), severities (all low), and statuses (Open) unchanged; sq check clean.
<!-- sq:discussion:end -->
