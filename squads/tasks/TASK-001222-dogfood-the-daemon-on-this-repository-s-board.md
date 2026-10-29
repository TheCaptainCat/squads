---
id: TASK-1222
sequence_id: 1222
type: task
title: Dogfood the daemon on this repository's board
status: Draft
parent: FEAT-1140
author: tech-lead
priority: medium
refs:
- ADR-1052:implements
- TASK-1219:depends-on
- TASK-1220:depends-on
description: enabled = false committed with a switch-on step, SQUADS_DAEMON=on trial,
  result recorded before enabling
subentities:
- local_id: ST1
  title: Commit enabled = false and the switch-on step
  status: Todo
  story: US8
- local_id: ST2
  title: Trial with SQUADS_DAEMON=on and record the result
  status: Todo
  story: US8
created_at: '2026-10-28T14:08:45Z'
updated_at: '2026-10-28T18:23:38Z'
---
<!-- sq:body -->
## Goal

Run the daemon on this repository's own board (US8): committed off first, trialled in-session with `SQUADS_DAEMON=on`, and enabled here only once the trial result is on the record.

## What it builds

- This repository's `.squads.toml` sets `[daemon] enabled = false`, and the contributor documentation (not the adopter docs) states the switch-on step: `SQUADS_DAEMON=on` for a trial session, then `enabled = true` once trusted. A development checkout keeps its daemon off.
- A trial: a stretch of the team's normal board work (reads, creates, comments, transitions, a `repair` and a `renumber` dry run, concurrent agents) run through the released or pre-release-installed tool with `SQUADS_DAEMON=on`, never through the dev tree. Recorded as a comment on this task: what ran, for how long, and any stale read, lost write or stuck process found (each one filed as a bug).
- The decision to enable the daemon by default here is the operator's, taken on that record.

## Acceptance

US8 in full: `enabled = false` committed with a documented switch-on step; trial via `SQUADS_DAEMON=on` with nothing committed until the result is recorded; no stale reads, lost writes or stuck processes in the trial; result recorded before enabling.

## Test approach

Between trial steps, compare a daemon answer with a local answer (`SQUADS_DAEMON=off`) for the same read; after the trial, `sq repair` reports nothing to fix, `sq check` is clean, and no `squads daemon run` process is left once `sq daemon stop` returns.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1222 add-subtask "<title>"`; track with `sq task 1222 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Commit enabled = false and the switch-on step

<!-- sq:subtask:ST1:body -->
Set `[daemon] enabled = false` in this repository's `.squads.toml` and document the switch-on step (`SQUADS_DAEMON=on` trial, then `enabled = true`) in contributor documentation. `sq check` stays clean.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Trial with SQUADS_DAEMON=on and record the result

<!-- sq:subtask:ST2:body -->
Normal board work through the installed tool with `SQUADS_DAEMON=on`, never the dev tree; compare daemon and local answers between steps; afterwards `sq repair` has nothing to fix, `sq check` is clean and no daemon process survives `sq daemon stop`. Record the result as a comment; file each defect as a bug; enabling by default here is the operator's call.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T18:23:38Z] `op-pierre` Pierre Chat:
  - The dogfood trial runs on a pre-release build installed as the uv tool, so it is recorded before the daemon is enabled on this board.
<!-- sq:discussion:end -->
