---
id: TASK-1220
sequence_id: 1220
type: task
title: 'CI: daemon coverage on Linux, macOS and native Windows'
status: Draft
parent: FEAT-1140
author: tech-lead
priority: high
refs:
- ADR-1052:implements
- TASK-1218:depends-on
- TASK-1219:depends-on
description: Daemon and remote-mode tests on the three-OS matrix, leaked-daemon check,
  bounded Windows wall time
subentities:
- local_id: ST1
  title: Daemon tests on the three-OS matrix, Windows first-class
  status: Todo
  story: US6
- local_id: ST2
  title: Leaked-daemon check and bounded wall time
  status: Todo
  story: US6
created_at: '2026-10-28T14:08:43Z'
updated_at: '2026-10-28T19:17:59Z'
---
<!-- sq:body -->
## Goal

Make the daemon's cross-platform promise visible in CI: the daemon and remote-mode tests run on the existing Linux, macOS and Windows matrix of `.github/workflows/test.yml`, with native Windows treated as a first-class target, not an afterthought. Native Windows is reached only through the CI runner here, so this is where its acceptance is proven.

## What it builds

- **Cross-process job on the three runners.** Exactly the members ADR-1172 "The cross-process set" names (implicit start, discovery, fall back, no replay, Ctrl-C, detached spawn on Windows), written in TASK-1219, running the real `sq` console script on `ubuntu-latest`, `macos-latest` and `windows-latest`.
- **The CLI surface suite in remote mode** (TASK-1219's parity run) as its own job per OS, under ADR-1172's time bound (10 minutes; 15 for Windows, where the remote-mode run is the full suite).
- **No stray daemons.** Every job sets `SQUADS_DAEMON=off` at job level except where a test turns it on; a post-test step fails the job if any `squads daemon run` process outlives the test step, printing its runtime-directory log.
- Report each job's time on two runs per OS, against the ADR-1172 bound.
- No new test cases: this task adds jobs that run the tests TASK-1218 and TASK-1219 write.

## Acceptance

- US6: the cross-process members and the surface suite in both modes pass on native Windows (idle exit is not tested, ADR-1052 point 11).
- Feature acceptance: "The same behaviour holds on Linux, macOS and native Windows."
- A daemon process left running after tests fails the job on every OS.
- Every job within ADR-1172's time bound on two runs per OS.

## Test approach

- Prove the leak check with a deliberately leaked daemon on a throwaway branch: the job fails on each OS, then passes once removed.
- Prove the Windows coverage is real: the Windows jobs' collected test IDs include the Windows-only cases (the Windows CLI port's admission cases, the detached-spawn member), with zero skips in the daemon modules, or an explicit list of the POSIX-only skips.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1220 add-subtask "<title>"`; track with `sq task 1220 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Daemon tests on the three-OS matrix, Windows first-class

<!-- sq:subtask:ST1:body -->
A cross-process job on `ubuntu-latest`, `macos-latest` and `windows-latest` in `.github/workflows/test.yml`, running exactly the members ADR-1172 "The cross-process set" names (implicit start, discovery, fall back, no replay, Ctrl-C, detached spawn on Windows), written in TASK-1219 ST1, ST2, ST3 and ST5. Show the Windows job collects the Windows-only member with no silent skip.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Leaked-daemon check and bounded wall time

<!-- sq:subtask:ST2:body -->
Job-level `SQUADS_DAEMON=off` plus a post-test step that fails when a `squads daemon run` process survives, printing its log; prove it with a deliberate leak on a throwaway branch. The surface suite's remote-mode run (ADR-1172 "Mode parity") gets its own job per OS, under ADR-1172's time bound (10 minutes; 15 for Windows, where the remote-mode run is the full suite); report two runs per OS.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
