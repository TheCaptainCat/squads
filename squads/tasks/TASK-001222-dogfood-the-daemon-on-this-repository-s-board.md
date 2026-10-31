---
id: TASK-1222
sequence_id: 1222
type: task
title: Dogfood the daemon on this repository's board
status: InReview
parent: FEAT-1140
author: tech-lead
refs:
- ADR-1052:implements
- TASK-1219:depends-on
- TASK-1220:depends-on
- ADR-1225:implements
- TASK-1264:depends-on
- TASK-1263:depends-on
description: enabled = false committed with a switch-on step, SQUADS_DAEMON=on trial,
  result recorded before enabling
subentities:
- local_id: ST1
  title: Commit enabled = false and the switch-on step
  status: Todo
  maps_to: US8
- local_id: ST2
  title: Trial with SQUADS_DAEMON=on and record the result
  status: Done
  assignee: qa
  maps_to: US8
- local_id: ST3
  title: Live check of remote timeouts and Ctrl-C
  status: Done
  assignee: qa
  maps_to: US3
created_at: '2026-10-28T14:08:45Z'
updated_at: '2026-10-31T08:31:46Z'
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

## Under ADR-1261

The trial and the live checks run against the shim and the command endpoint (TASK-1262, TASK-1263, TASK-1264), not the earlier `HttpApi` CLI. ST2 adds to the board work: a `comment remove` confirmed through the two prompt phases, a Tab completion, `--help`, a `--file -` write, and `check` timed cold and warm (the parse cache). ST3's cases apply to the shim's answer timeouts as TASK-1264 ST4 builds them; take the exact texts from the shipped code, not from this body.
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
- [2026-10-30T20:32:51Z] `tech-lead` Olivia Lead:
  - - Stays Draft and gated on the operator's go (2026-10-30): the trial needs this squad at schema 0.19, which is op-pierre's call. Now depends on TASK-1264 and TASK-1263 as well; the body gains the ADR-1261 additions to the trial. @manager
- [2026-10-30T20:50:17Z] `op-pierre` Pierre Chat:
  - The dogfood trial waits until the ADR-1261 architecture (TASK-1262 to TASK-1266) is delivered (2026-10-30).
- [2026-10-31T08:17:58Z] `op-pierre` Pierre Chat:
  - Go for the dogfood (2026-10-31): this repository's squad switches to daemon mode.
- [2026-10-31T08:30:28Z] `qa` Mara Tester:
  - Trial result (qa, 2026-10-31), installed 0.19.0 uv-tool build with the shim against this repository's own squad (daemon enabled by the operator, 9fc0d2a5), host load average 0.4 to 1.8 on 14 cores. Overall: no stale read, lost write, wrong refusal or stuck process found; no bug filed. Untested items are listed at the end.
    
    | # | What I ran | Result |
    |---|---|---|
    | 1 | Reads: `task 1222 show [--full --comments] [--json]`, `list --json`, `board list`, `tree 1140 --json`, `check --json`, `mine`, `inbox`, `workflow lifecycles`, `docs`, `--help`, `task --help`, `daemon status --json`, plus 5 error cases (unknown subtask, bad status, unknown command, bad hash, missing item), each daemon vs `SQUADS_DAEMON=off` | stdout, stderr and exit code identical (15 reads, 5 errors). One `list --json` differed only by another agent's `updated_at` on TASK-1267 written between the two runs; rerun twice per mode gave 4 identical files. `COLUMNS=60` and `NO_COLOR` forms identical too |
    | 2 | Writes: `task 1222 comment -m`, `--file -` with a backtick, 8 parallel comments (4 daemon + 4 local at once), 6 alternating daemon/local writes each followed by a read in both modes | all visible at once in both modes (6 of 6 alternations, 8 of 8 parallel); no lost write |
    | 3 | `task 1222 subtask 2 body --append --file F` (backticks, `[x]`), `--file -` through the daemon and in local mode, missing file in both modes | all applied, read back intact; missing file gives the same `error: cannot read file '/nonexistent.md'` and exit 1 in both modes; no stray `</content>` |
    | 4 | Subtask status moves: ST2 and ST3 Todo to InProgress (assignee qa) | applied |
    | 5 | `comment <hash> remove --as qa` in a pty, answer `n` | prompt `Remove this comment? [y/N]:`, `Aborted.`, exit 1, comment still present |
    | 6 | Same, answer `y` | removed, exit 0, gone in a later read |
    | 7 | Same, with the comment edited from another process between question and answer | `error: no comment 7fab8bc in TASK-1222's discussion (edited or removed since it was read?)`, exit 1, nothing removed. The documented re-ask on a changed screen was not reached, because an edit changes the hash |
    | 8 | Completion: bash `_SQ_COMPLETE=complete_bash COMP_WORDS="sq task 1222 " COMP_CWORD=3`, partial `sub`, `sq ta`, zsh `complete_zsh`, `source_bash` | the 14 sub-verbs listed; identical md5 daemon vs local for bash and zsh; 53 ms |
    | 9 | `daemon status`, `stop`, `stop --json`, status when none, next command | `daemon stopped`; `none running` rc 0; `{"was_running": false}`; the next `show` started a fresh daemon (1.07 s) |
    | 10 | Whitespace line appended to `.squads.toml`, then a command, then revert | the command ran in local mode (883 ms), the old pid exited, the next command (910 ms) started a new daemon; file restored byte for byte (same sha256, `git diff` empty) |
    | 11 | Interleaved terminals: daemon writer + local reader and the reverse | see rows 2 and 10; plus `sq repair --json` through the daemon and locally: same bytes, `missing/unreadable/renumbered` all empty |
    | 12 | ST3 case 1: `kill -STOP` the daemon of a scratch squad (outside the repository, `SQUADS_DAEMON=on`), `sq repair`, resume at 60 s | stderr `waiting for the daemon (squad.repair)…` once at 10.0 s; after resume `rebuilt index: 4 items, counter=4`, exit 0 |
    | 13 | ST3 case 2: paused daemon, `task 2 comment -m "timeout probe" --as manager` | after 300.1 s stderr `error: no answer from the squad served at /run/user/1000/squads/ba7ea6bc073c.sock after 300 s; the operation may still complete. Check its result before running it again.`, exit 1 (300.2 s total); after resume `show --comments` and `show --json` carry the probe exactly once |
    | 14 | ST3 case 3: paused daemon, write in a pty, Ctrl-C at 4 s | same sentence without the duration, ended at once, exit 130; the write present exactly once after resume |
    | 15 | ST3 case 4: daemon stopped, runtime directory `chmod 000` (done on a private `XDG_RUNTIME_DIR`, not the shared `/run/user/1000/squads`), `task 2 show` | `warning: the daemon could not be used (cannot create …/rt/squads: Permission denied); running locally. Set SQUADS_DAEMON=off or enabled = false …`, ran locally, exit 0, no timeout message; mode restored, directory removed |
    | 16 | After: `sq repair`, `sq check`, `daemon status --json` after `daemon stop` | repair nothing to fix; `check` "no issues"; `{"running": false, "daemon": null}` |
    
    Timings (ms, wall clock of the whole command, python `perf_counter`, uv tool build):
    
    | Command | Daemon | Local (`SQUADS_DAEMON=off`) |
    |---|---|---|
    | `task 1222 show`, cold (no daemon, includes the start) | 969, 1067, 883 to 910 after a retire | |
    | `task 1222 show`, warm | 95 to 182 (n=5, median 108) | 568 to 670 (n=3) |
    | `task 1222 show --full --comments`, warm | 163, 163 | |
    | `check`, cold daemon (start + empty parse cache) | 3907 | |
    | `check`, warm | 3094 (first after the start), then 1831, 1567, 1752 | 7220, 6851 |
    | bash completion | 53 | |
    
    Not tested, or only partly: `sq ui` (the uv-tool build has no `tui` extra: `error: the sq ui terminal UI needs the optional 'tui' extra`, so browsing through the daemon and a stop while it is open were not run); a real interactive Tab in zsh (a pty session was inconclusive; only the completion protocol in both shells was checked); the changed-screen re-ask of a confirmed removal (row 7); `renumber` dry run; native Windows.
    
    Observations, not defects: (a) the 16 trial comments I wrote on this task were not removed. My cleanup loop was blocked by a safety check, so they stay for the operator or the author to remove: they start with "trial probe", "interleave", "par " and "cmt via stdin". (b) With `enabled = true` here, a dev-tree `uv run sq` or a worktree build starts its own daemon on this squad: I saw two (the repository `.venv` and `.claude/worktrees/agent-*`) beside the uv-tool one, each serving the code it started with. It is the documented behaviour, but it now applies to every contributor session in this checkout, so SQUADS_DAEMON=off for dev-tree runs may be worth stating in the contributor notes (ST1). (c) I did not touch ST1.
<!-- sq:discussion:end -->
