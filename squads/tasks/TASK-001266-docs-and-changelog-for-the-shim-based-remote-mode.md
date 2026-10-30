---
id: TASK-1266
sequence_id: 1266
type: task
title: Docs and changelog for the shim-based remote mode
status: Draft
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
  status: Todo
  maps_to: US9
- local_id: ST2
  title: API page and CHANGELOG
  status: Todo
  maps_to: US9
created_at: '2026-10-30T20:30:38Z'
updated_at: '2026-10-30T20:32:22Z'
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
<!-- sq:discussion:end -->
