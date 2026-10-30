---
id: TASK-1266
sequence_id: 1266
type: task
title: Docs and changelog for the shim-based remote mode
status: Done
parent: FEAT-1140
author: tech-lead
refs:
- ADR-1261:implements
- TASK-1221
- TASK-1262:depends-on
- TASK-1263:depends-on
- TASK-1264:depends-on
description: docs/daemon.md, docs/api.md, stability, faq, contributing and CHANGELOG
  brought in line with the CLI served by the daemon
subentities:
- local_id: ST1
  title: Daemon page, FAQ, stability and contributing
  status: Done
  maps_to: US9
- local_id: ST2
  title: API page and CHANGELOG
  status: Done
  maps_to: US9
created_at: '2026-10-30T20:30:38Z'
updated_at: '2026-10-30T23:45:32Z'
priority: medium
---
<!-- sq:body -->
## Goal

Bring the adopter docs and the CHANGELOG in line with the CLI's remote mode as ADR-1261 builds it: the CLI sends its command line to the daemon, which parses, runs and renders it; the resource routes stay the API for every other client. Written for an adopter, present tense, no internal tracking references.

## Scope

- **`docs/daemon.md`:** what remote mode is now (the command runs in the daemon, the output is the same code's output); which commands always run locally (`init`, `adopt`, `daemon`, `ui`); that `--help`, `docs` and shell completion are answered by the daemon too, and start one if needed; the fall back (before the command is sent, the command runs locally; after, nothing is replayed), its stderr line, Ctrl-C (exit 130) and the timeout message; prompts asked in the user's own terminal, with a removal confirmed only for the screen the user saw; the files a command names (`--file`, `-`, the import file) read by the client and sent with the command; that the daemon keeps parsed files between commands, keyed by their content, so an edit made outside the daemon is seen by the next command; the environment variables a served command sees (the fixed list), and that `SQUADS_SPANS` and `SQUADS_DAEMON` act on the client.
- **`docs/api.md`:** the routes stay the public API for other clients and the terminal UI; state that this installation's CLI talks to its daemon through a private channel that is not part of the API and is not described there. Do not document `POST /v1/commands`'s wire format (ADR-1261 point 1: absent from the OpenAPI document and from `docs/api.md`). Remove anything that says the CLI calls the routes.
- **`docs/stability.md`, `docs/faq.md`, `CONTRIBUTING.md`:** the same corrections where they describe the CLI's remote path, the client budget or the parity jobs (`--api-mode remote` through the endpoint, `--api-mode routes` through `HttpApi`).
- **CHANGELOG 0.19.0:** the remote-mode entries rewritten for the shipped behaviour (one entry, not a history of the two designs), and the speed-up stated as measured by the shim task's report.

## Acceptance

- FEAT-1140 US9 holds against the shipped code: every command, variable, file and behaviour named exists and behaves as written. Check each against the code and a scratch squad, not against the ADR.
- No sentence describes the CLI calling `HttpApi` or the routes.

## Test approach

Drive every documented behaviour on a scratch squad nested under the session scratchpad with the dev tree (`uv run --project <repo> sq -C <scratch>`), in both modes (`SQUADS_DAEMON=on|off`), daemon stopped at the end; record what was run in a comment. Read the result as a stranger to the repository. `uv run --all-extras pytest -n 4 tests/meta` (the docs guards) and `~/.local/bin/sq check` clean. New tests: 0.

## Order

After the command-endpoint, parse-cache and shim tasks are merged. TASK-1221 (the current daemon and API pages) is the base this edits.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1266 add-subtask "<title>"`; track with `sq task 1266 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Daemon page, FAQ, stability and contributing

<!-- sq:subtask:ST1:body -->
`docs/daemon.md`: remote mode as the daemon running the command; the local-only commands; `--help`, `docs` and completion served; fall back before sending, no replay, Ctrl-C and timeouts; prompts in the user's terminal, confirmed for the screen seen; client files sent with the command; parsed files kept between commands and keyed by content; the environment a served command sees. Plus `docs/faq.md`, `docs/stability.md` and `CONTRIBUTING.md` (`--api-mode remote` and `--api-mode routes`) where they describe the CLI's remote path. Driven on a scratch squad in both modes.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — API page and CHANGELOG

<!-- sq:subtask:ST2:body -->
`docs/api.md`: the routes stay the API for other clients and the terminal UI; this installation's CLI uses a private channel that is not part of the API, and its wire format is not documented there (ADR-1261 point 1). Nothing says the CLI calls the routes. CHANGELOG 0.19.0: one remote-mode entry for the shipped behaviour, with the measured speed-up from the shim task's report.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-30T23:08:05Z] `tech-writer` Theo Writer:
  - - Docs and CHANGELOG rewritten for the shim-based remote mode, commit 6c883c29 on release/0.19 (pushed). Files: `docs/daemon.md`, `docs/api.md`, `docs/stability.md`, `docs/faq.md`, `docs/README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`.
      - `docs/daemon.md`: remote mode as the daemon parsing, running and rendering; the always-local list (bare `--version`, `init`, `adopt`, `daemon`, `ui`, `--install-completion`, `--show-completion`); `--help`, `docs`, `migrate help`/`chlog` and completion served; files a command names sent with it; two-phase prompts confirmed for the screen seen, local rerun when the daemon stops between phases; the sent environment list (`SQUADS_DAEMON` client-side only); the parse cache keyed by content; fallback before sending only; the unusable-setting stderr line; the version section narrowed to API clients (`sq ui` and others); the browser listener takes no command lines.
      - `docs/api.md`: the CLI uses a private channel outside the API, not described; no wire format; nothing says the CLI calls the routes. `docs/stability.md`: the unusable setting is no longer silent; the private channel listed as not part of the contract. `docs/faq.md`: a new entry for the unusable-setting warning; the schema/vocabulary entry scoped to `sq ui`. `CONTRIBUTING.md`: the shim's import sets and the 100 ms client budget (release criterion, CI reports only).
      - CHANGELOG 0.19.0: one daemon entry for the shipped behaviour; the `[daemon]` entry prints the problem; the HTTP API entry names the private channel; typer held to 0.27.x.
    - Driven with the dev tree (`.venv/bin/sq`, `SQUADS_DAEMON=on`) on a copy of this squad under `~/.cache/sq-1266/proj`, daemon stopped at the end: bare `--version` starts none; `--help`, `docs`, bash completion start one; `migrate help`, `ui --help` run; `SQUADS_DAEMON=maybe` prints the warning line and runs locally; `--file`, `--file -` served; a missing `--file` gives local mode's error text (same in `off`); removal prompt answered `n` and `y`, output identical to `off`; daemon stopped between the prompt's phases: the command reran locally and asked again; a frontmatter edit by `sed` seen by the next served `check`; a local-mode write seen by the next served `show`; `.squads.toml` edit retired the daemon and the next command started a new one; `SQUADS_SPANS=1` printed the served spans plus the shim's; `repair` behind a held index lock printed `waiting for the daemon (repair)…` after 10 s; SIGINT while the daemon waited on the lock: exit 130 with the "may still complete" line, the comment applied after the lock was released; a 0755 runtime directory gave the fallback line; `-C nowhere` gave local mode's error in both modes; `python -X importtime` in local mode loads none of starlette, uvicorn, h11, click.
    - Measured on the copy (1,227 item files), 15 interleaved runs, load 0.7-1.6: `task show` median 161 ms served against 732 ms local; `list --json` 159 against 620; `check` 1.7-2.0 s served once warm (3.2 s on the first run) against 6.7-7.1 s local. The CHANGELOG states these as one machine's figures.
    - `uv run --all-extras pytest -n 4 tests/meta`: 718 passed. The documented-commands guard reads the new page (a dead `sq` verb appended to `docs/daemon.md` turned it red; restored, green).
- [2026-10-30T23:08:06Z] `tech-writer` Theo Writer:
  - - @python-dev process-narration and stale-claim sweep of the new code comments in `_shim.py`, `_endpoint.py`, `_daemon/_commands.py`, `_daemon/_proxies.py`, `_parse_cache.py`: no phase/round/review narration found. Not edited (code is yours):
      - `src/squads/_shim.py`, the comment on `SENT_ENVIRONMENT`: "A variable outside this list does not exist for a served command; the daemon's diagnostic variables are never on it." Both halves are false against the code. `_proxies.Environment.__getitem__` reads every name outside the list from the daemon's own environment (the environment of the command that started it, minus `SQUADS_SPANS` and `SQUADS_DAEMON`), and `SQUADS_SPANS` is on the list. Suggested: "The variables whose client values a served command sees; it reads any other name from the daemon's own environment."
      - ADR-1261 point 1 carries the same "does not exist" sentence, while point 2 states what the code does (every other name reads the daemon's own). @architect the point 1 sentence needs the same correction.
- [2026-10-30T23:08:16Z] `tech-writer` Theo Writer:
  - ST1 and ST2 Done, task InReview; REV-1223 F66 set Fixed. @manager @reviewer
- [2026-10-30T23:41:07Z] `tech-writer` Theo Writer:
  - REV-1223 F66 reopen addressed in 1e2394f9 (waiting notice, unanswering daemon, prompt rerun); F66 Fixed again. @manager @reviewer
- [2026-10-30T23:45:31Z] `manager` Catherine Manager:
  - Accepted under the operator's overnight delegation (2026-10-31): REV-1223 is Approved with every finding Verified or Noted, and CI runs 41141368085 and 41145415746 are green on every job.
<!-- sq:discussion:end -->
