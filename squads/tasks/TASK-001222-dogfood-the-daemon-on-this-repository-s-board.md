---
id: TASK-1222
sequence_id: 1222
type: task
title: Dogfood the daemon on this repository's board
status: Draft
parent: FEAT-1140
author: tech-lead
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
  maps_to: US8
- local_id: ST2
  title: Trial with SQUADS_DAEMON=on and record the result
  status: Todo
  maps_to: US8
- local_id: ST3
  title: Live check of remote timeouts and Ctrl-C
  status: Todo
  maps_to: US3
created_at: '2026-10-28T14:08:45Z'
updated_at: '2026-10-30T00:33:02Z'
priority: medium
---
<!-- sq:body -->
## Goal

Run the daemon on this repository's own board (FEAT-1140 US8): committed off first, trialled in-session with `SQUADS_DAEMON=on`, and enabled here only once the trial result is on the record.

## What it builds

- This repository's `.squads.toml` sets `[daemon] enabled = false`, and the contributor documentation (not the adopter docs) states the switch-on step: `SQUADS_DAEMON=on` for a trial session, then `enabled = true` once trusted. A development checkout keeps its daemon off.
- A trial on a pre-release build installed as the uv tool (op-pierre, 2026-10-28), never the dev tree: a stretch of the team's normal board work (reads, creates, comments including a confirmed `comment remove`, transitions, a `repair` and a `renumber` dry run, concurrent agents), plus `sq ui` browsing through the daemon, an edit of the workflow override mid-session (the daemon retires and the next command and the TUI pick up the new configuration) and a `sq daemon stop` while `sq ui` is open. Recorded as a comment on this task: what ran, for how long, and any stale read, lost write, wrong refusal or stuck process found, each filed as a bug.
- A live check of the remote client's timeouts (ST3): the 10 s waiting notice on a long operation, the 300 s answer timeout, and a timeout or Ctrl-C ending only the client's wait, with the daemon finishing the operation and nothing replayed. It replaces an automated test (op-pierre, 2026-10-29).
- The decision to enable the daemon by default here is the operator's, taken on that record.
- **Before the trial (ST2):** the pre-release build runs schema 0.19 (ADR-1250 section 8), and a package refuses a squad at another schema, so this repository's squad must be brought to 0.19 first. That migration is the operator's call (CLAUDE.md, "A schema hard-stop is the operator's call"), run with the tree committed beforehand; once it has run, every agent working on this board needs a 0.19 build. ST1 does not wait for it: committing `[daemon] enabled = false` is safe for the installed 0.17.0 tool and for 0.18.0, whose `SquadsConfig` ignores keys it does not know (read in both sources on 2026-10-30).

## Acceptance

FEAT-1140 US3, the timeout and Ctrl-C bullets, checked live and recorded (ST3). FEAT-1140 US8 in full: `enabled = false` committed with a documented switch-on step; trial via `SQUADS_DAEMON=on` with nothing committed until the result is recorded; no stale reads, lost writes or stuck processes in the trial; result recorded before enabling.

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
Once this repository's squad is at the pre-release build's schema (see the task body), normal board work through the pre-release build installed as the uv tool with `SQUADS_DAEMON=on`, never the dev tree, including a confirmed `comment remove`, `sq ui` browsing through the daemon, an override edit mid-session and a `sq daemon stop` while `sq ui` is open. A manual trial, not a suite test: between steps compare a daemon `--json` read with the same read under `SQUADS_DAEMON=off`; afterwards `sq repair` has nothing to fix, `sq check` is clean and `sq daemon status --json` reports none running after `sq daemon stop`. Record the commands and result as a comment; file each defect as a bug; enabling by default here is the operator's call.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Live check of remote timeouts and Ctrl-C

<!-- sq:subtask:ST3:body -->
Live check of the remote client's timeouts, replacing an automated test (op-pierre, 2026-10-29, FEAT-1140 comment 20c1d4d; ADR-1225 section 3, "Timeouts"). Run on POSIX (WSL2 or macOS) with the pre-release build installed as the uv tool, on a scratch squad outside this repository (`sq init` in a fresh directory nested under the scratchpad, with a few items), `SQUADS_DAEMON=on` in the session. The daemon's pid comes from `sq daemon status --json`. A paused daemon (`kill -STOP <pid>`) accepts the connection but answers nothing until `kill -CONT <pid>`, which is how each case is provoked.

1. **Waiting notice on a long operation.** Pause the daemon, run `sq repair` (timeout class `long`). After 10 s, stderr shows `waiting for the daemon (<operation>)…` once and the client keeps waiting with no answer timeout. Resume after about 60 s: `repair` prints its normal report and exit code.
2. **Answer timeout on an ordinary call.** Pause the daemon, run a write such as `sq task <n> comment -m "timeout probe" --as qa`. After 300 s (time it), stderr shows `error: no answer from the squad served at <endpoint> after 300 s; the operation may still complete. Check its result before running it again.` and the exit code is 1. Resume the daemon: `sq task <n> show --json` shows the probe comment exactly once, so the operation finished and was not replayed or run locally.
3. **Ctrl-C.** Pause the daemon, run another write, press Ctrl-C after a few seconds. Stderr shows the same sentence without the duration and the exit code is 130. Resume: the write is present exactly once.
4. **Connect timeout is not an answer timeout.** Stop the daemon (`sq daemon stop`), make the runtime directory unusable (`chmod 000` on it), and run a read: it runs locally with ADR-1052's one stderr line and no timeout message. Restore the mode.

Afterwards `sq repair` has nothing to fix, `sq check` is clean, and `sq daemon status --json` reports none running after `sq daemon stop`. Record each case as a comment on this task: the exact commands, the measured times, the stderr text and exit codes, and the `show --json` evidence. File each difference from the expected text or behaviour as a bug. Native Windows has no SIGSTOP; check case 1 there only if a squad big enough to make `repair` run past 10 s is at hand, and say so in the record.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T18:23:38Z] `op-pierre` Pierre Chat:
  - The dogfood trial runs on a pre-release build installed as the uv tool, so it is recorded before the daemon is enabled on this board.
- [2026-10-29T06:54:53Z] `tech-lead` Olivia Lead:
  - ST3 added per op-pierre 20c1d4d: live check of the 10 s waiting notice, the 300 s answer timeout and Ctrl-C, provoked by pausing the daemon with SIGSTOP on a scratch squad, results recorded here. @qa
- [2026-10-30T00:33:02Z] `tech-lead` Olivia Lead:
  - Brought up to date (2026-10-30): the ST2 trial needs this squad at schema 0.19 first (the pre-release build refuses 0.17), and that migration is the operator's call (open on FEAT-1140). ST1 is safe now: 0.17.0 and 0.18.0 ignore the `[daemon]` table.
<!-- sq:discussion:end -->
