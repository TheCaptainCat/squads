---
id: TASK-1221
sequence_id: 1221
type: task
title: Adopter docs and changelog for the daemon
status: Draft
parent: FEAT-1140
author: tech-lead
priority: medium
refs:
- ADR-1052:implements
- TASK-1219:depends-on
description: Modes, settings, SQUADS_DAEMON, fall back, status/stop, the command endpoint,
  runtime files, per-platform security
subentities:
- local_id: ST1
  title: Modes, settings, fall back and daemon commands
  status: Todo
  story: US9
- local_id: ST2
  title: Command endpoint reference and security stance
  status: Todo
  story: US9
created_at: '2026-10-28T14:08:44Z'
updated_at: '2026-10-28T14:10:01Z'
---
<!-- sq:body -->
## Goal

Adopter documentation for the daemon, and the CHANGELOG entry for it (US9). Written for someone adopting squads into their own project: no internal tracking references, no repository process.

## What it covers

- The two modes, when each applies, and that output is identical; the differences that remain: Ctrl-C (remote mode stops waiting, local mode ends the command) and output arriving when a command ends.
- Settings: the `[daemon]` table (`enabled`, `idle_timeout_minutes` with 0 = never, `browser`), `SQUADS_DAEMON=on|off` and its precedence, what an unusable value does (local mode, one stderr line, `sq check`), and that settings take effect at the next command.
- The fall back and its stderr line; `sq daemon status` and `sq daemon stop`.
- The command endpoint, so another client can use it: `POST /v1/commands` request (`argv`, `cwd`, `env`, `terminal`, `attachments`) and response, the `503 not_executed` reasons, `GET /v1/daemon`, `POST /v1/daemon/stop`, and the admission requirements a client must meet (JSON content type, the custom header, `Host`).
- What the runtime directory holds per platform (socket, json, lock, log) and where; that nothing is written in the squad.
- That a development (editable) install should keep the daemon off, because a daemon runs the code it started with.
- Security, per platform, as US9 states it: native Windows and any platform with `daemon.browser` on, any local process or user can read and write the squad while the daemon runs; POSIX with the browser port off, only the owning user; browser-originated attacks refused everywhere. Stated as a property, not a defect.

Likely homes: a new daemon page under `docs/`, plus the configuration reference wherever `.squads.toml` keys are documented, `docs/faq.md` for misbehaviour, and the CHANGELOG's unreleased section.

## Acceptance

US9 in full. Every command, key, endpoint and file named in the docs exists in the shipped code (check each against the implementation, not the ADR).

## Test approach

Run every documented command and example against a scratch squad outside this repository with the released or built package, in both modes, and record what was run. Read the result as a stranger to the repository: no build-process narration, present tense.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1221 add-subtask "<title>"`; track with `sq task 1221 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Modes, settings, fall back and daemon commands

<!-- sq:subtask:ST1:body -->
Adopter page for remote and local mode and their differences (Ctrl-C, output at the end), the `[daemon]` table and `SQUADS_DAEMON`, the fall back line, `sq daemon status` and `stop`, runtime directory contents per platform, and keeping a development install off. Every example run against a scratch squad in both modes.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Command endpoint reference and security stance

<!-- sq:subtask:ST2:body -->
Request and response of `POST /v1/commands`, the `503 not_executed` reasons, `GET /v1/daemon`, `POST /v1/daemon/stop`, and what a client must send to be admitted. Security stated per platform exactly as US9 lists it, as a property. CHANGELOG entry in the unreleased section.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
