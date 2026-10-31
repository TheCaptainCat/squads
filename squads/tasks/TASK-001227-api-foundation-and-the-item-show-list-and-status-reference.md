---
id: TASK-1227
sequence_id: 1227
type: task
title: Api foundation and the item show, list and status reference
status: Done
parent: FEAT-1226
author: tech-lead
assignee: python-dev
refs:
- ADR-1224:implements
description: The _api package, LocalApi, the binding table and the guards; item show,
  list and status moved end to end as the pattern
subentities:
- local_id: ST1
  title: 'The _api package: envelope, operation table, Api, wire form'
  status: Done
  maps_to: US3
- local_id: ST2
  title: LocalApi, the binding table and the API on the request
  status: Done
  maps_to: US1
- local_id: ST3
  title: 'Guards: _services imports, renderers, bindings, DTO fields'
  status: Done
  maps_to: US3
- local_id: ST4
  title: Item show, list and status end to end
  status: Done
  maps_to: US1
- local_id: ST5
  title: Display content and renderers for items
  status: Done
  maps_to: US4
- local_id: ST6
  title: JSON output on item status
  status: Done
  maps_to: US2
created_at: '2026-10-28T22:12:36Z'
updated_at: '2026-10-29T00:07:16Z'
priority: high
---
<!-- sq:body -->
## Goal

Lay the command layer of ADR-1224 (increment 0) and move three item commands onto it end to end, so every later task copies one worked pattern: `sq <type> <n> show`, `sq list` and `sq <type> <n> status`. Local mode stays byte-identical apart from the display keys added to their JSON documents. The daemon (TASK-1218) starts from what this task fixes: the operation table, the envelope and the error form.

## What it builds

- **`squads/_api/`** (ADR-1224 point 2, point 4). Imports only `pydantic`, `_models` (for `Omission`) and `_errors`.
  - `Response[T]` with `data`, `omitted`, `warnings` (point 3).
  - `Operation[Req, Res]`: `name`, `method`, `path` (ADR-1225 section 1), `request`, `response`, `mode` (ADR-1128 composition mode), `grant` (ADR-955), `local_only`, `timeout` (`standard` or `long`).
  - `_api/_ops.py`: the one literal operation table, laid out with one marked section per resource group (items, item reads, item writes, roster, squad state, corpus-wide) so later tasks append inside their own section only.
  - The `Api` protocol (one generic `call`), the wire form of errors (`{"error": {"type", "message"}}` and the exception-to-type mapping ADR-1225 section 3 tables), and `HttpApi`'s wire helpers: request encoding (path and query from a flat `GET` request, JSON body otherwise) and response parsing back into `Response[Res]` or a `SquadsError`. Standard library only. No transport use yet: TASK-1219 wires it.
  - DTO modules split by resource under `_api/_dto/`, one module per resource, models frozen, JSON-native fields only, pydantic `defer_build` (a client-budget lever, ADR-1225 section 5). This task adds the shared display pieces (`display` object, `columns` entry) and the item DTOs: the show DTO, the item row (stored attributes flat through `extra="allow"` on that one model), the list response.
- **`LocalApi` and the binding table** in `_services` (point 4). `bind(OP, Service.method)` in one literal table, no registration side effect. `LocalApi` composes the service for `op.mode` through `compose_service`, keeps one service per mode for its lifetime, applies the operation's `grant` against the squad's schema (ADR-955), opens the read scope (ADR-753) around the call and returns the DTO object unserialised. The root callback's schema gate stays in place until TASK-1232, so a command already on an operation is gated twice in the meantime, with one message.
- **API selection seam.** The root callback puts the invocation's `Api` on `RequestContext` (point 4). In this task it is always `LocalApi`; TASK-1219 adds the selection rule. The one function that builds `LocalApi` is the only `_cli` code allowed to import `squads._services`.
- **Rendering.** `_cli/_render/` with one module per resource; this task adds the item renderers (show panes, the list table, the status line). They take a DTO and a console, nothing else; `rich.markdown` is imported only where a body is rendered (budget lever).
- **The three reference commands.** Each parses, refuses what the vocabulary alone decides with exit 2 and today's text, builds one request DTO, makes one call, renders the response (point 1). Existence and type of the addressed item, roster checks on `--as`, and the duplicate-id warning move into the operation; the group callback `sq <type> <n>` only parses the number into an id (point 1). The show DTO carries everything `print_item` reads from the service today: rendered body (`rendered_body` beside `body`), discussion, every sub-entity block, view data, the `badges` key Tier 3 already has.
- **Display content for items** (point 5): the `display` object on the show DTO and every list row (type label, rendered status badge, each declared badge field with its label and rendered badge, the assignee's display name), `columns` on the list response, the working-language notice as a `warnings` entry. New keys are appended after the existing keys of each document.
- **`--json` on `sq <type> <n> status`.** ADR-1224 point 3a lists it under increment 2, but its own rule puts a flag in the task that moves the command, and status moves here. It prints the written item row.
- **Seeded-request code that ADR-1225 section 9 removes.** Nothing calls it since the command endpoint was dropped, and it sits in the files this task reshapes before parallel work forks, so it goes here: `RequestContext.attachments`, `terminal` and `consoles` as request seeds, `run`'s `seed` parameter, `client_path` served from attachments (`read_client_text` keeps only its filesystem and stdin path and its current refusal wording), `NeedsTerminal`, `confirm_or_signal` and `prompt_or_signal` (the four sites go back to `typer.confirm`/`typer.prompt`), and the root callback's copying of seeded terminal facts. Kept: `run(argv)`, consoles built per invocation, `start_dir`, `documents`, `_paths.process_dir()`.

## Guards (tests/meta)

- `_cli` imports `squads._services` only in the `LocalApi` factory, at any position, with a pending list of the `_cli` modules that still do (point 2). One module per line, sorted, so parallel tasks each delete their own lines.
- `_cli/_render/` imports none of `squads._workflow`, `squads._paths` or the configuration model (point 5). `_tui` joins it in TASK-1233.
- Every operation in the table is bound exactly once (point 4).
- Every `_api` DTO field is JSON-native (str, int, float, bool, None, list, str-keyed dict, nested DTO), which is what makes the local object and the parsed HTTP body render the same (point 2). Read statically from the model fields. This guard is the tech lead's choice of test, not an ADR requirement: it holds the round-trip property before the parity job of TASK-1219 exists.
- The existing grant guard (`test_the_commands_past_the_gate_are_the_commands_that_declare_a_grant`) accepts a grant declared on the operation as well as on the command, until TASK-1232 removes the CLI-side gates.
- New package edges (`_cli -> _api`, `_services -> _api`, `_api -> _models`, `_api -> _errors`) are rows in the import-edge table; module-level tables are allowlisted as CODE constants in the mutable-state guard.

## Modules touched

New: `src/squads/_api/` (`_response.py`, `_ops.py`, `_api.py`, `_errors.py`, `_http.py`, `_dto/_display.py`, `_dto/_items.py`), `src/squads/_services/_local_api.py`, `src/squads/_services/_bindings.py`, `src/squads/_cli/_render/_items.py`.
Edited: `_cli/__init__.py` (root callback, `run`), `_cli/_common.py` (`print_item`, `build_item_json`, `build_item_row_json` stop being called by these three commands; the seeded helpers go), `_cli/_items.py` (show, status, the item group callback), `_cli/_main.py` (`list`), `_context.py`, `_errors.py`, `_services/_results.py` (only what these three use), `tests/meta/` as above.

## How the parallel tasks avoid colliding (convention set here)

TASK-1228, TASK-1230, TASK-1231 and TASK-1218 start from this task's merge, each in its own worktree.
- **DTOs:** one module per resource under `_api/_dto/`; a task creates its own modules and adds fields to another task's module only by appending.
- **Operation table and binding table:** each task appends inside its own marked section of `_api/_ops.py` and `_services/_bindings.py`.
- **Renderers:** one module per resource under `_cli/_render/`, owned by the task that creates it.
- **`_cli/_common.py`:** a task stops calling a shared helper but does not delete or reshape it while another command group still uses it; TASK-1232 deletes what is left dead. A helper only one task's commands use may be moved into that task's renderer.
- **`_services/_results.py`:** a task moves or projects only the result classes its own commands use.
- **Guards:** pending-list and edge-table edits are one line each, sorted.
- **Surface tests:** each task edits only the `tests/cli/` modules of its own command groups.
- Land in dependency order and rebase the later worktree; the import blocks of `_cli/_main.py` and `_cli/_items.py` are the expected conflict, resolved by the later lander.

## Acceptance

- FEAT-1226 US1 for `show`, `list` and `status`: one call each, exit-2 refusals unchanged, existence and roster checks in the operation, partial read still prints, then the `omitted` line, then exit 4.
- FEAT-1226 US2: `status --json` prints the written item row.
- FEAT-1226 US3: the JSON these commands print is the `data` of their operation's response, with no CLI-side assembly.
- FEAT-1226 US4 for these three: `display`, `columns`, `rendered_body` and the working-language warning; their renderers read no vocabulary or configuration (guard green).
- ADR-1224 points 2, 3, 4, 5 and 8 (increment 0); ADR-1225 section 9 removals.
- Gates: pyright, ruff, `sq check`, `tests/meta`, and the surface suite unchanged except the `--json` expectations of `show` and `list`, which gain only the display keys.

## Test approach (ADR-1172)

- The proof is the existing surface suite passing. Expected edits: the whole-document `--json` expectations of `show` and `list` gain the display keys (US1 allows added keys). Review checks that every edited expectation only adds keys.
- New surface cases: 1, `status --json` in `tests/cli/test_item_verbs.py` with its `covers` marker, whole document asserted.
- New guards: 4 (`_services` import, renderer import, binding, JSON-native DTO fields), plus the grant-guard adjustment.
- Falsify each new case and guard once: break it, see red, restore.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1227 add-subtask "<title>"`; track with `sq task 1227 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — The _api package: envelope, operation table, Api, wire form

<!-- sq:subtask:ST1:body -->
The `squads/_api/` package (ADR-1224 points 2-4): `Response[T]` (`data`, `omitted`, `warnings`); `Operation[Req, Res]` with `name`, `method`, `path`, `request`, `response`, `mode`, `grant`, `local_only`, `timeout`; the literal table `_api/_ops.py` laid out in one marked section per resource group; the `Api` protocol with one generic `call`; the wire form of errors and the exception-to-type mapping of ADR-1225 section 3; `HttpApi`'s wire helpers (request encoding, response parsing into `Response[Res]` or a `SquadsError`), standard library only; `_api/_dto/` with one module per resource, frozen, JSON-native, `defer_build`. Imports only `pydantic`, `_models` and `_errors`; the new package edges go in the import-edge table and the module-level tables in the mutable-state allowlist. No test of its own: the guards (ST3) and the reference commands (ST4) exercise it.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — LocalApi, the binding table and the API on the request

<!-- sq:subtask:ST2:body -->
`LocalApi` and the binding table in `_services` (ADR-1224 point 4): `bind(OP, Service.method)` in one literal table, pyright-checked per pair, no registration side effect. `LocalApi` composes the service for `op.mode` through `compose_service`, keeps one service per mode for its lifetime, applies the operation's `grant` (ADR-955), opens the read scope (ADR-753) around the call, and returns the DTO object unserialised. The root callback puts `LocalApi` on `RequestContext`; the factory that builds it is the one `_cli` function allowed to import `squads._services`. `get_service` stays for the commands not moved yet (deleted by TASK-1232). Held by the surface suite through ST4's commands.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Guards: _services imports, renderers, bindings, DTO fields

<!-- sq:subtask:ST3:body -->
`tests/meta` guards (ADR-1224 points 2, 4, 5): (1) no `_cli` module other than the `LocalApi` factory imports `squads._services`, at any position, with a sorted, one-line-per-module pending list of the modules that still do; (2) `_cli/_render/` imports none of `squads._workflow`, `squads._paths` or the configuration model; (3) every operation in the table is bound exactly once; (4) every `_api` DTO field is JSON-native (a tech-lead choice that holds the round-trip property before the parity job exists). The grant guard accepts a grant declared on the operation as well as on the command, until TASK-1232. Falsify each guard once: add a forbidden import, an unbound operation, a `datetime` field, see red, restore. 4 guards.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Item show, list and status end to end

<!-- sq:subtask:ST4:body -->
Move `sq <type> <n> show`, `sq list` and `sq <type> <n> status` end to end as the reference the other tasks copy (ADR-1224 points 1 and 8): parse, refuse what the vocabulary alone decides with exit 2 and today's text, build one request DTO, call through `Api`, render. The item group callback only parses the number into an id. Existence and type of the item, the `--as` roster check and the duplicate-id warning move into the operation. The show DTO carries everything `print_item` reads from the service today (rendered body beside the stored body, discussion, every sub-entity block, view data, the existing `badges` key); `list` carries the rows `build_item_row_json` built; a partial read keeps printing, then the `omitted` line, then exit 4. Also removes the seeded-request code ADR-1225 section 9 lists (attachments, terminal and consoles seeds, `run`'s `seed`, attachment-served `client_path`, `NeedsTerminal` and the two signalling helpers back to `typer.confirm`/`typer.prompt`, the root callback's copying of seeded terminal facts). Tests: the existing `show`, `list` and `status` cases pass unchanged except the added display keys in their `--json` documents.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Display content and renderers for items

<!-- sq:subtask:ST5:body -->
Display content for items (ADR-1224 point 5): a `display` object on the show DTO and every list row (type label, rendered status badge, each declared badge field with its label and rendered badge, the assignee's display name), `columns` (ordered `{key, header}`) on the list response, `rendered_body` beside `body`, and the working-language notice as a `warnings` entry printed on stderr in human mode. Keys appended after the existing ones. Renderers in `_cli/_render/_items.py` take a DTO and a console only; `rich.markdown` is imported only where a body is rendered. Held by ST3's renderer guard and the existing human-output cases.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — JSON output on item status

<!-- sq:subtask:ST6:body -->
`--json` on `sq <type> <n> status`, printing the written item row as the `data` of the status operation. ADR-1224 point 3a lists this key under increment 2, but its own rule gives the flag to the task that moves the command, and status moves here. Test: one whole-document case in `tests/cli/test_item_verbs.py` with `@pytest.mark.covers("<type> status", "--json")`, running the smallest allowed transition; falsified once. 1 test.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T22:34:08Z] `architect` Robert Architect:
  - ADR-1224 point 3a now lists `status --json` under a new increment 0 row (1 key), and increment 2 has 10. Point 8 says increment 0 adds that flag. ST6 and the body no longer contradict the ADR. @tech-lead you can drop the "ADR-1224 point 3a lists it under increment 2" sentence from the body and ST6. No code impact for the python-dev.
- [2026-10-28T23:05:38Z] `python-dev` Elias Python:
  - Increment 0 implemented, all six subtasks done; uncommitted in the tree, task left InProgress.
    - Landed: `squads/_api/` (`_response`, `_api` with `Operation`/`Grant`/`Mode`/`Timeout`/`Api`, `_ops` with marked sections, `_errors` wire form and type/status tables, `_http` encode/parse helpers, `_dto/_base`, `_dto/_display`, `_dto/_items`); `_services/_local_api.py`, `_services/_bindings.py`, `_services/_item_ops.py` (handlers), `_services/_item_dto.py` (projections); `_cli/_calls.py` (the `local_api()` factory, `select_api()`, `call`), `_cli/_render/_items.py` and `_cli/_render/_style.py`. `sq <type> <n> show`, `sq list` and `sq <type> <n> status` (now with `--json`) go through one call each.
    - Seeded-request code removed: `attachments`, `terminal`/`TerminalFacts`, `run(seed=)`, attachment-served reads, `NeedsTerminal`, `confirm_or_signal`/`prompt_or_signal` (back to `typer.confirm`/`typer.prompt`), the root callback's copying.
    - Proof: scratch squad, 125 command lines (human, piped, FORCE_COLOR styled, `--json`, refusals, status writes) before/after: 225 outputs byte-identical, 20 JSON documents differ only by the added `display`/`rendered_body` keys (key order of everything else preserved), 4 differ only by a wall-clock `updated_at`, 1 differs by refusal order (below).
    - Gates: pyright 0 errors, ruff check and format clean, `pytest -n 4 tests/meta tests/cli tests/check` 1566 passed (was 1558: +1 surface case, +7 guard tests).
    - Falsified, each red then green: `_services` import in a non-pending CLI module, in a renderer function, and at module level of `_calls.py`; a stale PENDING entry; `_paths`/`_models._config` import in a renderer; an unbound and a twice-bound operation; a `datetime` DTO field; status answering the pre-move row; an operation declaring a grant. pyright now rejects a binding whose handler does not match its operation (it did not while `BINDINGS` was annotated with `Any`).
    - Edited test expectations, keys added only: `tests/cli/test_list.py::test_json_prints_one_object_per_item` gains `display`. New: `test_status_json_prints_the_moved_items_row`.
    - Deviation 1, `list --json`: the list response is `ItemList{items, columns, hidden}`, and `--json` prints `data.items`, because Tier 3 freezes a bare array and an object would not be an additive change. The same conflict will meet `search`, `tree` and `graph`. @tech-lead: keep printing the rows, or should `columns` live elsewhere (a field on the envelope is ruled out by ADR-1224 point 3)?
    - Deviation 2: a combined error now reports the vocabulary refusal first (`sq task 6 status Sleeping --as ghost` names the unknown status, not the unknown slug), per ADR-1224 point 1.
    - Deviation 3: the item request carries `address` (the token as typed) besides `id` and `type`, so "5 is FEAT-5 (feature), not a task" keeps its text; `type` is required (the any-type form of `sq show` can relax it in increment 1).
    - Deviation 4: `--as` travels as `RequestContext.actor_override` (root callback no longer seeds "system"; `current_actor()` still defaults to it), checked by `adopt_declared_actor()` in the operation.
    - Deviation 5: the working-language notice is in every response's `warnings`; the root callback still prints it for unmoved commands, so printed notices are de-duplicated per invocation. JSON mode prints no response warnings (the duplicate-id warning was human-only).
    - Adopter-visible, for @tech-writer: `status --json`; `display` on `list --json` rows and `display`/`rendered_body` on `show --json`; `display` and `rendered_body` become reserved attribute names (`ROW_ADDED_KEYS`). `Service` gains a 14th base, `ItemOpsMixin`, so the CLAUDE.md architecture line counting 13 is stale.
- [2026-10-28T23:12:35Z, edited 2026-10-28T23:12:49Z] `architect` Robert Architect:
  - @manager CLAUDE.md architecture draft for the main loop to apply (outside the squads-managed region; nothing edited by me). Apply it once the `json_field` follow-up in my next comment lands. Four edits in "Architecture & layering".
    
    1. The layering block becomes:
    
    ```
    _cli → _api ← _services → (index store, backends, rendering, roles, interactions, …)
    _cli → _services only inside _cli/_calls.local_api() (the LocalApi factory)
    _api  imports only pydantic, _errors and _models
    _models  shared; imports only _clock, _errors and _util (and, through _clock, _context)
    ```
    
    2. New bullet, before the `_services/` bullet:
    
    - `_api/` — the command layer's contract (ADR-1224): `_ops.py` is the literal operation table (`Operation[Req, Res]`: name, HTTP method and path, request and response DTOs, composition `Mode`, schema-gate `Grant`, `local_only`, `timeout`, and `json_field`, the one field of `data` that `--json` prints where the frozen document is not an object); `_api.py` holds `Operation` and the one-method `Api` protocol (`call(op, req) -> Response[Res]`); `_response.py` the `Response[T]` envelope (`data`, `omitted`, `warnings`); `_dto/` the frozen, JSON-native pydantic DTOs (`_items.py`, `_display.py` for the display content: labels, rendered badges, columns); `_errors.py` the wire form of an error; `_http.py` `HttpApi`'s wire helpers. It imports nothing above `_models`/`_errors`, so the remote client never imports `_services`.
    
    3. In the `_services/` bullet: the mixin list gains `_item_ops` first (`ItemOpsMixin`: the handlers of the operations, each answering with its DTO) and "the 13 `Service` bases" becomes "the 14 `Service` bases". Append: "`_bindings.py` is the literal table binding each operation to its `Service` handler (`bind(OP, Service.method)`, checked by pyright; a `tests/meta` guard holds every operation bound exactly once); `_local_api.py` is `LocalApi`, which composes the service for `op.mode`, opens the read scope around the call and returns the DTO as an object; `_item_dto.py` projects `Item`/`SubEntity` onto their DTOs with the display content the spec and roster decide. Projections live in `_services`, never in `_cli`."
    
    4. The `_cli/` bullet becomes: "`_cli/` — Typer app (`__init__` wires sub-typers + the root `-C` callback + version notice); one `_module` per command group; `_common.py` has the shared console/error decorator/parsers. A moved command parses, refuses what the vocabulary alone decides (exit 2), builds one request DTO and calls one operation through `_calls.py` (`call`, `select_api`, the `local_api()` factory — the one place `_cli` imports `_services` — and the printers for `--json`, warnings and omissions), then renders. `_render/` holds the renderers: they take a DTO and a console only, and a `tests/meta` guard keeps them off `squads._workflow`, `squads._paths` and the configuration model. Commands not moved yet still reach the service through `get_service`; the `_services` import guard's pending list names their modules and shrinks as they move."
- [2026-10-28T23:13:00Z] `architect` Robert Architect:
  - @python-dev ADR-1224 amended 2026-10-29 for deviation 1 and the reserved names (ADR comment ad65a70). Keep printing the rows; the projection becomes declared, not hand-picked. Follow-up on this task, small:
  - `Operation` gains `json_field: str | None = None`, the field of `data` that `--json` prints. `ITEMS_LIST` sets `json_field="items"`. `calls.print_json` takes the operation and the response and prints `data` whole or that field, so `list` stops calling `print_json(list(response.data.items))` by hand. `data` stays an object (`ItemList`); the HTTP body is the whole `data`.
  - New `tests/meta` guard: every `json_field` names a field of its operation's response type, and only the operations of the 29 commands ADR-1224 point 3 lists may set one (today only `list`). Falsify once each.
  - `rendered_body` moves inside `display`: `ItemShowDisplay` gains `body` (the body with view tags expanded), `ItemShow` drops `rendered_body` from its fields and `TRAILING`, the renderer reads `display.body`, and `rendered_body` leaves `ROW_ADDED_KEYS`. Every later display value on an item row goes inside `display`, so `display` is the one name this refactor reserves. The collision handling stays the existing one (load refusal for a declared attribute or badge field, undeclared stored key kept out of the row); no migration. Update the `show --json` expectations accordingly.
  - Adopter-visible delta for the writer (TASK-1234): `display` is a reserved attribute name; `rendered_body` is not.
- [2026-10-28T23:43:01Z] `python-dev` Elias Python:
  - Round 2 (uncommitted): json_field on Operation (list prints `items`) with its guard; REV-1235 F1-F5, F7, F8 fixed and commented there. Gates: pyright 0, ruff clean; tests/meta+cli+check 1562 passed, 7 failed - all the override-manifest/kind-uniformity tests, because the bundled workflow.toml changed (milestone `target_date` label) while the working version is still the released 0.17.0. Proven on a scratch copy: bumping the working version to 0.18.0 and running scripts/gen_template_manifest.py turns all 59 of those tests green. I did not bump: a version bump is the release owner's call, and regenerating at 0.17.0 would overwrite the released entry. @manager
- [2026-10-29T00:07:16Z] `manager` Catherine Manager:
  - Done 2026-10-29: REV-1235 has nothing open for this task (F1-F8, F12 Verified; F9 Noted; F10/F11 deferred to TASK-1232). Full suite 1570 passed on 98b13ffe.
<!-- sq:discussion:end -->
