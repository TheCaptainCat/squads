---
id: TASK-1218
sequence_id: 1218
type: task
title: 'Daemon process: routes, request scope, listeners'
status: InProgress
parent: FEAT-1140
author: tech-lead
priority: high
refs:
- ADR-1052:implements
- TASK-1217:depends-on
- ADR-1225:implements
- TASK-1227:depends-on
- TASK-1243:depends-on
description: 'Starlette on uvicorn serving the operation table as /v1 routes: envelope
  and errors, OpenAPI, request scope, ETags, schema and vocabulary checks, settings,
  lifecycle, admission'
subentities:
- local_id: ST1
  title: '[daemon] table, SQUADS_DAEMON and the check rule'
  status: Todo
  story: US5
- local_id: ST2
  title: Shared endpoint resolution, key and runtime directory
  status: Todo
  story: US4
- local_id: ST3
  title: 'Starlette app: routes from the table, envelope, errors'
  status: Todo
  story: US1
- local_id: ST4
  title: Writes, corpus operations and ETags
  status: Todo
  story: US2
- local_id: ST5
  title: Lifecycle, retirement and sq daemon commands
  status: Todo
  story: US4
- local_id: ST6
  title: Listeners on uvicorn and the admission middleware
  status: Todo
  story: US6
- local_id: ST7
  title: Browser listener, off by default
  status: Todo
  story: US7
- local_id: ST8
  title: Request scope and metadata headers
  status: Todo
  story: US10
- local_id: ST9
  title: Schema and vocabulary checks, daemon side
  status: Todo
  story: US11
- local_id: ST10
  title: OpenAPI document and route guards
  status: Todo
  story: US1
- local_id: ST11
  title: Starlette and uvicorn at their locked lower bounds
  status: Done
  story: US1
- local_id: ST12
  title: Operation notices travel in warnings, nothing below the CLI prints
  status: Done
  story: US1
created_at: '2026-10-28T14:08:41Z'
updated_at: '2026-10-30T00:50:49Z'
---
<!-- sq:body -->
## Goal

The daemon process (ADR-1225 section 10, D1): a Starlette application on uvicorn that serves every operation of the operation table (`_api/_ops.py`, 127 operations) at its resource route, with the envelope and error table of ADR-1225, the OpenAPI document, the per-request scope, ETags, the schema and vocabulary checks, the listeners with their admission rules, the `[daemon]` settings, and `sq daemon run|status|stop`. After this task a daemon can be started by hand and driven by any HTTP client; the CLI does not call it yet (TASK-1219). It routes from the table, so an operation added to the table is served with no change here: `squad.rename-field` and `squad.rename-kind` (`/v1/squad/rename-field`, `/v1/squad/rename-kind`, timeout class `long`) are served like `rename-type` and `rename-status`.

## What it builds

- **Dependencies** (ADR-1225 section 6) — ST11. `starlette` and `uvicorn` join `[project] dependencies`, not an extra; `uvicorn`'s `standard` extra is not used. Their lower bounds are the versions this task locks, re-checked at lock time (latest on 2026-10-29: starlette 1.10.0, uvicorn 0.54.0), the rule FEAT-1242 applied to every other dependency. `uvicorn` brings `h11` and `click`; `click` is new to the install, since typer 0.27 vendors its own and the CLI imports `typer._click`. No `httpx`: the route harness serves the application with uvicorn on a thread and calls it through `http.client`. If a test client is wanted after all, `httpx` goes in the `dev` group at its locked version. Only the daemon imports these packages. Starts after TASK-1243's lock, so the daemon is built on typer 0.27, filelock 4 and pydantic 2.14.
- **Settings (ADR-1052 point 7)** — ST1. A tolerant `[daemon]` table on `SquadsConfig`: `enabled = true`, `idle_timeout_minutes = 30` (0 = never), `browser = false`; written by `to_toml()` only when non-default, kept by the legacy-key regeneration of `sq migrate up`; `SQUADS_DAEMON=on|off` overrides `enabled`; a squad-global `sq check` rule for unknown keys, unusable values and an unusable `SQUADS_DAEMON`.
- **Endpoint resolution, shared (ADR-1052 points 8-9, ADR-1225 section 5)** — ST2. One standard-library module from the client directory and `-C` values to the squad directory and an `Endpoint` (transport, address, how to check the daemon's identity, whether a local mode exists). It reads only `SQUADS_DAEMON`, the `.squads.toml` the walk-up finds (`squad_dir` and `[daemon]` only), the squad directory's real path, and `<key>.json`/`<key>.sock`. Key, runtime directory and the four files per key as ADR-1052 point 8 sets them. TASK-1219 calls it from the root callback.
- **The application (ADR-1225 sections 1, 3, 6)** — ST3. One Starlette `Route` per operation, built by a loop over the table, all served by one generic endpoint: validate the request DTO (query for `GET`, JSON body otherwise), await `LocalApi`, write `Response[T]` or the error body `{"error": {"type", "message", "warnings"}}` (`warnings` always present, an empty list when there is none; ADR-1225 section 3 as amended for REV-1235 F48) with the status from the table in `_api/_errors.py` (404 `not_found`, 409 `conflict`, 423 `locked`, 400 `invalid`, 500 `internal` with the traceback in the daemon log). The local half of the warnings is in place (`SquadsError.warnings`, attached by `LocalApi.call`); the wire half is this task's: `ErrorDetail` gains `warnings`. `GET /v1/daemon` (identity, listeners, start time, idle deadline, vocabulary hash with one digest per document) and `POST /v1/daemon/stop`. `503 {"not_executed": "retiring"}` is the only not-executed answer.
- **Request scope (ADR-1225 section 7)** — ST8. A context manager beside `compose_service`: a fresh `contextvars.Context`; a `RequestContext` bound from the headers (`Squads-Actor` declared and recorded as given, `Squads-At`, `Squads-Session-Id`, `Squads-Parent-Session-Id`, `Squads-Client-Dir` seeding `start_dir`, absent meaning paths spelled from the squad root, and `If-Match`) and the documents loaded at startup; the service for the operation's mode (normal mode built once at startup, fallback modes composed per request from the loaded documents); the read scope; one `asyncio.Lock` around the handler. No stdio redirection, no environment patching, no consoles, and no read of the daemon's own environment or working directory for a value a header carries. `Server-Timing` carries the handler's own time, which the client budget subtracts (ADR-1225 section 5).
- **Schema and vocabulary checks, daemon side (ADR-1225 sections 3 and 5)** — ST9. Order: schema, vocabulary, grant. `Squads-Schema` different from `SCHEMA_VERSION` answers `409 schema_mismatch` with both versions; a request without it is answered. The vocabulary hash: one standard-library function in `_api` over canonical bytes (format tag `squads-vocabulary-1`, the bundled `workflow.toml` and `<squad_dir>/.overrides/workflow.toml` or `absent`, BOM stripped, line ends normalised, length-prefixed, SHA-256), computed at startup from the bytes the daemon loaded. `spec_sources` already exists in `_spec_documents.py` and memoises the parsed documents per invocation; the hash takes its input from the same byte reads that loading uses under it (the bundled bytes through `_specload`, the override text through `OverrideFiles`), so what is hashed is what was parsed. A `Squads-Vocabulary` that differs runs the retirement check first (`503 retiring` if the configuration changed), otherwise answers `409 vocabulary_mismatch` with the per-document digests. The grant is the operation's, against the squad's on-disk schema.
- **Notices raised inside an operation (ADR-1225 section 3, ADR-1052 point 10 as amended 2026-10-30)** — ST12. Nothing below `_cli` and `_tui` writes to stdout or stderr. The index lock's waiting notice (`_index/_store.py`) and the reflog warnings (`_index/_reflog.py`) are recorded on the request's `RequestContext` instead of printed; `LocalApi` adds the recorded notices to the response's `warnings`, or the error's when the call is refused, as it adds the working-language notice. In local mode the root callback sets a sink on the `RequestContext` that prints a notice through the CLI's one notice printer as it is raised, and the end-of-call pass skips it as already printed; the daemon's request scope sets no sink, so its notices reach the client only in the answer. The lines become `warning: waiting for the index lock <path>…` and the reflog texts lose their `[squads reflog]` prefix. A `tests/meta` guard fails on a write or `print` to `sys.stdout`/`sys.stderr` outside `_cli`, `_tui`, `squads.__main__` and `_spans`, which also keeps a daemon line out of the parity harness's captured output.
- **Writes and ETags (ADR-1225 section 3, ADR-1052 points 14-15)** — ST4. Every write goes through the unchanged service code and `IndexStore.transaction()`, which since FEAT-1242 holds the OS lock (`fallback_to_soft=False`, `preserve_lock_file=True`); the corpus-wide operations (`migrate up`, `repad`, `rename-type`, `rename-status`, `rename-field`, `rename-kind`, `repair`, `renumber`, `import`) run synchronously. The ETag is the SHA-256 of the item file's bytes as the operation reads them, strong (`"<64 hex>"`): sent on every single-item read and every item write, sub-entities sharing the parent's, roster entries alike; the show DTO gains `etag`, last after `display` through `ItemShow`'s trailing-key list, so the key order ADR-1250 section 7 fixes before it is unchanged. `LocalApi` computes it too, so local `show --json` carries the key as well and the parity run compares it. How it travels (ADR-1225 section 3, "How the ETag travels"): `If-Match` is bound onto `RequestContext` with the other headers and read there by the transaction; the write records the new ETag on `RequestContext`, the hash of the addressed file's bytes at the end of the transaction under the lock, never a re-read after commit; the generic endpoint writes the header. The addressed item is the created one for `POST /v1/items` and the parent for sub-entity routes; a remove answers with none; write DTOs and the envelope get no `etag` field. `If-Match` on the item-level and sub-entity writes is compared inside the transaction after the re-read under the lock; a mismatch answers `409 changed_since_read` and writes nothing. Creation and corpus-wide operations check none; comments rely on their content hash.
- **Lifecycle and retirement (ADR-1052 points 11, 13)** — ST5. `sq daemon run` (hidden): takes `<key>.lock` (an OS lock, released when the process dies, like the index lock) or exits as already running, binds its listeners, reports `ready` or one failure line on the inherited pipe, exits after `idle_timeout_minutes` without a request, removes its four files on a clean exit. The configuration fingerprint (`.squads.toml` and every file under `.overrides/`) is compared before each operation; a difference answers `503 retiring` and exits. `sq daemon status` (`--json` from the start, ADR-1224 point 3a) and `sq daemon stop`, which waits for the files to go and exits 0 when none runs. The `daemon` group never goes through a daemon.
- **Listeners and admission (ADR-1052 points 4-6, ADR-1225 section 6)** — ST6. The daemon binds its own sockets: the Unix socket in the `0700` runtime directory with mode `0600` on POSIX, the loopback CLI port on native Windows, and hands them to one `uvicorn.Server` (`serve(sockets=[…])`) on the asyncio loop. Admission is one ASGI middleware ahead of routing, decided by the listener: `Host` allow-list, no CORS headers or preflight, `Content-Type: application/json` and `Squads-Client: 1` on every non-`GET`, any `Origin` refused on the Windows CLI port.
- **Browser listener (ADR-1052 points 4-6)** — ST7. Opened only when `browser = true`; `127.0.0.1` (and `::1` if dual-stacked) on an ephemeral port, never a non-loopback address; same routes, writes included; non-`GET` requires `Origin` equal to its own origin; listed in `<key>.json` and `GET /v1/daemon`.
- **OpenAPI and route guards (ADR-1225 sections 1 and 6)** — ST10. `GET /v1/openapi.json`: an OpenAPI 3.1 document built from the table at the first request (method, path, path and query parameters from the request DTO, body and response schemas from `models_json_schema`, the error envelope per status), `info.version` the schema version. The response schemas are taken in validation mode: the item and sub-entity rows serialise through a trailing-key `model_serializer` typed `dict[str, Any]`, so their serialization-mode schema is an opaque object with no properties (measured on 2026-10-30), while the validation-mode schema lists every key and allows the flat stored attributes (`extra="allow"`). The document does not depend on a squad's vocabulary: badge fields, kinds and attributes travel in maps (`badges`, `fields`, flat attributes), so one document serves every squad. `tests/meta` guards: the document describes every operation, each response schema listing its properties; no `GET` request DTO has a nested field (none has today: 53 `GET` operations checked on 2026-10-30).

## Modules touched

New: `src/squads/_daemon/` (application, generic endpoint, middleware, request scope, listeners, lifecycle, OpenAPI builder), `src/squads/_endpoint.py` (or the module name the dev picks for the shared, standard-library resolution), the vocabulary hash function in `_api`, `src/squads/_cli/_daemon.py` with its `LAZY_GROUPS` entry. Edited: `pyproject.toml` and `uv.lock`, `_api/_errors.py` (`warnings` on the error detail), `_models/_config.py`, `_migrations/_config_text.py`, `_workflow/_validator_names.py` and `_services/_validators.py` (the squad-global check rule beside `display_config_valid`), `_services/_service.py` (the scope beside `compose_service`), `_spec_documents.py`/`_specload.py` (the shared byte read), `_index/_store.py` (the `If-Match` comparison inside `transaction()`, the waiting notice recorded instead of printed), `_index/_reflog.py` (its warnings recorded), `_context.py` (the notice record and sink on `RequestContext`), `_services/_local_api.py` (notices merged into `warnings`), `_cli/__init__.py` (the local-mode sink), `tests/cross_process/test_the_index_lock.py` (its expected waiting lines become `warning: waiting for the index lock …`), `_api/_dto/_items.py` (`etag` on `ItemShow`), the import-edge table and, for any new module constant, the mutable-state allowlist in `tests/meta`. `_cli/_daemon.py` imports `squads._daemon` only inside the `daemon run` function, so no other command loads Starlette or uvicorn (the budget guard of TASK-1219 holds it).

## Acceptance

- FEAT-1140 US1: every operation in the table served at its route; `GET` never mutates; envelope; error statuses and types with the local-mode sentence and the warnings; OpenAPI describes every operation; daemon status and stop; file text travels in the request; one request at a time.
- ADR-1225 section 3, "Notices raised inside an operation": the waiting notice and the reflog warnings carried in `warnings` in both modes, printed once, as raised in local mode and when the answer arrives in remote mode.
- FEAT-1140 US2: writes as a peer under the lock, cross-mode visibility, ETags on reads and writes, `409 changed_since_read` with nothing written, the declared actor recorded as given.
- FEAT-1140 US4 (lifecycle, retirement, status and stop), US5 (settings), US6 server side (admission, Windows CLI port), US7 (browser listener), US10 (metadata headers bound per request, paths spelled from the client directory or the squad root), US11 daemon side (schema then vocabulary then grant; digests in `GET /v1/daemon`).
- ADR-1225 sections 1, 2, 3, 6, 7; ADR-1052 points 1-8 and 11-15 as amended.

## Test approach (ADR-1172 "The daemon's routes", "The cross-process set")

- Route tests run in-process: the application served on a thread of the test process against a copied squad, whole response asserted, state read back through `invoke … show --json`, in modules named for the route behaviour, no `covers` marker. Only what the parity run (TASK-1219) cannot see: one case per error-table row (8), the vocabulary mismatch on a changed configuration (1; the unchanged case is the `vocabulary_mismatch` row), a partial read's envelope (1), the binding of each metadata header (5), the ETag on a read and on a write (2), a `GET` that does not mutate (1), the admission negatives of ADR-1052 (7) and the browser listener (2). About 27.
- The daemon thread shares the test process's environment, working directory and `sys.stderr`. A header-binding case therefore sets the matching process value (`SQUADS_SESSION_ID`, `SQUADS_PARENT_SESSION_ID`, the working directory) to something else, so a daemon that reads its own process instead of the header fails it.
- Surface cases with markers: `[daemon]` breach cases in `tests/check/` (3) and the `migrate up` legacy-key case (1); `sq daemon status` running, none and `--json`, `sq daemon stop` running and none, `daemon run` refused while one runs (6); retirement on an edited `.squads.toml` and on a scaffolded override (2). Endpoint resolution through `-C` into a subfolder and from another squad (2). About 14. Those in `tests/cli/` run on both squads (ADR-1172 "Scope: two squads") and reach their host through the squad's profile, never a bundled name.
- Guards: OpenAPI covers every operation with its response properties; no nested field on a `GET` request; no stdout or stderr write below the CLI (ST12). 3.
- Edited, not added: the expected waiting lines in `tests/cross_process/test_the_index_lock.py`.
- Built and not tested: idle exit (ADR-1052 point 11), the lock singleton and crash leftovers, two writers in separate processes. The cross-process members are TASK-1219's.
- Expected total: about 41 tests and 3 guards. Falsify each once when written.

## Parallel plan: two developers, two worktrees

ST11 lands first, alone (one commit: `pyproject.toml`, `uv.lock`), so neither lane edits the lock. Then:

- **Lane A, the request path:** ST3, ST8, ST4, ST9, ST10, ST12, and the route harness (`tests/` fixture serving the application with uvicorn on a thread). Files: `_daemon/` application, endpoint, scope and OpenAPI modules, `_api/_errors.py`, the hash module in `_api`, `_services/_service.py`, `_spec_documents.py`/`_specload.py`, `_index/_store.py`, `_index/_reflog.py`, `_context.py`, `_services/_local_api.py`, the sink in `_cli/__init__.py`, `_api/_dto/_items.py`, `tests/meta` guards, `tests/cross_process/test_the_index_lock.py`. 18 tests and 3 guards.
- **Lane B, the process:** ST1, ST2, ST5, ST6, ST7. Files: `_models/_config.py`, `_migrations/_config_text.py`, `_workflow/_validator_names.py`, `_services/_validators.py`, `_endpoint.py`, `_daemon/` lifecycle, listener and admission modules, `_cli/_daemon.py`, `_cli/__init__.py` (`LAZY_GROUPS` only), `tests/check/`, `tests/cli/test_daemon.py`. 23 tests.
- **Seams, fixed before both start:** lane A's `build_app(state, retirement_check)`, where `state` is the identity `GET /v1/daemon` reports (filled by lane B's lifecycle) and `retirement_check` the callable the request scope runs before each operation and before answering a vocabulary mismatch (lane A ships a never-retiring default; lane B supplies the fingerprint). Lane B serves whatever `build_app` returns, wrapped in its admission middleware.
- **Shared files:** the import-edge table and the mutable-state allowlist in `tests/meta` take rows from both lanes, and `_cli/__init__.py` takes lane A's sink and lane B's `LAZY_GROUPS` entry; the second merge resolves them by union.
- **Merge order:** A, then B rebased on it. B's retirement, status and admission cases need A's routes and harness, so B writes them against A's branch and lands second.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1218 add-subtask "<title>"`; track with `sq task 1218 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — [daemon] table, SQUADS_DAEMON and the check rule

<!-- sq:subtask:ST1:body -->
Tolerant `[daemon]` model on `SquadsConfig` (`enabled`, `idle_timeout_minutes` with 0 = never, `browser`), written by `to_toml()` only when a value differs from its default and kept by the legacy-key regeneration of `sq migrate up` (`_migrations/_config_text.py`); `SQUADS_DAEMON=on|off` overrides `enabled`, any other value is unusable. A squad-global, always-on `sq check` rule beside `display_config_valid`, named in `_workflow/_validator_names.py` (`SQUAD_GLOBAL_VALIDATOR_NAMES`, `ALWAYS_ON_SQUAD_GLOBAL_NAMES`, its default level) and implemented in `_services/_validators.py`, reports unknown keys, unusable values and an unusable `SQUADS_DAEMON` (ADR-1052 point 7).

Tests (surface): three breach cases in `tests/check/` with their `breaches` marker (an unusable value, an unknown key, an unusable `SQUADS_DAEMON`), whole finding line asserted; one `sq migrate up` case on a legacy-key squad whose regenerated `.squads.toml` keeps a non-default table. Which mode a command takes under a setting is the fall back member of the cross-process set (TASK-1219). 4 tests.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Shared endpoint resolution, key and runtime directory

<!-- sq:subtask:ST2:body -->
One standard-library module (no pydantic, no rich) from the client directory and the `-C` values to the squad directory and an `Endpoint`: transport, address, how to check the daemon's identity, and whether a local mode exists (always true for a local daemon). It reads only `SQUADS_DAEMON`, the `.squads.toml` the walk-up finds (`squad_dir` and `[daemon]`, with `tomllib`), the squad directory's real path, and `<key>.json`/`<key>.sock` (ADR-1225 section 5, ADR-1052 points 8-9). `SquadsConfig`'s reading of `[daemon]` and `effective_dir` use it, so the daemon, the CLI and `sq check` cannot disagree. Key from the squad's real path, the squads version and the package directory; per-platform runtime directory with owner, mode and `sun_path` checks; the four files per key. Its input stays open to a configured remote address (FEAT-33) with no change here.

Tests (surface): with the route harness serving a squad, `sq daemon status --json` with `-C` into a subfolder reports that daemon, and from another squad reports none (2). An unusable runtime directory is a failed start, held by the fall back member of the cross-process set (TASK-1219). 2 tests.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Starlette app: routes from the table, envelope, errors

<!-- sq:subtask:ST3:body -->
Starlette application with one `Route` per operation, built by a loop over `_api/_ops.py`, all served by one generic endpoint: validate the request DTO (query string for `GET`, a repeated list field repeating its key; JSON body otherwise), await `LocalApi`, write `Response[T]` with `200`, or the error body `{"error": {"type", "message", "warnings"}}`, `warnings` always present and empty when there is none (ADR-1225 section 3 as amended for REV-1235 F48: `ErrorDetail` in `_api/_errors.py` gains the field, filled from `SquadsError.warnings`), with the status from the table in `_api/_errors.py` (404 `not_found`, 409 `conflict`, 409 `vocabulary_mismatch`, 409 `schema_mismatch`, 409 `changed_since_read`, 423 `locked`, 400 `invalid`, 500 `internal` with its traceback in the daemon log and a message saying to read it). A partial read is a `200` with a non-empty `omitted`. `GET /v1/daemon` and `POST /v1/daemon/stop`. `503 {"not_executed": "retiring"}` is the only not-executed answer (ADR-1225 sections 1, 3, 6; ADR-1052 points 1-2).

Tests (route, in-process harness, whole response asserted, no `covers` marker): one case per error-table row (8), the `423 locked` one asserting the index lock's waiting notice in the error's `warnings` (ST12), and a partial read's envelope (1). The success path of every operation is the parity run of TASK-1219, not new cases. 9 tests.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Writes, corpus operations and ETags

<!-- sq:subtask:ST4:body -->
Writes go through the unchanged service code and `IndexStore.transaction()`; `migrate up`, `repad`, `rename-type`, `rename-status`, `rename-field`, `rename-kind`, `repair`, `renumber` and `import` run synchronously like any operation (ADR-1052 points 14-15). ETags (ADR-1225 section 3, "Concurrent writes"): the SHA-256 of the item file's bytes as the operation reads them, sent strong; on every single-item read and every item write, sub-entity routes sharing the parent's, roster entries alike; the show DTO gains the provisional `etag` key, last after `display` through `ItemShow`'s trailing-key list, so the order ADR-1250 section 7 fixes for the keys before it holds. `LocalApi` computes it as well, so local `show --json` carries it and the parity run compares it; that local change is reported for the CHANGELOG (TASK-1221). `If-Match` on update, status, body, retype, remove, refs, views and the sub-entity add, update, body and remove is compared inside the transaction after the re-read under the lock; a mismatch answers `409 changed_since_read` and writes nothing. Creation and the corpus-wide operations check none; comment edits and removals rely on the content hash.

How it travels (ADR-1225 section 3): `If-Match` is read from `RequestContext` (bound by ST8) inside the transaction; the write records the new ETag on `RequestContext` as the hash of the addressed file's bytes at the end of the transaction, under the lock, never re-read after commit, and the generic endpoint writes the header. The addressed item is the created one for `POST /v1/items` and the parent for sub-entity routes; a remove answers with none; no `etag` field on write DTOs or the envelope.

Tests (route): the ETag on a read and on a write (the created item's on `POST /v1/items`), each asserting the header equals the hash of the bytes read back (2). The mismatch is the `changed_since_read` row of ST3. Cross-mode visibility comes from the parity run. 2 tests.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Lifecycle, retirement and sq daemon commands

<!-- sq:subtask:ST5:body -->
`sq daemon run` (hidden from `--help` and adopter docs): takes `<key>.lock`, an OS lock released when its holder dies, built like the index lock (`fallback_to_soft=False`), or exits as already running, binds its listeners, reports `ready` or one failure line on the inherited pipe and closes it, exits after `idle_timeout_minutes` without a request (an operation in progress counts as activity), removes its four files on a clean exit, replaces a crashed predecessor's log. Configuration fingerprint at start (bytes of `.squads.toml`, names and bytes of every file under `<squad-dir>/.overrides/`), compared before each operation; any difference answers `503 retiring` and exits (ADR-1052 points 11, 13). `sq daemon status` (with `--json`) and `sq daemon stop` (waits until the files are gone; exit 0 with none running).

Tests (surface, `invoke` with `covers` markers, route harness for a running daemon, in `tests/cli/test_daemon.py`, so they run on both squads through the squad profile): `daemon status` with one running and with none, its `--json`; `daemon stop` with one running (then `status --json` reports none) and with none; `daemon run` refused as already running (6). Retirement: an edited `.squads.toml` and an override scaffolded by `sq override` each answer `retiring` (2). Idle exit is built and not tested (ADR-1052 point 11); the lock singleton and crash leftovers are not cross-process members and get no test. 8 tests.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Listeners on uvicorn and the admission middleware

<!-- sq:subtask:ST6:body -->
The daemon binds its own sockets and hands them to one `uvicorn.Server` (`serve(sockets=[…])`) on the asyncio loop: the Unix socket in the `0700` runtime directory with mode `0600` on POSIX, the loopback CLI port on native Windows, always on while the daemon runs. Admission is one ASGI middleware ahead of routing, decided by the listener the connection arrived on (ADR-1052 point 5, ADR-1225 section 6): `Host` exactly `127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>`; no CORS headers, no preflight answered; every non-`GET` requires `Content-Type: application/json` and `Squads-Client: 1` (name case-insensitive, value exactly `1`); the Windows CLI port refuses any `Origin`.

Tests (route, harness over TCP, whole status and body asserted): one negative case per rule of ADR-1052's Consequences: a rebinding `Host`, a form post, a `text/plain` body, a missing and a wrong `Squads-Client`, any `Origin` on the Windows CLI port (6, the last running on the Windows runner and skipped by platform elsewhere). The positive request is every parity case. 6 tests; the foreign-`Origin` negative of the browser port is ST7's.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Browser listener, off by default

<!-- sq:subtask:ST7:body -->
Opened only when `browser = true`: binds `127.0.0.1` (and `::1` if dual-stacked) on an ephemeral port, never a non-loopback address; serves the same routes, writes and the OpenAPI document included; non-`GET` requires `Origin` equal to its own origin; listed in `<key>.json` and `GET /v1/daemon`. No authentication (ADR-1052 points 4-6).

Tests: `sq daemon status --json` lists no browser listener by default and a loopback one with `browser = true` (surface, 1, may share ST5's `--json` case); through that listener a write with its own `Origin` succeeds and is read back by `invoke … show --json`, and a foreign `Origin` is refused with the whole response asserted (route, 2). About 3 tests.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Request scope and metadata headers

<!-- sq:subtask:ST8:body -->
The per-request scope of ADR-1225 section 7, a context manager beside `compose_service` in `_services/_service.py`: a fresh `contextvars.Context`; a `RequestContext` bound from the headers and the documents loaded at startup: `Squads-Actor` (declared, recorded as given, never verified), `Squads-At`, `Squads-Session-Id`, `Squads-Parent-Session-Id`, and `Squads-Client-Dir` seeding `start_dir` so `path_from_process_dir` spells paths from it, its absence spelling them from the squad root, and `If-Match`, which the transaction reads (ST4); the service for the operation's mode (normal mode built once at startup, a fallback mode composed per request from the loaded documents); the read scope (ADR-753); one `asyncio.Lock` around the handler so operations run one at a time in arrival order, identity and stop answered without waiting. No stdio redirection, no environment variables set or read for a value a header carries, no read of the daemon's working directory, no consoles, no command line. The handler's own time goes out in `Server-Timing`.

Tests (route): the binding of each metadata header, one case each, read back through the CLI: the actor on a reflog line, the `--at` time on the written item, each session id on the reflog line, and a remedy path spelled from the client directory against one without it (5). The daemon thread shares the test process, so each case sets the process value the header replaces (`SQUADS_SESSION_ID`, `SQUADS_PARENT_SESSION_ID`, the working directory) to something else: a daemon reading its own process instead of the header fails it. Isolation between requests follows from the fresh context and is held by the parity run. 5 tests.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Schema and vocabulary checks, daemon side

<!-- sq:subtask:ST9:body -->
Daemon side of ADR-1225 sections 3 and 5. The check order inside the request scope is schema, then vocabulary, then the operation's `grant` against the squad's on-disk schema (ADR-955).
- `Squads-Schema` different from `SCHEMA_VERSION` answers `409 schema_mismatch` with both versions; nothing runs; a request without the header is answered.
- The vocabulary hash: one standard-library function in `_api`, over canonical bytes (format tag `squads-vocabulary-1`; for each document in a fixed order its name and `absent` or its text decoded as UTF-8 with a leading BOM removed and CRLF/CR turned into LF; every field length-prefixed; SHA-256, 64 hex digits), over the bundled `workflow.toml` and `<squad_dir>/.overrides/workflow.toml`. `spec_sources` in `_spec_documents.py` already memoises the parsed documents per invocation; the hash takes its bytes from the same reads loading uses under it (the bundled bytes through `_specload`, the override text through `OverrideFiles`), so what is hashed is what was parsed. The daemon computes it at startup from what it loaded and reports it, with one digest per document, at `GET /v1/daemon` and in `sq daemon status`.
- A `Squads-Vocabulary` that differs: the retirement check runs first (`503 retiring` when the configuration changed since start); otherwise `409 vocabulary_mismatch` with the per-document digests; nothing runs.

Tests (route): the `schema_mismatch` and `vocabulary_mismatch` rows are ST3's; the mismatch on a changed configuration answering `retiring` (1). The CLI's messages are TASK-1219's. 1 test.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — OpenAPI document and route guards

<!-- sq:subtask:ST10:body -->
`GET /v1/openapi.json`: an OpenAPI 3.1 document built from the operation table at the first request: per operation its method and path, path and query parameters from the request DTO's fields, request body and response schemas from pydantic (`models_json_schema`, JSON Schema 2020-12, in validation mode: the item and sub-entity rows serialise through a trailing-key `model_serializer` typed `dict[str, Any]`, so their serialization-mode schema is an opaque object, measured 2026-10-30; the validation-mode schema lists every key and allows the flat stored attributes), and the error envelope for each status of ADR-1225 section 3; `info.version` is the schema version, which the web front sends as `Squads-Schema` (ADR-1225 section 6). `GET` requests never mutate (ADR-1225 section 1).

Tests: two `tests/meta` guards, the document describes every operation in the table and every response schema lists its properties, and no `GET` request DTO declares a nested field; one route case, a `GET` that does not mutate (state read back through the CLI before and after). 1 test, 2 guards.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->

<!-- sq:subtask:ST11 -->
### ST11 — Starlette and uvicorn at their locked lower bounds

<!-- sq:subtask:ST11:body -->
`starlette` and `uvicorn` in `[project] dependencies` (ADR-1225 section 6), not an extra, without `uvicorn`'s `standard` extra; lower bounds at the versions locked in this commit, re-checked at lock time (latest on 2026-10-29: starlette 1.10.0, uvicorn 0.54.0), the rule FEAT-1242 applied to every other dependency. `h11` and `click` come with `uvicorn`; `click` is new to the install, since typer 0.27 vendors its own and the CLI imports `typer._click`. No `httpx` unless a test client is wanted, and then in the `dev` group at its locked version. One commit, `pyproject.toml` and `uv.lock` only, landed before either lane starts, after TASK-1243's lock.

Tests: none of its own; the full suite, pyright and ruff pass on the new lock. 0 tests.
<!-- sq:subtask:ST11:body:end -->

#### Discussion

<!-- sq:subtask:ST11:discussion -->
<!-- sq:subtask:ST11:discussion:end -->
<!-- sq:subtask:ST11:end -->

<!-- sq:subtask:ST12 -->
### ST12 — Operation notices travel in warnings, nothing below the CLI prints

<!-- sq:subtask:ST12:body -->
ADR-1225 section 3, "Notices raised inside an operation" (ADR-1052 point 10 as amended 2026-10-30). The index lock's waiting notice in `_index/_store.py` and the reflog warnings in `_index/_reflog.py` are recorded on the request's `RequestContext` instead of printed. `LocalApi` adds the recorded notices to the response's `warnings`, or to the error's when the call is refused, as it adds the working-language notice. The root callback gives the `RequestContext` a sink that prints a notice through the CLI's notice printer as it is raised, and the end-of-call pass skips a notice already printed, so each prints once; the daemon's request scope (ST8) sets no sink. Texts carry no prefix of their own: `warning: waiting for the index lock <path>…`, and the reflog warnings without `[squads reflog]`.

A `tests/meta` guard fails on a write to `sys.stdout` or `sys.stderr`, or a `print` to either, in any module outside `_cli`, `_tui`, `squads.__main__` and `_spans`.

Tests: the guard (1); the expected waiting lines in `tests/cross_process/test_the_index_lock.py` updated to the new text (edited, not added); the notice in a refused call's `warnings` is ST3's `423 locked` route case. Falsify the guard with one `print` below the CLI. 0 tests, 1 guard.
<!-- sq:subtask:ST12:body:end -->

#### Discussion

<!-- sq:subtask:ST12:discussion -->
<!-- sq:subtask:ST12:discussion:end -->
<!-- sq:subtask:ST12:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T22:34:07Z] `architect` Robert Architect:
  - Settled your open point on how a write's ETag reaches the router in ADR-1225 section 3, "How the ETag travels" (amended 2026-10-28), as you recommended, with one addition: `If-Match` travels the same way.
  - ST8 binds `If-Match` onto `RequestContext` with the other headers, and the transaction reads it there. The write records the new ETag on `RequestContext`: the hash of the addressed file's bytes at the end of the transaction, under the lock, never a re-read after the commit. The generic endpoint writes the header. The addressed item is the created one for `POST /v1/items` and the parent for sub-entity routes. A remove answers with none. Write DTOs and the envelope get no `etag` field, and the show DTO keeps its own.
  - @tech-lead please update the task body, ST4 and ST8.
- [2026-10-28T22:36:28Z] `tech-lead` Olivia Lead:
  - Body, ST4 and ST8 updated per the architect (7839e9b): If-Match bound onto RequestContext and read by the transaction; the write records the new ETag there and the endpoint writes the header; no etag on write DTOs; remove answers none. Test count unchanged (about 41).
- [2026-10-29T07:04:57Z] `manager` Catherine Manager:
  - From REV-1235 F48 (architect ruling, ADR-1225 §3 amended 2026-10-29): the wire error envelope becomes {"error": {type, message, warnings}} with warnings always present, and HttpApi restores them on the SquadsError it raises. The local side (SquadsError.warnings, attached by LocalApi.call) landed in dcc42a00; the wire form and HttpApi parsing land with the daemon (this task and TASK-1219).
- [2026-10-29T16:24:42Z] `tech-lead` Olivia Lead:
  - Depends on TASK-1243 per op-pierre on MILE-1241 (dependency upgrade first). When this task adds starlette and uvicorn, set their lower bounds to the versions it locks (latest on 2026-10-29: starlette 1.10.0, uvicorn 0.54.0, httpx 0.28.1 if a test client is used).
- [2026-10-30T00:32:58Z] `tech-lead` Olivia Lead:
  - Brought up to date with release/0.19 (2026-10-30); decisions and test count (about 41 tests, 2 guards) unchanged.
    - New ST11: `starlette`/`uvicorn` at their locked lower bounds, one commit before both lanes and after TASK-1243's lock. `click` comes in with uvicorn, and no `httpx` is needed (the harness serves with uvicorn on a thread).
    - ST3: the error body carries `warnings` (ADR-1225 section 3 as amended for REV-1235 F48). `_api/_errors.py` lacks the field today.
    - ST4: the corpus-wide list now includes `rename-field` and `rename-kind` (already `long` in the table). `etag` goes last on `ItemShow` through its trailing keys, and local `show --json` gains it.
    - ST1: the check rule is registered in `_workflow/_validator_names.py` plus `_services/_validators.py`, not in the bundled workflow spec.
    - ST9: `spec_sources` already exists, so the hash shares its byte reads. ST10: response schemas in validation mode, because serialization mode is opaque for the row DTOs (measured).
    - ST5: `<key>.lock` is an OS lock like the index lock. ST8: header-binding cases set the competing process value, so a daemon reading its own environment fails them.
    - REV-1223's findings deferred here (F3, F4, F6, F8) are all settled with their subject removed; nothing is live (checked at HEAD).
    - Parallel plan: lane A (ST3, ST8, ST4, ST9, ST10), lane B (ST1, ST2, ST5, ST6, ST7), seams and merge order in the body.
- [2026-10-30T00:44:16Z] `tech-lead` Olivia Lead:
  - Folded the 2026-10-30 rulings (architect 6f3d62c on FEAT-1140): new ST12 (lane A) records the lock notice and reflog warnings on `RequestContext`, with the local sink set by the root callback, `LocalApi` merging them into `warnings`, the guard against stdout/stderr writes below the CLI, and the expected lines updated in `tests/cross_process/test_the_index_lock.py`. ST3: the 423 case asserts the notice in `warnings`. Now about 41 tests and 3 guards.
<!-- sq:discussion:end -->
