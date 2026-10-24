---
id: TASK-1111
sequence_id: 1111
type: task
title: 'Inventory the old suite: parity ledger and falsification audit'
status: Ready
parent: FEAT-1096
author: tech-lead
assignee: qa
priority: high
refs:
- TASK-1110:depends-on
- TASK-1098:depends-on
- TASK-1103:depends-on
- TASK-1104:depends-on
- TASK-1105:depends-on
- TASK-1106:depends-on
- TASK-1107:depends-on
- TASK-1123:depends-on
- TASK-1124:depends-on
- TASK-1125:depends-on
- TASK-1126:depends-on
description: Parity ledger, per-module falsification audit and per-OS CI baseline;
  read-only on tests and src.
subentities:
- local_id: ST1
  title: Build the parity ledger from regression classes, bugs and findings
  status: Todo
  story: US1
- local_id: ST2
  title: Run the falsification audit per source module on the old suite
  status: Todo
  story: US2
- local_id: ST3
  title: Record the per-OS CI baseline with durations and worker counts
  status: Todo
  assignee: devops
  story: US10
created_at: '2026-10-24T13:42:12Z'
updated_at: '2026-10-24T21:56:19Z'
---
<!-- sq:body -->
Inventory what the old suite protects before any of it is rebuilt: the parity ledger (US1), the falsification audit (US2) and the per-OS CI baseline every later increment is measured against (US10). Read-only on `tests/` and `src/`: no old test is deleted or edited here. The one file this task adds to the repo is the ledger, `tests_next/LEDGER.md`, which starts the new root; the rest of that root is set up by the next task.

The task starts after the queue ahead of it (TASK-1110, TASK-1098 and the FEAT-1101 tasks TASK-1103 to TASK-1107) has landed, so the suite it inventories is the one the rebuild replaces.

**Measured on 2026-10-24** (`pytest --collect-only --run-slow`, static reads, `gh run view 39020459902`, the 2026-10-17 push to `main`):

- 13,931 tests in 751 files. Per directory: `tests/service` 5,119; `tests/unit` 3,668; `tests/cli` 3,383; `tests/integration` 1,228; `tests/meta` 450 (55 files); `tests/tui` 77; `tests/test_scale.py` 6 (the only `slow` tests, skipped in CI).
- From the earlier count the same day (13,816 tests): 4,975 test functions; 9,605 parametrised rows (70%) from 760 parametrised functions; the 20 largest functions hold 3,811 tests (28%), the 100 largest 6,283 (45%).
- CI pytest step: Windows 3,190 s (53 min, 13,772 passed, 44 skipped), macOS 852 s (14 min), Ubuntu 480 s (8 min). Setup steps are under 10 s each; the time is all pytest. That is about 231 ms per test on Windows, 62 on macOS, 35 on Ubuntu. Worker counts are not in the `-q` log.
- A filename heuristic puts about 8,100 tests in 509 files on a fresh `init` per test, against 1,500 tests in 33 files that copy a shared squad (`tests/_roster_squad.py` pattern). This is an estimate from static reads, to be confirmed by the profile.

The queue ahead adds tests, so ST2 and ST3 re-count at the start and the ledger and baseline cite that count, not these figures.

**What makes an edge case a ledger entry.** An entry is kept when it falls in one of these sources, and only then:

1. The regression classes seeded in the FEAT-1096 body.
2. A Verified or Fixed bug (115 Verified, 6 Fixed on 2026-10-24) whose fix added or changed a test: found from the bug's refs, the fixing commit and `git log -S` on the test name.
3. A defect-severity review finding (critical, high, medium; Verified or Fixed), REV-706 F1, F10, F11 and F12 included.
4. An old test that the audit shows is the only one red for some break of its seam (a unique kill). A row that only ever goes red together with its siblings is redundant; a row that never goes red is not protective. Neither becomes an entry.

Each entry names the seam (module and function), the user-visible behaviour, the area that owns it (integrity core, engine/services/CLI, or backend/skills/rendering/TUI, matching the three area tasks), the owning layer in the new suite, the old test ids that cover it today, and the break used to prove it (a small described patch to `src/`). The area tasks later fill in the new owner test and the recorded red.

**Order.** ST2 runs first: sources 1 to 3 of ST1 can be gathered alongside it, but source 4 comes from the audit.

**Acceptance**

- `tests_next/LEDGER.md` exists with every entry carrying the fields above; every seeded class and every qualifying bug and finding is either an entry or listed as not reproducible with a reason.
- The audit report, posted as a comment on this task, states per `src/` module how many sampled old tests stayed green under a break of their seam, and names the worst tables and fixtures. The 30 largest parametrised functions are all in the sample, and every `tests/meta` guard is broken once against its target.
- The CI baseline per OS is recorded in a comment: test count, wall time, worker count, the top 50 `--durations` with setup and call split, and the run link.
- Mutations are applied only in a scratch worktree, never in the shared tree, and only the selected test ids are run per break, never the full suite.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1111 add-subtask "<title>"`; track with `sq task 1111 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Build the parity ledger from regression classes, bugs and findings

<!-- sq:subtask:ST1:body -->
Build `tests_next/LEDGER.md` from the four sources in the task body: the seeded regression classes, the Verified and Fixed bugs whose fixes touched tests, the defect-severity review findings, and the unique kills ST2 finds. Each entry: seam, behaviour, owning area, owning layer, old test ids, the break that proves it, with empty slots for the new owner test and its recorded red that the area tasks fill. Classes that cannot be traced to a test are listed with the reason, so the rebuild knows to write them rather than port them.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Run the falsification audit per source module on the old suite

<!-- sq:subtask:ST2:body -->
Re-count the suite first (`pytest --collect-only --run-slow`) and cite that count. For each `src/` module, break its seams one at a time in a scratch worktree and run only the old tests that target it. Record per test: red, green, or red only with all its siblings. Cover the 30 largest parametrised functions in full, starting with `tests/cli/test_c_runs_exactly_as_cd_into_the_folder_would.py` (477 rows: layouts by command by schema direction), `tests/unit/test_place_view_tags_fuzz_idempotence_and_invertibility.py` (1,001 rows) and `tests/service/test_a_check_reports_only_on_the_types_that_select_it.py` (488 rows: check by type by level). Break each `tests/meta` guard once against its target. Post the report as a comment on this task: the share that stayed green per module, the rows that carry the information in each large table, and the guards that stayed green.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Record the per-OS CI baseline with durations and worker counts

<!-- sq:subtask:ST3:body -->
Make the CI test job runnable on demand on a branch and print `--durations=50` with worker counts (today `test.yml` runs only on pushes and pull requests to `main`, with `-q`); the later increments reuse it. Run it once per OS on the suite as it stands when this task starts, and record test count, wall time, the worker count `-n auto` got, and the top offenders with their setup and call split. TASK-1095 is cancelled and this subtask carries its profiling. Windows runs the full suite, so its profile is the one that steers the rebuild. Check whether Windows Defender scans the temp directory on the hosted runner. Record what was measured and what was inferred.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:48:41Z] `tech-lead` Olivia Lead:
  - Re-read for Ready on 2026-10-24: recounted the suite (13,931 tests, 751 files), set the ledger at tests_next/LEDGER.md and the audit report as a comment here, added the meta-guard audit, the ST2-before-ST1 order and an on-demand CI run with durations (ST3). Moved to Ready.
- [2026-10-24T21:56:19Z] `tech-lead` Olivia Lead:
  - Added depends-on TASK-1123 (startup, FEAT-916) and TASK-1124, TASK-1125, TASK-1126 (FEAT-1092 structure). The ledger's seam fields and the audit's break patches name modules and functions those tasks move, so this inventory runs on the code as it will stay. The queue in the body's second paragraph now includes them.
<!-- sq:discussion:end -->
