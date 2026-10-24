---
id: TASK-1116
sequence_id: 1116
type: task
title: Close the rebuild and measure per-OS CI against the targets
status: Draft
parent: FEAT-1096
author: tech-lead
assignee: devops
priority: high
refs:
- TASK-1113:depends-on
- TASK-1114:depends-on
- TASK-1115:depends-on
description: Old root gone, ledger complete, one CI run per OS recorded against the
  binding targets.
subentities:
- local_id: ST1
  title: Confirm the old root is gone and the parity ledger is complete
  status: Todo
  story: US9
- local_id: ST2
  title: Record one CI run per OS against the binding targets
  status: Todo
  story: US10
created_at: '2026-10-24T13:42:20Z'
updated_at: '2026-10-24T13:43:33Z'
---
<!-- sq:body -->
Close the rebuild: confirm the old root is gone, finish the parity record (US9), and measure CI per OS against the binding targets (US10).

**Binding targets** (op-pierre, 2026-10-24): every CI test job under 10 minutes; Windows up to 15. Baseline from the 2026-10-17 push to `main` (run 39020459902): Windows 53 min, macOS 14 min, Ubuntu 8 min for the pytest step.

**Proposals for the operator:** the test-count ceiling (3,500), a local full run at or under 60 s, the default local run at or under 30 s, and an internal design target of Windows at or under 12 min so one slow runner day does not break the 15-minute limit.

**Acceptance**

- No test remains under the old root; the new root is the only `testpaths` entry (renamed to `tests/` if the operator chooses); `uv run --all-extras pytest`, pyright, ruff and `sq check` are clean.
- The ledger shows every entry with an owner and a recorded red, or a recorded gap in the old suite.
- One CI run per OS after the last deletion is recorded in a comment: wall time, worker count, test count, run link, compared to the targets and to the baseline from the inventory task. Every job is under 10 minutes and Windows under 15; a miss is reported with its `--durations` profile and is not closed as met.
- The count-ceiling guard passes at the agreed number.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1116 add-subtask "<title>"`; track with `sq task 1116 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Confirm the old root is gone and the parity ledger is complete

<!-- sq:subtask:ST1:body -->
Confirm no old test file remains, rename the new root to `tests/` if the operator chooses, make it the only `testpaths` entry, and check the ledger has an owner and a recorded red (or a recorded gap) for every entry.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Record one CI run per OS against the binding targets

<!-- sq:subtask:ST2:body -->
Run the CI test job once per OS after the last deletion and record wall time, worker count, test count and the run link against the binding targets and the inventory baseline. Report any miss with its `--durations` profile.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
