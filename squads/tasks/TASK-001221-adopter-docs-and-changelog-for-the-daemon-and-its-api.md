---
id: TASK-1221
sequence_id: 1221
type: task
title: Adopter docs and changelog for the daemon and its API
status: InReview
parent: FEAT-1140
author: tech-lead
assignee: tech-writer
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
  status: Done
  assignee: tech-writer
  maps_to: US9
- local_id: ST2
  title: API reference and security stance
  status: Done
  assignee: tech-writer
  maps_to: US9
created_at: '2026-10-28T14:08:44Z'
updated_at: '2026-10-30T08:40:03Z'
priority: medium
---
<!-- sq:body -->
## Goal

Adopter documentation for the daemon and its API, and the CHANGELOG entries for it (FEAT-1140 US9). Written for someone adopting squads into their own project, or writing a front against the API: no internal tracking references, no repository process, present tense.

## What it covers

- **Modes.** Remote and local mode, when each applies, that output is identical; the differences that remain: Ctrl-C (remote mode stops waiting and the operation completes, local mode ends the command), output arriving when an operation ends, the timeouts (5 s to connect, 300 s for an answer including time queued, no answer limit for the corpus-wide operations `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `migrate rename-field`, `migrate rename-kind`, `repair`, `renumber` and `import`, with the waiting notice after 10 s; the operation table's `timeout` class is the authority) and the "may still complete" message.
- **Settings.** The `[daemon]` table (`enabled`, `idle_timeout_minutes` with 0 = never, `browser`), `SQUADS_DAEMON=on|off` and its precedence, what an unusable value does (local mode, one stderr line, `sq check`), that settings take effect at the next command.
- **The fall back** and its stderr line; `sq daemon status` (with `--json`) and `sq daemon stop`. `sq daemon run` stays out of these docs.
- **The API for another client** (ADR-1225 sections 1-3, 6): the routes under `/v1` and their grammar (items by id, roster entries by address, squad-wide operations under `/v1/squad/`, `GET` never mutates, filters as query parameters with repeated keys); the envelope (`data`, `omitted`, `warnings`); the error body `{"error": {"type", "message", "warnings"}}` and the status table (404, 409 with its four types, 423, 400, 500); the request headers (`Squads-Actor`, `Squads-At`, the session ids, `Squads-Client-Dir`, `Squads-Schema`, `Squads-Vocabulary`, `If-Match`, `Squads-Client: 1`) and what a client must send to be admitted (JSON content type, `Squads-Client`, `Host`, `Origin` on the browser port); `GET /v1/openapi.json` as the source of the result schemas, `GET /v1/daemon`, `POST /v1/daemon/stop`. How a result carries a squad's own vocabulary (ADR-1250 section 7): an item or sub-entity row holds its stored attributes flat beside its core keys, `badges` maps each declared field that holds a value to its badge code on every row, a sub-entity carries `maps_to` and `deferred_to` and its `display` carries `maps_to` and `maps_to_kind`; a client reads badge values from `badges` and labels from `display` and the catalogs, as given, never from a field-named key. The document is the same for every squad, since the vocabulary travels in these maps.
- **The declared actor.** `Squads-Actor` is declared by the client and never verified, so the actor recorded on an item, a comment or a reflog line is a claim, with the same standing as the session ids.
- **Item versions.** The `ETag` on single-item reads and writes (a sub-entity shares its item's), the `etag` key of the show result (which local `show --json` also gains, a change the CHANGELOG lists), `If-Match` to refuse a write on an item changed since it was read (`409 changed_since_read`, nothing written), comments addressed by their content hash.
- **Compatibility.** A client and a daemon at different schema versions refuse each other (`409 schema_mismatch`), the CLI's two messages and their remedies; a checkout whose workflow vocabulary differs from the daemon's is refused (`409 vocabulary_mismatch`) and the remedy; that an incompatible change to a result shape ships as a schema change (linking the stability guide).
- **Dependencies.** Installing squads brings the daemon's HTTP server packages (`starlette`, `uvicorn`, with `h11` and `click`), which only the daemon loads.
- **Runtime directory** per platform (socket, json, lock, log) and where; nothing is written in the squad; a development (editable) install should keep the daemon off.
- **Security,** per platform, as US9 states it: on native Windows and on any platform with `daemon.browser` on, any local process or user can read and write the squad while the daemon runs; on POSIX with the browser port off, only the owning user can; browser-originated attacks are refused everywhere. Stated as a property, not a defect.

Likely homes: a daemon page and an API reference page under `docs/`, the configuration reference where `.squads.toml` keys are documented, `docs/faq.md` for misbehaviour, the CHANGELOG's unreleased section.

## Acceptance

FEAT-1140 US9 in full. Shapes and stability tiers are linked to `docs/stability.md` (which the bundled-vocabulary docs updated for `badges`, `maps_to_kind` and the kind `label`), not restated. Every command, key, route, header and file named exists in the shipped code: check each against the implementation and against `GET /v1/openapi.json`, not the ADR.

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
API reference for another client: the route grammar, the envelope, the error body with its `warnings`, the error statuses and types, how a row carries the squad's own vocabulary (flat attributes, `badges`, `maps_to`, `display.maps_to_kind`), the request headers with the declared, unverified actor, admission requirements, ETags and `If-Match`, the schema and vocabulary refusals with their remedies, `GET /v1/openapi.json`, `GET /v1/daemon`, `POST /v1/daemon/stop`. Security stated per platform exactly as US9 lists it, as a property. CHANGELOG entries in the 0.19.0 section, the `etag` key that local `show --json` gains among them. Every route and header checked against the served OpenAPI document.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-30T00:33:01Z] `tech-lead` Olivia Lead:
  - Brought up to date (2026-10-30): the timeout list now names every `long` operation (`rename-field` and `rename-kind` included); the error body carries `warnings`; the API page covers how rows carry a squad's own vocabulary (ADR-1250 section 7) and links `docs/stability.md`; the CHANGELOG lists the `etag` key that local `show --json` gains; dependencies list `h11` and `click`.
- [2026-10-30T08:19:01Z] `tech-writer` Theo Writer:
  - - @manager TASK-1221 written in the working tree (uncommitted), ST1 and ST2 Done, task InReview.
      - New: `docs/daemon.md` (modes and their differences, `[daemon]` and `SQUADS_DAEMON`, the fall back line, `sq daemon status|stop`, lifecycle, runtime directory per platform, dependencies, development install, version refusals, security per platform as US9 states it, Windows notes) and `docs/api.md` (reaching the listeners, OpenAPI, routes and grammar, request headers with the unverified actor, admission, envelope, error body and status table incl. 405/`Allow` and 503 retiring, how rows carry the vocabulary, ETag/If-Match, comments by hash, compatibility, the daemon's own routes).
      - Edited: `docs/stability.md` (Tier 1 "Daemon settings", Tier 2 "The daemon commands", exit `130`, `etag` row on show, `daemon status/stop` in the provisional list, a Tier 3 "The HTTP API" section: `/v1` versions the wire layer, the schema version the shapes, error types an open set, what is not contract), `docs/faq.md` (four entries, exit `130`), `docs/README.md` and `README.md` (index and command reference), `CHANGELOG.md` 0.19.0 (Added: daemon, `[daemon]`/`SQUADS_DAEMON`, `sq daemon`, the HTTP API, the browser listener; Changed: background process by default with the CI remedy; the dependency line now says only the daemon loads them), `CONTRIBUTING.md` (`tests/daemon/`, `--squad`, `--api-mode`, `SQUADS_DAEMON=off` in the root conftest, keep the daemon off in a checkout you change).
    - Driven on a scratch squad with the dev tree (`sq daemon run` started there three times and stopped each time: by a `.squads.toml` edit, by `sq daemon stop`, by `POST /v1/daemon/stop`; `sq daemon status` clean at the end): status human and `--json`, stop running and none (`--json` too), `daemon run` refused while one runs (`error: already running`, exit 1), retirement (503 `{"not_executed":"retiring"}`, four runtime files gone), `sq check` lines for an unusable value, an unknown key and a bad `SQUADS_DAEMON`, local `show --json` ending with `etag`, cross-mode visibility both ways. With curl on the socket and the browser port: the OpenAPI document (3.1.0, `info.version` 0.19, 93 paths, 127 operations, header parameters), GET/HEAD with `ETag` and `Server-Timing`, a sub-entity sharing its item's ETag, If-Match current (200, new ETag) and stale (409 `changed_since_read`, nothing written), 409 `conflict`, 404 item and `no such route`, 405 with `allow: DELETE, GET, HEAD, PATCH`, unknown body and query fields (400), relative `Squads-Client-Dir` (400), `schema_mismatch` and `vocabulary_mismatch` with `details`, `Squads-At` recorded, unknown actor refused, no actor recorded as `system`, every admission refusal (421 Host; 403 no Origin, wrong Origin, no `Squads-Client`, `text/plain`, preflight) and the socket admitting a write without either header.
    - Depends on TASK-1219's unmerged parts, written from the ADRs and the code on release/0.19 but not driven end to end, because `select_api` still returns `LocalApi`: the implicit start and the selection itself, the fall back stderr line (text quoted from `_daemon_start.failure_line`), the one stderr line for an unusable setting (only the `sq check` text is verified), Ctrl-C ending the wait with exit 130 (REV-1223 F30 is open: one Ctrl-C does not end the wait today), the timeout and connection-lost messages and the schema and vocabulary CLI messages (quoted from `_api/_client.py`), "a connection that cannot be made is handled like a failed start", `sq ui` following the same rule (ST9), and the default-on behaviour the Changed entry describes. Re-read these sentences in `docs/daemon.md` and the CHANGELOG once TASK-1219 lands.
    - Not run: native Windows and macOS (runtime directories, the CLI port, `Origin` on it), idle exit, crash leftovers, `423 locked`, `500 internal`.
    - Observed, for the owners: a repeated single-valued query key keeps the last value silently (`?type=task&type=feature` lists features only); the OpenAPI document lists no `403` on `GET` operations, which the Windows CLI port answers to a `GET` carrying an `Origin`.
    - `uv run --all-extras pytest -n 4 tests/meta`: 675 passed. The docs guards were shown to read the new pages (a dead `sq` verb and an item id appended to `docs/api.md` turned both red; restored). `sq check` clean.
- [2026-10-30T08:40:03Z] `tech-writer` Theo Writer:
  - - @manager Docs corrected against the merged remote mode (working tree, uncommitted: docs/daemon.md, docs/api.md, docs/stability.md, CHANGELOG.md, CONTRIBUTING.md). Driven on the scratch squad with the dev tree, daemon stopped at the end:
      - implicit start on `sq list`; `--version`, `docs`, `migrate help`, `--help` started none;
      - fall back line with an unusable runtime directory (mode 0755), exit 0;
      - one SIGINT while the daemon waited on the index lock: exit 130 in 0.02 s with the "may still complete" line, and the comment was applied after the lock was released;
      - `sq repair` behind a held lock: `waiting for the daemon (squad.repair)…`, then the lock notice, then the 423 error;
      - F35: 403 and 405 on every operation (GET included), 421/403/405 on the /v1/daemon routes; F36: `?type=task&type=feature` gives 400 `invalid request: type takes one value, got 2`.
    - Corrected, not just confirmed: an unusable `[daemon]` value or `SQUADS_DAEMON` now reads as local mode **with nothing on stderr** (only `sq check` reports it); ADR-1052 point 7 and FEAT-1140 US5 promise one stderr line, so either the code or those texts should change (owner: python-dev or architect). A connection refused after the daemon was found goes to local mode silently, and the docs now say so. `sq ui` is documented as choosing per request.
    - Not driven: the 300 s timeout, a connection lost after sending, the schema and vocabulary CLI messages (quoted from `_api/_client.py`), Windows and macOS. `pytest -n 4 tests/meta`: 673 passed; `sq check` clean.
<!-- sq:discussion:end -->
