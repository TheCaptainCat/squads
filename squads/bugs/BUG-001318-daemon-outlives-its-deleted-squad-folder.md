---
id: BUG-1318
sequence_id: 1318
type: bug
title: Daemon outlives its deleted squad folder
status: Open
author: qa
description: Nothing checks that the squad folder still exists; only the idle timer
  ends a daemon.
created_at: '2026-11-05T09:24:19Z'
updated_at: '2026-11-05T09:24:19Z'
severity: medium
---
<!-- sq:body -->
## Steps
1. In scratch squads A (`[daemon] idle_timeout_minutes = 0`) and B (default 30), run one command each so a daemon starts. `sq daemon status` showed "exits idle at: never" for A and +30 min for B. (driven)
2. `rm -rf` both squad folders without stopping the daemons. (driven)
3. Watch the processes for about 4 minutes. (driven)

## Expected
A daemon whose squad folder is gone exits (it has nothing left to serve).

## Actual
- Both `daemon run` processes were still alive after 4 minutes; `/proc/<pid>/cwd -> .../b2a (deleted)`. Their socket, lock, json and log files stayed in `/run/user/1000/squads/`. (driven)
- A was configured to never idle out, so it can never leave on its own. (driven)
- B, with the default timeout, left alive for the 4 minutes watched. I did not wait the full 30 minutes. (driven up to 4 min)
- I killed both by pid at the end and confirmed no process remained. (driven)

## Cause
- The only exit conditions are a stop request, a retirement and the idle timer (`_daemon/_lifecycle.py`: `_watch_idle`, `_idle_deadline`). Nothing checks that `endpoint.squad_dir` or `.squads.toml` still exists. (read)
- Retirement runs only inside a request (`_daemon/_app.py`, `except Retiring`). `fingerprint()` would change once the config is absent, but nothing triggers the check without a request. (read)
- The idle timer restarts on every request (`Activity.end`). A client that polls a deleted folder, or idle_timeout 0, keeps the daemon alive for good. That is what I infer kept the canary daemons up past an hour; I did not reproduce the polling. (inferred)

## Suggested direction
Have `_watch_idle` also check, at its 5 s tick or at a slower interval, that `.squads.toml` and the squad dir still exist, and stop the daemon when they do not.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
