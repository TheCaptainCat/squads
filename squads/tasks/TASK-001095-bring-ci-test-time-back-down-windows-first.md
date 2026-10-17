---
id: TASK-1095
sequence_id: 1095
type: task
title: Bring CI test time back down, Windows first
status: Draft
author: tech-lead
refs:
- MILE-1051:targets
- FEAT-1096
description: CI went 19/2.5/4.5 min to 42/14.5/11 (Win/mac/Ubuntu) in 0.16; profile,
  then cut setup cost.
subentities:
- local_id: ST1
  title: Profile the suite per OS on CI with --durations=50
  status: Todo
- local_id: ST2
  title: Build each heavy table's scratch squad once per module and copy it per row
  status: Todo
- local_id: ST3
  title: Move the heaviest shape tables behind the slow marker without losing gate
    coverage
  status: Todo
- local_id: ST4
  title: Check xdist worker counts and runner settings on CI
  status: Todo
- local_id: ST5
  title: Measure the write-once guard's cost, and keep it on
  status: Todo
created_at: '2026-10-17T07:42:12Z'
updated_at: '2026-10-17T07:57:07Z'
---
<!-- sq:body -->
CI test time roughly tripled between the 0.15 and 0.16 release PRs. This task brings it back down, Windows first, using the simplest measures before any restructuring.

**Measured**

| Runner  | 0.15 PR | 0.16 PR |
|---------|---------|---------|
| Windows | 19 min  | 42 min  |
| macOS   | 2.5 min | 14.5 min |
| Ubuntu  | 4.5 min | 11 min  |

- The full suite takes about 3.5 min locally.
- The suite grew from about 6,300 to 13,800 tests in 0.16. Many are table-driven, and each row builds a scratch squad on disk.
- On Windows, pytest alone ran 2,515 s.

**Suspected, not profiled**

- Slow Windows file I/O (Defender scanning, NTFS, `os.replace`), multiplied over roughly 500k small files.
- Few runner cores, so `-n auto` gets 2 to 4 workers.
- The write-once guard adding about 8% on every OS.

None of these is confirmed. The profiling subtask comes first, and the rest is ordered by what it finds.

**Goal**

- Windows CI at or under about 15 min.
- macOS and Ubuntu CI at or under about 5 min.
- The local full suite unchanged or faster.

**Acceptance**

- Measured on CI, on a PR run after the changes land: wall time per OS for the test job meets the goal above. Record the before and after numbers in a comment.
- The release gate keeps the coverage it has today. Any test moved behind the `slow` marker still runs somewhere on the gate (one OS, or a nightly job the release checks), and the comment says where.
- The write-once guard stays on.
- No test is deleted to buy time.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1095 add-subtask "<title>"`; track with `sq task 1095 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Profile the suite per OS on CI with --durations=50

<!-- sq:subtask:ST1:body -->
Run the CI test job once per OS with `--durations=50` and record the top offenders in a comment: the test, its setup/call split, and the module. Also record the pytest wall time and the xdist worker count each runner got. This is the baseline every later subtask is measured against, and it confirms or rules out the suspected causes in the task body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Build each heavy table's scratch squad once per module and copy it per row

<!-- sq:subtask:ST2:body -->
For the tables the profile names, build the scratch squad once per module and copy it into each row's `tmp_path` instead of running a fresh init per row. `tests/_roster_squad.py` already does this; reuse that pattern rather than adding a new fixture style. Rows must stay isolated: each one mutates its own copy. Measure the before and after on the affected modules.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Move the heaviest shape tables behind the slow marker without losing gate coverage

<!-- sq:subtask:ST3:body -->
Mark the heaviest shape tables `slow`, like the scale tests in `tests/test_scale.py`, so the default run skips them. They must still run on the release gate: on one OS in CI, or in a nightly job the release checks. State in a comment which tables moved and where they now run. Only after the setup-sharing subtask, and only for tables still heavy after it.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Check xdist worker counts and runner settings on CI

<!-- sq:subtask:ST4:body -->
Confirm how many workers `-n auto` gets on each runner, and whether a larger runner, an explicit `-n`, or a different `--dist` mode helps. On Windows, check whether Defender scanning of the temp directory is in play and whether excluding the workspace temp dir is possible on the hosted runner. Record what was measured and what was changed.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Measure the write-once guard's cost, and keep it on

<!-- sq:subtask:ST5:body -->
Measure the suite with and without the write-once guard on one OS to confirm or correct the estimated 8%. The guard stays on. If the cost is real, look for a cheaper implementation of the same check; otherwise record the number and close this out.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T07:42:39Z] `tech-lead` Olivia Lead:
  - Left unparented: FEAT-1092 is engine layering and cohesion (REV-956 findings), not test or CI time, and no other open feature covers CI cost (FEAT-916/917 are sq runtime cost under EPIC-31). Targets MILE-1051 directly. Filed at op-pierre's request on 2026-10-17.
- [2026-10-17T07:55:40Z] `op-pierre` Pierre Chat:
  - 2026-10-17: a speed boost is not enough. We need another complete rebuild of the test suite, from the ground up.
- [2026-10-17T07:57:07Z] `product-owner` Nina Product:
  - Linked FEAT-1096 (complete test-suite rebuild, per op-pierre 2026-10-17). This task's profiling and setup-sharing work is one input to it.
<!-- sq:discussion:end -->
