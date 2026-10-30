---
id: TASK-1265
sequence_id: 1265
type: task
title: 'CI: endpoint and route parity jobs, shim budget report'
status: InProgress
parent: FEAT-1140
author: tech-lead
refs:
- ADR-1261:implements
- ADR-1172:implements
- TASK-1262:depends-on
- TASK-1264:depends-on
description: Remote-mode jobs through the command endpoint, one Linux route-parity
  job, the client-budget report on the shim's overhead
subentities:
- local_id: ST1
  title: Endpoint parity jobs and the Linux route-parity job
  status: InProgress
  maps_to: US3
- local_id: ST2
  title: Client-budget report on the shim's overhead
  status: Todo
  maps_to: US12
created_at: '2026-10-30T20:30:37Z'
updated_at: '2026-10-30T23:05:28Z'
priority: medium
---
<!-- sq:body -->
## Goal

CI for ADR-1261's test plan (point 9, and ADR-1172 "Mode parity" as ADR-1261 amends it): the remote-mode jobs run `tests/cli` through the command endpoint, one more Linux job runs it through `HttpApi` (route parity), the cross-process job carries the new members, and the client-budget report measures the shim's overhead.

## Scope

- **Endpoint parity:** the four existing remote-mode jobs (bundled squad on Linux, macOS and native Windows; override squad on Linux) keep `--api-mode remote`, which the command-endpoint task points at the endpoint. Check each still runs under ADR-1172's 10-minute bound on at least two runs, Windows included; report the timings.
- **Route parity:** one new ubuntu job, `uv run pytest --api-mode routes tests/cli`, with the "No daemon left running" step the other jobs have; bundled squad only.
- **Cross-process:** no workflow change expected; confirm the job picks up the new members on every OS and stays under the bound.
- **Client-budget report:** the `client-budget` job runs the updated `scripts/bench_remote_client.py` and puts the shim's overhead (median and p25-p75 of 31 interleaved `task <n> show` runs, plus `--json` and a completion) in the job summary against the 100 ms criterion. It stays a report (`continue-on-error`), never a gate; the release runbook reads it.

## Modules touched

`.github/workflows/test.yml` only. Any script change the report needs goes back to the shim task's developer.

## Acceptance

- Two green runs of the whole workflow on the release branch with the new job, each job under its bound; the run URLs and the budget figures recorded in a comment here.
- ADR-1261 point 9's job list and point 10's report met.

## Test approach

No new tests: CI configuration. Falsify the route job once (point it at a branch with one route's DTO field dropped, or ask for a local run that shows `--api-mode routes` turning red on it) and record it.

## Order

Depends on the command-endpoint task (the parity modes) and the shim task (the benchmark). The route-parity job can be added as soon as the endpoint task is merged; the report waits for the shim.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1265 add-subtask "<title>"`; track with `sq task 1265 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Endpoint parity jobs and the Linux route-parity job

<!-- sq:subtask:ST1:body -->
The four remote-mode jobs keep `--api-mode remote`, now through the command endpoint; one new ubuntu job runs `uv run pytest --api-mode routes tests/cli` with the "No daemon left running" step. Every job under ADR-1172's 10-minute bound on two runs, Windows included; timings reported. Can start once the command-endpoint task is merged.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Client-budget report on the shim's overhead

<!-- sq:subtask:ST2:body -->
The `client-budget` job runs the updated `scripts/bench_remote_client.py` and writes the shim's overhead (median, p25-p75 of 31 interleaved `task <n> show` runs, `--json`, a completion) to the job summary against the 100 ms criterion; it stays a report, never a gate. Waits for the shim task.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-30T22:20:44Z] `devops` Hugo Ops:
  - ST1 route job added to test.yml (worktree commit 610ee02b, unpushed): job route-parity, ubuntu, bundled squad, SQUADS_DAEMON=off, uv run pytest -rs --api-mode routes tests/cli, same No daemon left running step. The four remote-mode jobs need no change (same --api-mode remote); cross-process runs all of tests/cross_process so new members are picked up. Local -n 4 routes run: 999 passed in 67.44s. Falsification: dropping the title field from every route response made routes 224 failed, 41 errors; local stayed 999 passed; reverted, not committed. Still needed: two green CI runs of the whole workflow with per-job timings under the bound (10 min; 15 for the Windows test job), recorded here. ST2 waits for TASK-1264.
- [2026-10-30T23:05:28Z] `manager` Catherine Manager:
  - First all-green run with the route-parity job and the shim: https://github.com/TheCaptainCat/squads/actions/runs/41141368085 (e06928aa). Timings: test windows 7m47s, macOS 3m38s, ubuntu 2m8s; remote-mode windows 2m54s, macOS 1m32s, ubuntu 1m34s; remote-mode-override 1m34s; route-parity 1m22s; cross-process windows 1m35s, macOS 1m34s, ubuntu 1m24s; client-budget 0m22s.
<!-- sq:discussion:end -->
