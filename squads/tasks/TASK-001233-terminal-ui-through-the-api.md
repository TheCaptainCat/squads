---
id: TASK-1233
sequence_id: 1233
type: task
title: Terminal UI through the Api
status: Done
parent: FEAT-1226
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1224:implements
- TASK-1228:depends-on
- TASK-1230:depends-on
- TASK-1231:depends-on
description: sq ui screens call operations through the Api the root callback selects;
  display from DTOs only
subentities:
- local_id: ST1
  title: sq ui hands the app a per-call API selector
  status: Done
  story: US5
- local_id: ST2
  title: Screens onto operations
  status: Done
  story: US5
- local_id: ST3
  title: _tui under the renderer guard
  status: Done
  story: US4
created_at: '2026-10-28T22:12:42Z'
updated_at: '2026-10-29T13:05:43Z'
---
<!-- sq:body -->
## Goal

Take the terminal UI off the service (ADR-1224 point 7, increment 6): `sq ui` hands the app the API selection of the root callback, every screen makes its calls through `Api`, and the screens show only what the DTOs carry. It needs no operation of its own; it uses the ones TASK-1227, TASK-1228, TASK-1230 and TASK-1231 create. In local mode it runs on `LocalApi`; its behaviour as a daemon client (FEAT-1140 US13) is built in TASK-1219 on the seam this task leaves.

## What it builds

- **The seam for a long session.** The app holds the selection rule, not one selected API (ADR-1224 point 7): each call asks a selector for the API to use. In this task the selector always returns `LocalApi`; TASK-1219 makes it resolve the endpoint per call, re-resolve after a retirement or a refused connection, and reload the catalogs after a retirement. Each `LocalApi` call opens its own read scope, which the reader skips today.
- **Screens onto operations** (ADR-1224 point 7 table):
  - browse tree: the `tree` operation with the same filter fields as `sq tree`; roster nodes call `memory list` per slug, and names with pronouns come from the tree DTO's display names, so the `roster_all`/`operators_all` calls go;
  - reader: the item `show` operation, whose DTO carries the rendered body as `display.body`, the discussion and every sub-entity block;
  - memory reader: `memory show`; search: `search`; board: `board list`;
  - filter screen and search filters: the workflow catalog operations (`types`, `statuses`, `collections`) instead of `svc.spec`.
- Every screen reads the whole `data` of its operation, never the `--json` projection (`json_field`), so `columns` and `hidden` are there for it (ADR-1224 point 3, amended 2026-10-29).
- `sort_siblings` and `populate_tree` work on DTOs instead of `TreeNode` and `Item`; the `[display] pronouns` read of `svc.paths.config` goes.
- `_tui/` joins the renderer guard of TASK-1227: no `_tui` module imports `squads._services`, `squads._workflow`, `squads._paths` or the configuration model.

## Modules touched

`src/squads/_tui/` (`_app.py`, `_browse.py`, `_tree.py`, `_reader.py`, `_memory_reader.py`, `_search.py`, `_board.py`, `_filter.py`), `src/squads/_cli/_ui.py`, the renderer guard in `tests/meta/`. Where a screen needs a field a DTO lacks, it is appended to that DTO's module (owned by the task that made it), never computed in `_tui`. Depends on TASK-1228, TASK-1230 and TASK-1231 (ADR-1224 point 8); runs beside TASK-1232, with no file in common.

## Acceptance

- FEAT-1226 US5: browse, reader, memory reader, search, board and filter screens show what they show today, labels, badges and display names from the results; each screen load is one call; the filter choices come from the catalog operations.
- FEAT-1226 US4: the TUI displays only what the results carry; `_tui` passes the guard.
- ADR-1224 point 7 and point 8 (increment 6), local mode.

## Test approach

- ADR-1172 covers the CLI surface; the TUI has no surface suite in this repository. New tests: 0. The guard extension is the automated proof that no screen reads the service, the vocabulary or the configuration.
- The screens are checked by eye: the operator compares each screen against the released build on this repository's board, in local mode. This is a visual item, so it goes to the operator in review.
- See "Left open".

## Left open

- **Automated TUI tests.** None exist since the suite rebuild, and ADR-1172 does not name a home for them. Recommendation: none in 0.18, the operator's visual check plus the guard; a Textual pilot set, if wanted, is its own decision.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1233 add-subtask "<title>"`; track with `sq task 1233 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq ui hands the app a per-call API selector

<!-- sq:subtask:ST1:body -->
`sq ui` hands the app a per-call API selector instead of a `Service` (ADR-1224 point 7). In this task the selector always returns `LocalApi`, one read scope per call; TASK-1219 ST9 makes it resolve the endpoint per call. `_cli/_ui.py` stops calling `get_service`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Screens onto operations

<!-- sq:subtask:ST2:body -->
Every screen onto operations (ADR-1224 point 7 table): browse tree on `tree` with the same filter fields as `sq tree`, roster nodes on `memory list` per slug with names from the tree DTO (the `roster_all`/`operators_all` calls go); the reader on the item `show` operation (rendered body from `display.body`); every screen reads the whole `data`, never the `--json` projection; the memory reader on `memory show`; search on `search`; the board on `board list`; the filter screen and search filters on `workflow types`, `statuses` and `collections`. `sort_siblings` and `populate_tree` work on DTOs. A field a screen needs and a DTO lacks is appended to that DTO's module, never computed in `_tui`. Checked by eye by the operator against the released build.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — _tui under the renderer guard

<!-- sq:subtask:ST3:body -->
`_tui/` joins the renderer guard of TASK-1227: no `_tui` module imports `squads._services`, `squads._workflow`, `squads._paths` or the configuration model, and the `svc.spec` and `svc.paths.config.display.pronouns` reads are gone. Falsify by adding one such import. Guard extension, no new test.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T23:13:24Z] `architect` Robert Architect:
  - @tech-lead ADR-1224 amended 2026-10-29 (comment ad65a70). For this task: the reader's rendered body is `display.body` on the show DTO (no `rendered_body` key), and every screen reads the whole `data`, never the `--json` projection, so `columns` and `hidden` are there for it.
- [2026-10-28T23:32:36Z] `tech-lead` Olivia Lead:
  - Body updated per the architect (ADR-1224 amended 2026-10-29): the json_field share for this task and the US3 acceptance line ("data, or the field its operation names"). Test count unchanged.
- [2026-10-29T05:49:06Z] `python-dev` Elias Python:
  - - Implemented in d52476d3, on the python-dev worktree branch, not pushed. ST1 and ST3 are Done. ST2 stays InProgress until the operator's eye-check.
    - Seam: `sq ui` builds the app from an `ApiSelector` (`_tui/_session.py`). `Session.call` asks the selector on every call. Today the selector answers one `LocalApi` (the context's `api`, else `select_api()`), and TASK-1219 replaces it. The catalogs (types, statuses, collections) load once at start. The catalogs and the first tree view load before the app starts, so a refusal (for example, no squad) prints as a CLI error, as it did before.
    - Screens: the browse tree uses `tree` plus `memory list` per notebook slug. The reader uses `items.show` (`display.body`, sub-entity blocks, `discussion`). The memory reader uses `memory.show`, search uses `search` and the board uses `board.list`. The filter and search choices come from the catalogs. `_tui` imports no `_services`, `_workflow`, `_paths` or config model, and nothing from `_badges`, `_discussion`, `_pronouns`, `_memory` or `_board` either.
    - DTO fields appended for the TUI: `TreeRequest.label` (honoured by the handler and the hidden count), and `TreeNode.slug` (a role's or operator's notebook slug, `None` elsewhere), `TreeNode.closed` (hidden by default) and `TreeNode.updated_at`. This adds 3 keys to every node of `sq tree --json` and of the subtree view source. Pronouns are now gated on role and operator, which fixes a skill that shares a role's slug picking up that role's pronouns.
    - Guard: the renderer guard now also scans `_tui/`. I falsified it by adding a `_workflow` import to `_tui/_board.py`, and it failed as expected. Tests added: 0. The suite stays at 1634.
    - I captured every screen headless, before and after, on a scratch squad (Textual pilot driving the real `sq ui`: tree labels and spans, the reader tabs for each node, memory, board, search with a type filter, the filter choices, and 9 filter or sort states). Everything is identical except one case: a status filter on a closed status (Done) now shows the matching items, because the `tree` operation includes closed items when filtering by status, as `sq tree --status Done` does. Before, it showed an empty tree.
    - The second change is not in the capture. An unknown assignee in the filter now shows an error toast and keeps the previous view. Before, it showed an empty tree.
    - For the operator's eye-check, against the released build: the browse tree (groups, dimming, pronouns, memory counts), the reader tabs, a memory entry, `f` with each sort, `/` search with a hit opened, `b` board, and `q`.
- [2026-10-29T06:54:55Z] `op-pierre` Pierre Chat:
  - 2026-10-29: no TUI test suite in 0.18. The TUI is held by the import guard, the surface tests of the operations it calls, and the operator's eye-check (list on REV-1235). A TUI suite is decided later, with its own rule in ADR-1172.
- [2026-10-29T13:05:41Z] `op-pierre` Pierre Chat:
  - 2026-10-29: TUI eye-check OK — sq ui on this board in 0.18.0 matches 0.17.0 apart from the changelogged differences.
<!-- sq:discussion:end -->
