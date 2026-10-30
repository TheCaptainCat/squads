---
id: BUG-1154
sequence_id: 1154
type: bug
title: check reports false duplicate id during a retitle
status: Verified
parent: MILE-1051
author: qa
created_at: '2026-10-25T22:05:02Z'
updated_at: '2026-10-26T12:15:07Z'
priority: low
severity: low
---
<!-- sq:body -->
## Steps (driven 2026-10-25, scratch squad, dev build 0.17)

1. `sq init` a scratch squad, create one milestone plus 120 filler milestones (lengthens the check scan).
2. Process A: 80 times `sq milestone 2 update --title "Title N vK"` (every call renames the file).
3. Process B, concurrently: `sq check` in a loop until A ends.

## Expected

`sq check` never reports a duplicate id for a board that is only being retitled; the rename is a single atomic `rename(2)`.

## Actual

10 of 61 `sq check` runs reported a false error, e.g.
`error MILE-2: 2 files carry this id (milestones/MILE-000002-title-0-v42.md, milestones/MILE-000002-title-1-v41.md); merge the content you want into one file, delete the other by hand, then run sq repair`.
A rerun is clean. With a 1-item board (short scan) 0 of 61 runs hit it, so the window is the length of the scan. Matches the 2026-10-25 report on MILE-1061 (0-18 vs 0-19 file names). The advice in the message (delete a file by hand) is dangerous for a false positive.

## Code location and write order

The writer is not the culprit. `_services/_items.py` `_update_core` (about line 446) calls `_move_item_file` (`_services/_base.py` ~1261) -> `_aio.path_rename` = `Path.rename`, one atomic rename; inside a deferred-write block the flush (`_base.py` ~1285) does rename, then `write_text`. The old and new file names never coexist on disk (read from code; no tight directory watcher was run).

The reader is the culprit. `_services/_check.py` `check()` (~473) takes no lock by design and only re-reads "cross-source" issues (`_confirm_cross_source`). The duplicate-id report is built from two separate reads: the scan records `(id, path)` pairs in a `CarrierLog` (reads the file under its old name), then `_id_carriers` (`_base.py` ~1669, called at `_check.py` ~516) lists the directory again and adds any not-yet-seen path. A rename between the two reads gives the same file under old and new names, and `duplicate_groups` reports it as two files. Same shape in `_maintenance.py` (~1540, ~2007) for repair paths, not driven.

Index lock: `transaction()` takes a three-layer lock (`_index/_store.py`), but `check` and the unlocked load used by list/show do not take it, so the lock does not cover this reader.

## Suggested fix direction (for tech lead)

Treat a duplicate-id group like the cross-source candidates: re-scan the group's paths once (confirm both still exist and still carry the id) before reporting. Not driven: `sq list`, `sq repair`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T09:44:36Z] `python-dev` Elias Python:
  - Root cause: check built the duplicate-id report from two reads, the scan log and a second directory listing; a rename between them put one file in the report under its old and new name.
  - Fix: a duplicate group is confirmed by re-reading its files (gone or no longer carrying the id drops out) before it is reported, as for cross-source issues. No lock added.
  - Repair: reads the carriers once per call (one listing, no second read to disagree with), so it is not the same shape; left unchanged. Test: tests/service/test_check_does_not_report_a_file_renamed_during_the_scan_as_a_duplicate.py (red without the confirmation).
- [2026-10-26T12:15:06Z] `qa` Mara Tester:
  - Verified on release/0.17 dev build (scratch squad, 121 milestones + 2 tasks; writer loop and `sq check`/`sq repair` loop in two processes; a report = "files carry" / numbers_unique / duplicate / traceback in the output):
    - Retitle loop (`milestone 9 update --title`, 50 iterations) vs `sq check`: 36 checks, 0 false reports. Control, same loop with the installed `~/.local/bin/sq` as reader: 9 of 39 flagged, so the race fires in this setup.
    - Retype loop (task 130 to bug and back, 60 rounds) vs `sq check` (shared-number rule): 100 checks, 0 reports.
    - Retitle + retype loop (40 rounds) vs `sq repair`: 115 runs, 0 duplicate/renumber/traceback; 25 rounds vs `sq repair --renumber`: 63 runs, 0; item count unchanged (121 milestones, 2 tasks, ids intact).
    - Real duplicate (hand-copied MILE-10 file): still reported, `error MILE-10: 2 files carry this id (...)`, exit 3; removing the copy gives 0 reports.
    Moving to Verified.
<!-- sq:discussion:end -->
