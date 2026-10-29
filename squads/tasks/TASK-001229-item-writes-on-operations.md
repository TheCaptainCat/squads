---
id: TASK-1229
sequence_id: 1229
type: task
title: Item writes on operations
status: Ready
parent: FEAT-1226
author: tech-lead
priority: high
refs:
- ADR-1224:implements
- TASK-1227:depends-on
- TASK-1228:depends-on
description: create, update, body, retype, remove, refs, views, comment and sub-entity
  verbs on one operation each, with --json
subentities:
- local_id: ST1
  title: create
  status: Todo
  story: US1
- local_id: ST2
  title: update, body, retype, remove, refs and views
  status: Todo
  story: US1
- local_id: ST3
  title: Comment verbs on every host, confirmed remove
  status: Todo
  story: US1
- local_id: ST4
  title: Sub-entity verbs
  status: Todo
  story: US1
- local_id: ST5
  title: JSON output on the 10 item writes
  status: Todo
  story: US2
created_at: '2026-10-28T22:12:38Z'
updated_at: '2026-10-28T23:32:33Z'
---
<!-- sq:body -->
## Goal

Move the item writes onto one operation each (ADR-1224 point 8, increment 2) and give them `--json`: `sq create <type>` (and `create guide`), `<type> <n> update`, `body`, `retype`, `remove`, `ref add`/`ref rm`, `view add`/`view disable`, the comment verbs on every host, and the sub-entity verbs (`add-<kind>`, `<kind> <k> update`, `body`, `remove`). `status` moved with TASK-1227. A write prints the resource it wrote, built from the read rows TASK-1227 and TASK-1228 define.

## What it builds

- One operation per command in the item-writes section of `_api/_ops.py`, bound in `_services/_bindings.py`, routes per ADR-1225 section 1: `POST /v1/items` (type in the body), `PATCH /v1/items/{id}`, `PUT …/body`, `POST …/retype`, `DELETE /v1/items/{id}`, `POST …/refs` and `DELETE …/refs/{target}`, the views sub-resource, `POST`/`GET`/`PATCH`/`DELETE` on `…/comments[/{hash}]` for items and `/v1/{roles,skills,operators}/{addr}/comments[/{hash}]` for roster hosts, and `/v1/items/{id}/subentities[/{local}]` with `/body` and `/comments` under it. Timeout class `standard`.
- File text (`--file`, `-`) is read by the CLI and sent in the request DTO's text field (`body: str`); nothing is attached and the operation never reads a client path (ADR-1225 section 2).
- What the CLI checks against the squad today moves into the operation (ADR-1224 point 1): existence and type of the item, roster checks on `--as`, `--author`, `--assignee`, whether there is an assignee to clear, the duplicate-id warning.
- **Prompts sit between calls, never inside one.** Item removal and sub-entity removal ask first and then make their one call. `comment remove` without `--yes` makes two: a preview operation returning the comments the hash prefix selects with their full hash, then, once the user confirms, the remove operation sent with that full hash, so a comment edited or removed in between answers not-found and nothing is removed (ADR-1224 point 1, ADR-1225 section 3 "comment remove after a confirmation"). With `--yes`, one call resolving the typed prefix.
- **Comment verbs on every host.** `register_comment_verbs` and `register_comment_group` are one code path for items, sub-entities, roles, skills and operators, so this task moves them for every host (`<host> comment` is one ADR-1172 key). On a roster host the comment operations take the parsed `addr` from the start and resolve it themselves, an unresolved address answering not-found with today's text; they are served at `/v1/roles/{addr}/comments[/{hash}]` and the skill and operator equivalents, with the same methods and DTOs as the item comment routes, the roster kind given by the route, never by a request field (ADR-1225 section 1). They are bound the way TASK-1230 binds the shared roster verbs.
- **`--json` on 10 keys** (ADR-1224 point 3a, minus `status`): `<host> comment` when it adds a comment, `<type> update`, `body`, `retype`, `ref add`, `ref rm`, `view add`, `view disable`, `<type> <kind> update`, `<type> <kind> body`. A write prints the item row or sub-entity object it wrote. `--json` on the comment group given together with a verb (`edit`, `remove`, `show`) is a usage error, exit 2.
- **`json_field`** (ADR-1224 points 3 and 4, amended 2026-10-29): `<host> comment <hash> remove --json` keeps its bare array of removed comments by setting `json_field = "items"`; every other write prints `data` whole and sets none. A write that prints an item row puts any display value inside `display`; an item row reserves no other name.
- DTOs: write requests and the comment preview in `_api/_dto/_item_writes.py` and `_api/_dto/_comment_writes.py`; responses reuse the item row, sub-entity and comment DTOs (appending fields only where a write needs one). Renderers in `_cli/_render/_writes.py`.

## Modules touched

Edited: `_cli/_create.py`, `_cli/_items.py` (update, body, retype, remove, ref and view sub-apps, the sub-entity verbs and `add-<kind>`), `_cli/_common.py` (the comment registrars and the comment remove flow only), the item-writes sections of `_api/_ops.py` and `_services/_bindings.py`, `CreateResult` and the write results of `_services/_results.py`, `tests/cli/test_create.py`, `test_item_verbs.py`, `test_subentity_verbs.py`, `test_comment_verbs.py`. Depends on TASK-1228, because the write responses reuse its rows and both edit `_cli/_items.py`.


## Acceptance

- FEAT-1226 US1: one call per command, `comment remove` without `--yes` previews then removes exactly the comments shown; human output, exit codes and error text unchanged.
- FEAT-1226 US2: the 10 flags print the written resource; the comment-group usage error.
- FEAT-1226 US3: `--json` prints `data`, or the field its operation names.
- FEAT-1140 US2, sixth bullet, in local mode: a comment changed between preview and confirmation is not removed.
- ADR-1224 points 1, 3a and 8 (increment 2); ADR-1225 sections 2 and 3.

## Test approach (ADR-1172)

- Existing surface suite as the proof; only additive `--json` expectation edits (display keys).
- New surface cases: 11. One whole-document case per new flag (10), in the module of its command group with its `covers` marker, each running the smallest write the command accepts; one refusal case for `--json` with a comment verb.
- Not reachable by a surface in local mode: a comment edited between preview and confirmation (the prompt and both calls run in one process). Built and held by review; the not-found answer itself is the error table's 404 row in TASK-1218's route tests.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1229 add-subtask "<title>"`; track with `sq task 1229 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — create

<!-- sq:subtask:ST1:body -->
`sq create <type>` and `sq create guide` on one operation (`POST /v1/items`, the type in the body). Roster checks on `--author`, `--assignee` and `--as`, the parent and story resolution, and the duplicate-id warning move into the operation; `-m`/`--file` text is read by the CLI and sent in the request DTO. `--json` already exists and keeps printing the created item. Existing cases in `tests/cli/test_create.py` pass; only display keys are added.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — update, body, retype, remove, refs and views

<!-- sq:subtask:ST2:body -->
`<type> <n> update`, `body`, `retype`, `remove`, `ref add`/`ref rm` and `view add`/`view disable` on one operation each (`PATCH /v1/items/{id}`, `PUT …/body`, `POST …/retype`, `DELETE /v1/items/{id}`, `POST …/refs`, `DELETE …/refs/{target}`, the views sub-resource). Whether there is an assignee to clear and the roster checks move into the operation. `remove` asks before its one call. Each write's response is the item row it wrote. Existing cases pass.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Comment verbs on every host, confirmed remove

<!-- sq:subtask:ST3:body -->
The comment verbs (add, `show`, `edit`, `remove`, `status`) on every host, through the one registrar pair (`register_comment_verbs`, `register_comment_group`), on `/v1/items/{id}/comments[/{hash}]` and its sub-entity form. `comment remove` without `--yes` makes two calls: a preview operation returning the selected comments with their full hash, then, after the user confirms, the remove operation sent with that full hash; a comment edited or removed in between answers not-found and nothing is removed (ADR-1225 section 3). With `--yes`, one call. On roster hosts the operations take the parsed `addr` from the start, served at `/v1/roles/{addr}/comments[/{hash}]` and the skill and operator equivalents, the kind from the route, an unresolved address answering not-found with today's text (ADR-1225 section 1). Existing cases pass.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Sub-entity verbs

<!-- sq:subtask:ST4:body -->
The sub-entity verbs (`add-<kind>`, `<kind> <k> update`, `body`, `remove`, and the sub-entity comment address) on one operation each, under `/v1/items/{id}/subentities[/{local}]` with `/body`. `--story` resolution against the parent's stories and the severity and deferral checks happen in the operation; vocabulary-only refusals stay exit 2 in the CLI. `remove` asks before its one call. Responses are the sub-entity object TASK-1228 defines. Existing cases pass.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — JSON output on the 10 item writes

<!-- sq:subtask:ST5:body -->
`--json` on 10 keys (ADR-1224 point 3a, `status` excepted): `<host> comment` when it adds, `<type> update`, `body`, `retype`, `ref add`, `ref rm`, `view add`, `view disable`, `<type> <kind> update`, `<type> <kind> body`, each printing the resource written. `--json` on the comment group together with `edit`, `remove` or `show` is a usage error, exit 2. Tests: one whole-document case per flag with its `covers` marker, smallest write, in the group's module (10), plus the usage-error refusal (1). Falsify each once. 11 tests.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T22:34:04Z] `architect` Robert Architect:
  - Settled your open point on the roster comment route in ADR-1225 section 1 (amended 2026-10-28). Roster comments use `/v1/roles/{addr}/comments[/{hash}]` and the skill and operator equivalents, with the same methods and DTOs as the item comment routes, `addr` in place of `id`.
  - The roster kind belongs to the operation (its path), never to a request field, so the address is `addr` alone. The operation resolves it, and an unresolved address answers 404 with today's text. Bind them the way TASK-1230 binds the shared roster verbs (status, body, remove).
  - Consequence: if the roster comment operations take `addr` from the start, the CLI can pass the parsed address right away, and the address switch TASK-1230 carries goes away. @tech-lead please update the task body and the ST3 note.
- [2026-10-28T22:36:25Z] `tech-lead` Olivia Lead:
  - Body and ST3 updated per the architect (3f2b004): roster comment operations take the parsed addr from the start, routes /v1/{roles,skills,operators}/{addr}/comments[/{hash}]; the TASK-1230 hand-off is gone. Test count unchanged (11).
- [2026-10-28T23:13:21Z] `architect` Robert Architect:
  - @tech-lead ADR-1224 amended 2026-10-29 (comment ad65a70), points 2, 3 and 4. For this task: `<host> comment <hash> remove --json` keeps its bare array of removed comments by setting the operation's new `json_field` (`items`); every other write prints `data` whole and sets none. Write responses that print an item row put any display value inside `display` (an item row reserves no other name). The US3 acceptance line should read "`data`, or the field its operation names".
- [2026-10-28T23:32:33Z] `tech-lead` Olivia Lead:
  - Body updated per the architect (ADR-1224 amended 2026-10-29): the json_field share for this task and the US3 acceptance line ("data, or the field its operation names"). Test count unchanged.
<!-- sq:discussion:end -->
