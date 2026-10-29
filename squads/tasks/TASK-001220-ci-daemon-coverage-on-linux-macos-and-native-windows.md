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
updated_at: '2026-10-28T14:09:59Z'
---
<!-- sq:body -->
## Goal

Make the daemon's cross-platform promise visible in CI: the daemon and remote-mode tests run on the existing Linux, macOS and Windows matrix of `.github/workflows/test.yml`, with native Windows treated as a first-class target, not an afterthought. Native Windows is reached only through the CI runner here, so this is where its acceptance is proven.

## What it builds

- **Daemon coverage on all three runners.** The daemon tests (lifecycle, admission, parity against a real spawned daemon) run on `ubuntu-latest`, `macos-latest` and `windows-latest`. On Windows they exercise the detached spawn flags, the loopback CLI port, `%LOCALAPPDATA%` runtime files and lock release on process termination.
- **No stray daemons.** The jobs run with `SQUADS_DAEMON=off` at the job level as well as through the test suite's own setting, and a post-test step fails the job if any `squads daemon run` process outlives the test step, printing its runtime-directory log.
- **Wall time kept in check.** The Windows job already dominates CI time; the remote-mode parity tests are placed so they do not double it (a separate job or marker selection, decided with the parity harness the forwarder task builds). Report the before and after job times.

## Acceptance

- US6: the feature's acceptance behaviours pass on native Windows, including start, discovery, idle exit and fall back.
- Feature acceptance: "The same behaviour holds on Linux, macOS and native Windows."
- A daemon process left running after tests fails the job on every OS.

## Test approach

- Prove the leak check by a deliberately leaked daemon on a throwaway branch run: the job must fail on each OS, then pass once removed.
- Prove the Windows coverage is real by checking the collected test IDs on the Windows job include the Windows-only rows (no silent skip-all): a skip count of zero for the daemon module on Windows, or an explicit list of the POSIX-only skips.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1220 add-subtask "<title>"`; track with `sq task 1220 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Daemon tests on the three-OS matrix, Windows first-class

<!-- sq:subtask:ST1:body -->
Run the daemon and remote-mode tests on `ubuntu-latest`, `macos-latest` and `windows-latest` in `.github/workflows/test.yml`; show the Windows job collects the Windows-only rows (no silent skip-all) and exercises detached spawn, the CLI port, runtime files and lock release on termination.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Leaked-daemon check and bounded wall time

<!-- sq:subtask:ST2:body -->
Job-level `SQUADS_DAEMON=off` plus a post-test step that fails when a `squads daemon run` process survives, printing its log; prove it with a deliberate leak on a throwaway branch. Place the remote-mode parity tests so the Windows job time does not double; report before and after job times.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
