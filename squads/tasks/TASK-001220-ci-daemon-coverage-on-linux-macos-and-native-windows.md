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
- ADR-1225:implements
description: Cross-process set, mode-parity run and budget report on the three-OS
  matrix, leaked-daemon check, bounded time
subentities:
- local_id: ST1
  title: Cross-process and parity jobs on the three-OS matrix
  status: Todo
  story: US6
- local_id: ST2
  title: Leaked-daemon check and bounded wall time
  status: Todo
  story: US6
- local_id: ST3
  title: Client-budget report job
  status: Todo
  story: US12
created_at: '2026-10-28T14:08:43Z'
updated_at: '2026-10-28T22:25:58Z'
---
<!-- sq:body -->
## Goal

Make the daemon's cross-platform promise visible in CI: the cross-process set, the surface suite in remote mode and a client-budget report run on the existing Linux, macOS and Windows matrix of `.github/workflows/test.yml`, with native Windows a first-class target. Native Windows is reached only through the CI runner here, so this is where its acceptance is proven (FEAT-1140 US6).

## What it builds

- **Cross-process job on the three runners.** Exactly the members ADR-1172 "The cross-process set" names (implicit start, discovery, fall back, no replay, Ctrl-C, detached spawn on Windows), written in TASK-1219 ST2, ST3 and ST5, running the real `sq` console script on `ubuntu-latest`, `macos-latest` and `windows-latest`.
- **Mode-parity job per OS.** The surface suite rerun with `HttpApi` against the daemon's application served in-process (TASK-1219 ST6, ADR-1225 section 5), under ADR-1172's time bound: 10 minutes, 15 on Windows where the run is the full suite.
- **Client-budget report.** The benchmark script of TASK-1219 ST8 runs on one runner and its numbers are published as a job summary; it never fails the build, because runner timings spread too widely to gate on (ADR-1225 section 5). The budget's import guard runs with `tests/meta` in the ordinary jobs.
- **No stray daemons.** Every job sets `SQUADS_DAEMON=off` at job level except where a test turns it on; a post-test step fails the job if any `squads daemon run` process outlives the test step, printing its runtime-directory log.
- `starlette` and `uvicorn` are ordinary dependencies, so the install step needs no extra; check the lock resolves on all three runners.
- Report each job's time on two runs per OS against the ADR-1172 bound.
- No new test cases: this task adds jobs that run the tests TASK-1218 and TASK-1219 write.

## Acceptance

- FEAT-1140 US6: the cross-process members and the surface suite in both modes pass on native Windows (idle exit is not tested, ADR-1052 point 11).
- FEAT-1140 US3, last bullet: the surface suite runs in remote mode in its own CI job and passes. US12: CI runs the budget measurement as a report.
- Feature acceptance: "The same behaviour holds on Linux, macOS and native Windows."
- A daemon process left running after tests fails the job on every OS.
- Every job within ADR-1172's time bound on two runs per OS.

## Test approach

- Prove the leak check with a deliberately leaked daemon on a throwaway branch: the job fails on each OS, then passes once removed.
- Prove the Windows coverage is real: the Windows jobs' collected test IDs include the Windows-only cases (the Windows CLI port's admission case, the detached-spawn member), with zero skips in the daemon modules, or an explicit list of the POSIX-only skips.
- New tests: 0.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1220 add-subtask "<title>"`; track with `sq task 1220 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Cross-process and parity jobs on the three-OS matrix

<!-- sq:subtask:ST1:body -->
A cross-process job on `ubuntu-latest`, `macos-latest` and `windows-latest` in `.github/workflows/test.yml`, running exactly the members ADR-1172 "The cross-process set" names (implicit start, discovery, fall back, no replay, Ctrl-C, detached spawn on Windows), written in TASK-1219 ST2, ST3 and ST5; and a mode-parity job per OS rerunning the surface suite with `HttpApi` against the in-process application (TASK-1219 ST6). Show that the Windows jobs collect the Windows-only cases with no silent skip.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Leaked-daemon check and bounded wall time

<!-- sq:subtask:ST2:body -->
Job-level `SQUADS_DAEMON=off` plus a post-test step that fails when a `squads daemon run` process survives, printing its log; prove it with a deliberate leak on a throwaway branch. Every job, the parity and cross-process jobs included, under ADR-1172's time bound (10 minutes; 15 for Windows, where the parity run is the full suite); report two runs per OS.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Client-budget report job

<!-- sq:subtask:ST3:body -->
The benchmark script of TASK-1219 ST8 run on one runner as a report: the human and `--json` medians of 31 interleaved runs of `sq <type> <n> show`, client overhead (wall time minus `Server-Timing`), published in the job summary. Never a gate (ADR-1225 section 5); the release criterion is the measurement on the reference host recorded by the release runbook.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
