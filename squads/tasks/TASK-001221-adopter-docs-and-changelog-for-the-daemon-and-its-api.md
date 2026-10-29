---
id: TASK-1221
sequence_id: 1221
type: task
title: Adopter docs and changelog for the daemon and its API
status: Draft
parent: FEAT-1140
author: tech-lead
priority: medium
refs:
- ADR-1052:implements
- TASK-1219:depends-on
- ADR-1225:implements
- ADR-1224:implements
- TASK-1218:depends-on
description: Modes, settings, fall back, daemon commands, routes, envelope, errors,
  headers, ETags, compatibility, declared actor, runtime files, per-platform security
subentities:
- local_id: ST1
  title: Modes, settings, fall back and daemon commands
  status: Todo
  story: US9
- local_id: ST2
  title: API reference and security stance
  status: Todo
  story: US9
created_at: '2026-10-28T14:08:44Z'
updated_at: '2026-10-28T22:26:04Z'
---
<!-- sq:body -->
## Goal

Adopter documentation for the daemon and its API, and the CHANGELOG entries for it (FEAT-1140 US9). Written for someone adopting squads into their own project, or writing a front against the API: no internal tracking references, no repository process, present tense.

## What it covers

- **Modes.** Remote and local mode, when each applies, that output is identical; the differences that remain: Ctrl-C (remote mode stops waiting and the operation completes, local mode ends the command), output arriving when an operation ends, the timeouts (5 s to connect, 300 s for an answer including time queued, no answer limit for migrate, repair, renumber and import, with the waiting notice after 10 s) and the "may still complete" message.
- **Settings.** The `[daemon]` table (`enabled`, `idle_timeout_minutes` with 0 = never, `browser`), `SQUADS_DAEMON=on|off` and its precedence, what an unusable value does (local mode, one stderr line, `sq check`), that settings take effect at the next command.
- **The fall back** and its stderr line; `sq daemon status` (with `--json`) and `sq daemon stop`. `sq daemon run` stays out of these docs.
- **The API for another client** (ADR-1225 sections 1-3, 6): the routes under `/v1` and their grammar (items by id, roster entries by address, squad-wide operations under `/v1/squad/`, `GET` never mutates, filters as query parameters with repeated keys); the envelope (`data`, `omitted`, `warnings`); the error body and the status table (404, 409 with its four types, 423, 400, 500); the request headers (`Squads-Actor`, `Squads-At`, the session ids, `Squads-Client-Dir`, `Squads-Schema`, `Squads-Vocabulary`, `If-Match`, `Squads-Client: 1`) and what a client must send to be admitted (JSON content type, `Squads-Client`, `Host`, `Origin` on the browser port); `GET /v1/openapi.json` as the source of the result schemas, `GET /v1/daemon`, `POST /v1/daemon/stop`.
- **The declared actor.** `Squads-Actor` is declared by the client and never verified, so the actor recorded on an item, a comment or a reflog line is a claim, with the same standing as the session ids.
- **Item versions.** The `ETag` on single-item reads and writes (a sub-entity shares its item's), the `etag` key of the show result, `If-Match` to refuse a write on an item changed since it was read (`409 changed_since_read`, nothing written), comments addressed by their content hash.
- **Compatibility.** A client and a daemon at different schema versions refuse each other (`409 schema_mismatch`), the CLI's two messages and their remedies; a checkout whose workflow vocabulary differs from the daemon's is refused (`409 vocabulary_mismatch`) and the remedy; that an incompatible change to a result shape ships as a schema change (linking the stability guide).
- **Dependencies.** Installing squads brings the daemon's HTTP server packages (`starlette`, `uvicorn`), which only the daemon loads.
- **Runtime directory** per platform (socket, json, lock, log) and where; nothing is written in the squad; a development (editable) install should keep the daemon off.
- **Security,** per platform, as US9 states it: on native Windows and on any platform with `daemon.browser` on, any local process or user can read and write the squad while the daemon runs; on POSIX with the browser port off, only the owning user can; browser-originated attacks are refused everywhere. Stated as a property, not a defect.

Likely homes: a daemon page and an API reference page under `docs/`, the configuration reference where `.squads.toml` keys are documented, `docs/faq.md` for misbehaviour, the CHANGELOG's unreleased section.

## Acceptance

FEAT-1140 US9 in full. Every command, key, route, header and file named exists in the shipped code: check each against the implementation and against `GET /v1/openapi.json`, not the ADR.

## Test approach

Run every documented command and example against a scratch squad outside this repository with the built package, in both modes, and call the documented routes with a plain HTTP client against a running daemon; record what was run in a comment. Read the result as a stranger to the repository. New tests: 0.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1221 add-subtask "<title>"`; track with `sq task 1221 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Modes, settings, fall back and daemon commands

<!-- sq:subtask:ST1:body -->
Adopter page for remote and local mode and their differences (Ctrl-C, output at the end, timeouts and the waiting notice), the `[daemon]` table and `SQUADS_DAEMON`, the fall back line, `sq daemon status` and `stop`, runtime directory contents per platform, keeping a development install off, and the daemon's dependencies. Every example run against a scratch squad in both modes.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — API reference and security stance

<!-- sq:subtask:ST2:body -->
API reference for another client: the route grammar, the envelope, the error statuses and types, the request headers with the declared, unverified actor, admission requirements, ETags and `If-Match`, the schema and vocabulary refusals with their remedies, `GET /v1/openapi.json`, `GET /v1/daemon`, `POST /v1/daemon/stop`. Security stated per platform exactly as US9 lists it, as a property. CHANGELOG entries in the unreleased section. Every route and header checked against the served OpenAPI document.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
