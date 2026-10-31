---
id: TASK-1231
sequence_id: 1231
type: task
title: Board, memory, workflow and maintenance reads on operations
status: Done
parent: FEAT-1226
author: tech-lead
assignee: python-dev
refs:
- ADR-1224:implements
- TASK-1227:depends-on
description: board, memory, workflow catalogs and views, overrides, reflog, check,
  sync and package-data commands on operations, with --json
subentities:
- local_id: ST1
  title: board and memory
  status: Done
  maps_to: US1
- local_id: ST2
  title: workflow catalogs and views
  status: Done
  maps_to: US1
- local_id: ST3
  title: override, reflog, check and sync
  status: Done
  maps_to: US1
- local_id: ST4
  title: Views and catalogs rendered by the operation
  status: Done
  maps_to: US4
- local_id: ST5
  title: JSON output on the 12 remaining keys
  status: Done
  maps_to: US2
created_at: '2026-10-28T22:12:40Z'
updated_at: '2026-10-29T05:37:44Z'
priority: high
---
<!-- sq:body -->
## Goal

Move the rest of the squad's readers and writers onto one operation each (ADR-1224 point 8, increment 4): `board` (`list`, `post`, `clear`), `memory` (`list`, `search`, `show`, `add`, `forget`), the `workflow` catalogs and views (`show`, `types`, `statuses`, `lifecycles`, `collections`, `ref-kinds`, `subentity-kinds`, `roles`, `views`, `view`, `lint`), `override` (`list`, `diff`, `scaffold`, `update`), `reflog`, `check` and `sync`; and give `--json` to the 12 keys that lack it, the three package-data commands included. The terminal UI (TASK-1233) depends on the board, memory and workflow-catalog operations made here.

## What it builds

- One operation per command in the squad-state section of `_api/_ops.py`, bound in `_services/_bindings.py`. Routes per ADR-1225 section 1: `GET /v1/workflow/{catalog}` for the catalogs, `GET` for every read, `POST`/`DELETE` for board and memory writes, `POST /v1/squad/sync` for `sync`; the others where the table assigns them. Timeout class `standard`.
- Composition modes move from the CLI to the operation (ADR-1224 point 4): `check` keeps its own composition and fallback order (`CHECK_FALLBACKS`), the catalogs and `workflow lint` work as today where they run outside a squad or on a broken override, `override` commands keep their bypass. The CLI stops calling `get_service_bypassing_index_cross_check` for these commands.
- `check` returns its report as a DTO, and the exit code 3 for findings comes from it (ADR-1224 point 3).
- Display (ADR-1224 point 5): `workflow view` and `workflow show` output is rendered by the operation, through the squad's `.overrides/templates/`; the catalogs carry their labels and headers; `reflog` and the memory and board listings carry `columns` where their tables come from the spec.
- **`--json` on 12 keys** (ADR-1224 point 3a): `board post`, `board clear`, `memory add`, `memory forget`, `override scaffold`, `override update`, `sync`, `workflow show`, `workflow lint`, `docs`, `migrate help`, `migrate chlog`. A write prints what it wrote; `sync` and `workflow lint` print their report; the package-data commands print their text or index as data. Their DTOs live in `_api/_dto/_package.py` and are built by a function beside the data they read (`_docfiles` for `docs`, the migration registry for `migrate help` and `migrate chlog`), called directly by the command: no operation, no route, no call (ADR-1224 point 3a). The import-edge table gains `_docfiles -> _api` and `_migrations -> _api`.
- **`json_field`** (ADR-1224 points 3 and 4, amended 2026-10-29): `board list`, `memory list`, `memory search`, `override list`, `override diff`, `reflog`, `check` and the eight `workflow` catalogs keep their bare-array `--json` by setting `json_field = "items"`; `workflow view` sets `json_field = "source"`, the resolved source in its own shape, beside the rendered output human mode prints. `check`'s exit 3 still comes from the DTO. The 12 new flags print `data` whole, an object, and set none; the package-data DTOs are not operations and print whole.
- DTOs in `_api/_dto/_board.py`, `_memory.py`, `_workflow.py`, `_overrides.py`, `_reflog.py`, `_check.py`, `_package.py`; renderers in the matching `_cli/_render/` modules.

## Modules touched

Edited: `_cli/_board.py`, `_cli/_memory.py`, `_cli/_workflow_cmd.py`, `_cli/_override.py`, `_cli/_main.py` (`reflog`, `check`, `sync`, `docs` and their helpers only), `_cli/_migrate.py` (`help` and `chlog` only; the migrate operations are TASK-1232's), the squad-state section of `_api/_ops.py` and `_services/_bindings.py`, the matching classes of `_services/_results.py` (`ReflogEntry` and the check and board results), `_docfiles.py` and `_migrations/_registry.py` (the package-data DTO builders), the import-edge table, `tests/cli/test_board.py`, `test_memory.py`, `test_workflow.py`, `test_override.py`, `test_reflog.py`, `test_check.py`, `test_sync.py`, `test_docs_ui.py`, `test_migrate.py` (the `help` and `chlog` cases only). Runs beside TASK-1228 and TASK-1230; it shares `_cli/_main.py` with TASK-1228, in different functions.


## Acceptance

- FEAT-1226 US1 for every command listed: one call (none for the three package-data commands), `check` exit 3 on findings, output and error text unchanged.
- FEAT-1226 US2: the 12 flags print the written resource, the report, or the package text or index.
- FEAT-1226 US3: `--json` prints `data`, or the field its operation names.
- FEAT-1226 US4: view and workflow output rendered by the operation through the squad's templates; renderers pass the `_cli/_render/` guard.
- ADR-1224 points 1, 3, 3a, 4, 5 and 8 (increment 4).

## Test approach (ADR-1172)

- Existing surface suite as the proof, including the override-file reads rule 5 allows; only additive `--json` expectation edits.
- New surface cases: 12, one whole-document case per new flag in its group's module with its `covers` marker.
- Guards: none new; the pending list loses the modules this task finishes.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1231 add-subtask "<title>"`; track with `sq task 1231 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — board and memory

<!-- sq:subtask:ST1:body -->
`board` (`list`, `post`, `clear`) and `memory` (`list`, `search`, `show`, `add`, `forget`) on one operation each. `board list`, `memory list` and `memory show` are the operations the terminal UI calls (TASK-1233). Listing `columns` where they come from the spec. DTOs in `_api/_dto/_board.py`, `_memory.py`. Existing cases pass.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — workflow catalogs and views

<!-- sq:subtask:ST2:body -->
The `workflow` catalogs and views (`show`, `types`, `statuses`, `lifecycles`, `collections`, `ref-kinds`, `subentity-kinds`, `roles`, `views`, `view`, `lint`) on one operation each, `GET /v1/workflow/{catalog}` for the catalogs. They keep working where they do today outside a squad or on a broken override, through the operation's composition mode. `types`, `statuses` and `collections` feed the terminal UI's filter screen. DTOs in `_api/_dto/_workflow.py`. Existing cases pass.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — override, reflog, check and sync

<!-- sq:subtask:ST3:body -->
`override` (`list`, `diff`, `scaffold`, `update`), `reflog`, `check` and `sync` on one operation each. `check` keeps its own composition and fallback order inside the operation, and its report DTO gives exit 3 on findings. `sync` and the override writes regenerate or stamp files inside the operation. The CLI stops calling `get_service_bypassing_index_cross_check` for these commands. DTOs in `_api/_dto/_overrides.py`, `_reflog.py`, `_check.py`. Existing cases pass, including the override-file reads ADR-1172 rule 5 allows.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Views and catalogs rendered by the operation

<!-- sq:subtask:ST4:body -->
Display rendered by the operation (ADR-1224 point 5): `workflow view` and `workflow show` output rendered through the squad's `.overrides/templates/`, catalog labels and headers, `columns` on `reflog` and the board and memory listings. The renderers take only the DTO. Held by TASK-1227's guard and the existing human-output cases.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — JSON output on the 12 remaining keys

<!-- sq:subtask:ST5:body -->
`--json` on 12 keys (ADR-1224 point 3a): `board post`, `board clear`, `memory add`, `memory forget`, `override scaffold`, `override update`, `sync`, `workflow show`, `workflow lint`, `docs`, `migrate help`, `migrate chlog`. The three package-data commands make no call: their DTOs in `_api/_dto/_package.py` are built by a function in `_docfiles` (`docs`) and beside the migration registry (`migrate help`, `migrate chlog`), called directly by the command, with no operation or route; the import-edge table gains `_docfiles -> _api` and `_migrations -> _api` (ADR-1224 point 3a). Tests: one whole-document case per key with its `covers` marker in its group's module. Falsify each once. 12 tests.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T22:34:06Z] `architect` Robert Architect:
  - Settled your open point on the package-data DTOs in ADR-1224 point 3a (amended 2026-10-28), as you recommended. DTOs live in `_api/_dto/_package.py` and are built by a function beside the data: `_docfiles` for `docs`, the migration registry for `migrate help` and `migrate chlog`. The command calls it directly. No operation, no route, no call. Add the `_docfiles -> _api` and `_migrations -> _api` rows to the import-edge table.
  - @tech-lead please update the task body and ST5.
- [2026-10-28T22:36:27Z] `tech-lead` Olivia Lead:
  - Body and ST5 updated per the architect (7ffc067): package-data DTOs in _api/_dto/_package.py, built beside _docfiles and the migration registry, no operation or route; two new import-edge rows. Test count unchanged (12).
- [2026-10-28T23:13:23Z] `architect` Robert Architect:
  - @tech-lead ADR-1224 amended 2026-10-29 (comment ad65a70), points 3 and 4. For this task: `board list`, `memory list`, `memory search`, `override list`, `override diff`, `reflog`, `check` and the eight `workflow` catalogs keep their bare-array `--json` by setting the operation's new `json_field` (`items`); `workflow view` sets `json_field="source"`, the resolved source in its own shape, beside the rendered output human mode prints. `check`'s exit 3 still comes from the DTO. The 12 new flags print `data` whole, an object, and set none; the package-data DTOs are not operations and print whole. The US3 acceptance line should read "`data`, or the field its operation names".
- [2026-10-28T23:32:35Z] `tech-lead` Olivia Lead:
  - Body updated per the architect (ADR-1224 amended 2026-10-29): the json_field share for this task and the US3 acceptance line ("data, or the field its operation names"). Test count unchanged.
- [2026-10-29T00:41:05Z] `python-dev` Elias Python:
  - - Landed on branch `worktree-agent-adba49678e342becd`, commit 512aec7e, rebased onto `release/0.18` 77fac31d (my worktree had been created from `main`). Not pushed. Task left InProgress, all five subtasks Done.
    - What changed:
      - 26 operations in the squad-state section of `_api/_ops.py`, bound in `_services/_bindings.py`. Their handlers are on a new `SquadStateOpsMixin` (`_services/_squad_ops.py`), the 15th `Service` base.
      - Catalog projections are in `_services/_catalogs.py`, the `workflow view` source JSON in `_services/_view_source.py`.
      - DTO modules `_api/_dto/_board`, `_memory`, `_workflow`, `_overrides`, `_reflog`, `_check` (which also holds sync), `_package`. Renderers in the matching `_cli/_render/` modules.
      - `check` exits 3 from `CheckReport.errors`. Each catalog carries its `columns`. A status row carries `display.intent`. `workflow view` and `workflow show` are rendered by the operation.
      - `json_field="items"` on board list, memory list and search, override list and diff, reflog, check and the 8 catalogs. `json_field="source"` on workflow view.
      - The package-data builders are `_docfiles.doc_index()`/`doc()` and `_migrations._registry.migration_index()`/`manual_steps()`. They make no call.
    - Composition modes, changed outside my sections (deviation):
      - `_api.Mode` gains `CHECK` and `VOCABULARY`. `LocalApi` composes `CHECK` by the `CHECK_FALLBACKS` rule.
      - `VOCABULARY` refuses on the invocation's `spec_error`. Otherwise it is the normal service, falling back to `PLAYBOOK_UNAVAILABLE`. Outside a squad it uses `compose_squadless()`, a service over the bundled documents.
      - The refusal travels as `ServiceCore.refusal`. The catalogs and cheatsheet use `VOCABULARY`, `check` uses `CHECK`, and lint and override list/diff/update use `BUNDLED_FALLBACK`.
      - The override operations carry the `NO_SQUAD_STATE` behind grant, and their CLI decorators stay until TASK-1232.
    - Parity: 159 command lines run on scratch squads from the parent commit and from this one. The lines cover human, piped, `FORCE_COLOR`, `NO_COLOR` and `--json` output, 4 overrides with one drifted, a broken workflow override, outside a squad, `check` with findings (exit 3) and clean, writes, and the refusals.
      - 157 outputs are byte-identical.
      - `workflow statuses --json` only gains `display` on each row.
      - `memory ghost show` without a slug now gives the usage error (exit 2) before the roster check, because the group callback only parses (ADR-1224 point 1).
    - Tests: +12, one whole-document case per new `--json` flag (1571 to 1583). Each was falsified (code mutated, test red, restored, green).
      - Existing expectation edited, keys added only: `test_statuses_json_prints_one_object_per_status` gains `display`.
      - Stale bare markers dropped: `covers("sync")` x3, `covers("migrate help")`, `covers("workflow lint")`.
      - Guards: `json_field` ALLOWED +16, `_workflow_cmd.py` leaves PENDING, the grant guard gets 3 operation rows, the edge table adds `_docfiles/_migrations -> _api`, `_migrations -> _util` and `_services -> _overrides top` and drops 9 dead `_cli` rows. Also updated: check-finding sites, the repair-corridor site (sync moved to `render_sync`) and one subentity-literal allowlist row.
      - Gates: pyright 0 errors; ruff check and format clean; `pytest -n 2 tests/meta tests/cli tests/check` 1583 passed.
    - Other deviations:
      - No `columns` on the board, memory and reflog listings: they print lines, not tables, and nothing in them comes from the spec.
      - `workflow view --json` keeps the source shapes as they were (the tree node and `show` shape without `display`), so TASK-1228's tree node `display` will not reach it.
      - `workflow view` now computes both the source and the rendered output, so a template error also fails `--json`.
      - Memory add and forget answer `{role, memory}` and `{role, slug}`.
      - `_cli/_common.get_squad_paths` is now unused. Left for TASK-1232.
    - Adopter-visible: `--json` on board post/clear, memory add/forget, override scaffold/update, sync, workflow show/lint, docs, migrate help/chlog; `display.intent` on `workflow statuses --json` rows. CLAUDE.md's count of `Service` bases is now 15.
    - @tech-lead for review; @tech-writer for the changelog lines above.
- [2026-10-29T05:37:44Z] `manager` Catherine Manager:
  - Done 2026-10-29: its REV-1235 findings are Verified, Noted or deferred with a home; full suite 1634 passed on e6462b5e.
<!-- sq:discussion:end -->
