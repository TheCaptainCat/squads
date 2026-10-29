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
- ADR-1225:implements
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
updated_at: '2026-10-28T22:26:06Z'
---
<!-- sq:body -->
## Goal

Run the daemon on this repository's own board (FEAT-1140 US8): committed off first, trialled in-session with `SQUADS_DAEMON=on`, and enabled here only once the trial result is on the record.

## What it builds

- This repository's `.squads.toml` sets `[daemon] enabled = false`, and the contributor documentation (not the adopter docs) states the switch-on step: `SQUADS_DAEMON=on` for a trial session, then `enabled = true` once trusted. A development checkout keeps its daemon off.
- A trial on a pre-release build installed as the uv tool (op-pierre, 2026-10-28), never the dev tree: a stretch of the team's normal board work (reads, creates, comments including a confirmed `comment remove`, transitions, a `repair` and a `renumber` dry run, concurrent agents), plus `sq ui` browsing through the daemon, an edit of the workflow override mid-session (the daemon retires and the next command and the TUI pick up the new configuration) and a `sq daemon stop` while `sq ui` is open. Recorded as a comment on this task: what ran, for how long, and any stale read, lost write, wrong refusal or stuck process found, each filed as a bug.
- The decision to enable the daemon by default here is the operator's, taken on that record.

## Acceptance

FEAT-1140 US8 in full: `enabled = false` committed with a documented switch-on step; trial via `SQUADS_DAEMON=on` with nothing committed until the result is recorded; no stale reads, lost writes or stuck processes in the trial; result recorded before enabling.

## Test approach

A manual trial, not a suite test: between trial steps, compare a daemon answer with a local answer (`SQUADS_DAEMON=off`) for the same `--json` read; afterwards `sq repair` reports nothing to fix, `sq check` is clean, and `sq daemon status --json` reports none running once `sq daemon stop` returns. Record the commands run in the result comment. New tests: 0.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1222 add-subtask "<title>"`; track with `sq task 1222 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Commit enabled = false and the switch-on step

<!-- sq:subtask:ST1:body -->
Set `[daemon] enabled = false` in this repository's `.squads.toml` and document in contributor documentation: the switch-on step (`SQUADS_DAEMON=on` trial, then `enabled = true`), that a daemon started from a development checkout serves the code it started with until `sq daemon stop`, and that `SQUADS_DAEMON=off` keeps a session in local mode. Nothing detects an editable install (ADR-1052 point 13). `sq check` stays clean.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Trial with SQUADS_DAEMON=on and record the result

<!-- sq:subtask:ST2:body -->
Normal board work through the pre-release build installed as the uv tool with `SQUADS_DAEMON=on`, never the dev tree, including a confirmed `comment remove`, `sq ui` browsing through the daemon, an override edit mid-session and a `sq daemon stop` while `sq ui` is open. A manual trial, not a suite test: between steps compare a daemon `--json` read with the same read under `SQUADS_DAEMON=off`; afterwards `sq repair` has nothing to fix, `sq check` is clean and `sq daemon status --json` reports none running after `sq daemon stop`. Record the commands and result as a comment; file each defect as a bug; enabling by default here is the operator's call.
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
