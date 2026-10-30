---
id: TASK-1220
sequence_id: 1220
type: task
title: 'CI: daemon coverage on Linux, macOS and native Windows'
status: InReview
parent: FEAT-1140
author: tech-lead
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
  status: Done
  maps_to: US6
- local_id: ST2
  title: Leaked-daemon check and bounded wall time
  status: Done
  maps_to: US6
- local_id: ST3
  title: Client-budget report job
  status: Done
  maps_to: US12
created_at: '2026-10-28T14:08:43Z'
updated_at: '2026-10-30T08:03:28Z'
priority: high
---
<!-- sq:body -->
## Goal

Make the daemon's cross-platform promise visible in CI: the cross-process set, the surface suite in remote mode and a client-budget report run on the existing Linux, macOS and Windows matrix of `.github/workflows/test.yml`, with native Windows a first-class target. Native Windows is reached only through the CI runner here, so this is where its acceptance is proven (FEAT-1140 US6).

## What it builds

- **The pattern to follow** is the `override-squad` job already in `.github/workflows/test.yml`: a job of its own, the same checkout (`fetch-depth: 0`), `setup-python`, `setup-uv` and `uv sync --frozen --all-extras` steps, and one `pytest` line whose option selects the run (`--squad override tests/cli` there). The new jobs differ only in that line and in their matrix.
- **Cross-process set.** The `cross-process` job already exists (three OS, `uv run pytest -n0 tests/cross_process`, the index lock cases), and the ordinary `test` job already passes `--ignore=tests/cross_process`. The daemon's members ADR-1172 names (implicit start, discovery, fall back, no replay, Ctrl-C, detached spawn on Windows), written by TASK-1219 lane C in `tests/cross_process/`, join it with no new job. Its Windows timeout (15 minutes today) comes down to ADR-1172's 10, since it does not run the full suite.
- **Four remote-mode jobs** (ADR-1172 "Mode parity" and "Time bound", amended 2026-10-30): `tests/cli` in remote mode on the bundled squad on `ubuntu-latest`, `macos-latest` and `windows-latest`, and with `--squad override` on `ubuntu-latest`, each with `timeout-minutes: 10`, Windows included. The 15-minute bound stays only for the Windows `test` job that runs the full suite. The override job is the only run whose vocabulary hash covers a present workflow override and that sends custom fields, kinds and attributes over the wire.
- **Client-budget report.** The benchmark script of TASK-1219 ST8 runs on one runner and its numbers are published as a job summary; it never fails the build, because runner timings spread too widely to gate on (ADR-1225 section 5). The budget's import guard runs with `tests/meta` in the ordinary jobs.
- **No stray daemons.** Every job, the existing `test` and `override-squad` included, sets `SQUADS_DAEMON=off` at job level except where a test turns it on; a post-test step fails the job if any `squads daemon run` process outlives the test step, printing its runtime-directory log.
- `starlette` and `uvicorn` are ordinary dependencies, so the install step needs no extra; check the lock resolves on all three runners.
- Report each job's time on two runs per OS against the ADR-1172 bound. The workflow runs on pushes and pull requests to `main` and on `workflow_dispatch`, so the timing runs on the release branch are dispatched by hand.
- No new test cases: this task adds jobs that run the tests TASK-1218 and TASK-1219 write.
- Only `.github/workflows/test.yml` changes, so this task shares no file with the development tasks and starts once TASK-1219's options exist.

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
Four remote-mode jobs in `.github/workflows/test.yml`, each in the `override-squad` job's shape with its own `pytest` line and `timeout-minutes: 10`: `tests/cli` in remote mode on the bundled squad on `ubuntu-latest`, `macos-latest` and `windows-latest`, and with `--squad override` on `ubuntu-latest` (TASK-1219 ST6). The daemon's cross-process members join the existing `cross-process` job through `tests/cross_process/`; its Windows timeout comes down from 15 to 10 minutes (ADR-1172 "Time bound"). Show that the Windows jobs collect the Windows-only cases with no silent skip.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Leaked-daemon check and bounded wall time

<!-- sq:subtask:ST2:body -->
Job-level `SQUADS_DAEMON=off` plus a post-test step that fails when a `squads daemon run` process survives, printing its log; prove it with a deliberate leak on a throwaway branch. Every job, the existing `test` and `override-squad` jobs and the remote-mode and cross-process jobs included, under ADR-1172's time bound (10 minutes on every OS, 15 only for the Windows `test` job that runs the full suite); report two runs per OS, dispatched by hand on the release branch.
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
- [2026-10-30T00:33:00Z] `tech-lead` Olivia Lead:
  - Brought up to date (2026-10-30): the new jobs follow the `override-squad` job pattern. Added remote mode on the override squad (pending the operator) and the Windows remote-run scope (pending the architect); both are on FEAT-1140. The existing jobs get `SQUADS_DAEMON=off` and the leak check. Timing runs are dispatched by hand on the release branch. Still 0 new tests.
- [2026-10-30T00:44:18Z] `tech-lead` Olivia Lead:
  - Folded the 2026-10-30 rulings: four remote-mode `tests/cli` jobs (bundled on ubuntu, macOS and Windows; override on ubuntu), each at 10 min. The existing `cross-process` job takes the daemon members, and its Windows timeout drops from 15 to 10 min per ADR-1172.
- [2026-10-30T08:03:16Z] `devops` Hugo Ops:
  - @manager `.github/workflows/test.yml` is edited in the working tree (not committed); no other file changed.
    - Jobs: `remote-mode` (matrix ubuntu, windows, macos; `pytest -rs --api-mode remote tests/cli`, 10 min on all three), `remote-mode-override` (ubuntu, `--api-mode remote --squad override tests/cli`, 10 min), `client-budget` (ubuntu, `continue-on-error`, runs `scripts/bench_remote_client.py` on a copy of the repo squad, medians to `$GITHUB_STEP_SUMMARY`, never gates). `cross-process` keeps its three-OS matrix; its Windows timeout was already 10, so no change, and `-rs` lists the skips. The Windows `test` job keeps 15 minutes.
    - `SQUADS_DAEMON=off` at job level on `test`, `override-squad`, `remote-mode`, `remote-mode-override`. Left unset on `cross-process` (its members start daemons) and `client-budget` (it needs one).
    - Leak check: a final `if: always()` step on every job except lint. It lists processes (`ps` or PowerShell `Get-CimInstance Win32_Process`) ending in `daemon run`, plus `*.json`/`*.sock` in the runtime directory from `squads._endpoint.runtime_directory` (it prints the `*.log` files too), and fails if either is found. Checked locally on Linux: it exits 0 on a clean box and 1 with a live daemon, naming the process and files.
    - Local counts: `tests/cli` collects 997 tests in each of local, remote and remote-override mode. `scripts/bench_remote_client.py` exists only in a worktree, not on release/0.19 yet, so `client-budget` fails (harmlessly) until TASK-1219 ST8 merges.
    - Not done: the throwaway-branch deliberate-leak proof, the Windows collected-ID check and the two timing runs per OS. They need CI.
    - Timing on release/0.19: push and PR triggers are main-only, so push the branch and run `gh workflow run test.yml --ref release/0.19`, or use Actions > test > Run workflow with the branch chosen. Do it twice, then read each job's duration with `gh run view <id> --json jobs`.
<!-- sq:discussion:end -->
