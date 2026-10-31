---
id: TASK-1228
sequence_id: 1228
type: task
title: Item reads on operations
status: Done
parent: FEAT-1226
author: tech-lead
assignee: python-dev
refs:
- ADR-1224:implements
- TASK-1227:depends-on
description: sq show, tree, graph, search, inbox, mine, blocked, workload, refs, comments
  and sub-entity reads each call one operation
subentities:
- local_id: ST1
  title: show, tree, graph and search
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST2
  title: inbox, mine, blocked and workload
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST3
  title: refs, comments and sub-entity reads
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST4
  title: Display content for item reads
  status: Done
  assignee: python-dev
  maps_to: US4
created_at: '2026-10-28T22:12:37Z'
updated_at: '2026-10-29T05:27:28Z'
priority: high
---
<!-- sq:body -->
## Goal

Move the item read commands onto one operation each (ADR-1224 point 8, increment 1), following the pattern TASK-1227 sets: `sq show <id>`, `tree`, `graph`, `search`, `inbox`, `mine`, `blocked`, `workload`, `<type> <n> refs`, `<type> <n> comments`, and the sub-entity reads (`<type> <n> <kinds>`, `<type> <n> <kind> <k> show`). Every one of them already has `--json`, so no flag is added here. The write task (TASK-1229) reuses the sub-entity and comment rows this task defines.

## What it builds

- One operation per command in the item-reads section of `_api/_ops.py`, bound in `_services/_bindings.py`, all `GET` with flat request DTOs (filters as query fields, repeated list fields such as `badge`), routes per ADR-1225 section 1 (`/v1/tree`, `/v1/graph`, `/v1/search`, `/v1/inbox/{slug}`, `/v1/mine/{slug}`, `/v1/items/{id}/refs`, `/v1/items/{id}/comments`, `/v1/items/{id}/subentities[/{local}]`; `blocked` and `workload` at the paths the table assigns). Timeout class `standard`.
- What each command calls more than once today folds into its one operation: `tree`'s hidden count and its `--json` blocked flags; `sq show`'s eight reads (it reuses the item show operation of TASK-1227); the roster lookups behind `inbox`/`mine` slugs, which become the operation's not-found error.
- The `tree` request takes the same filter fields as `sq tree` (filter, `include_closed`), because the terminal UI's browse screen calls it (ADR-1224 point 7).
- **`json_field`** (ADR-1224 points 3 and 4, amended 2026-10-29): `data` is always an object. `tree`, `search`, `inbox`, `mine`, `blocked`, `workload`, `<type> <n> comments` and the sub-entity lists keep their bare-array `--json` by setting `json_field = "items"` (the root nodes for `tree`, the hits for `search`), so `columns`, `hidden` and any other sibling reach human mode and HTTP only. `graph`, `refs`, `sq show` and sub-entity show are objects and set none. A display value added to an item row (the `mine` rows) goes inside `display`, never beside it.
- DTOs in new per-resource modules: `_api/_dto/_tree.py`, `_graph.py`, `_search.py`, `_queues.py` (inbox, mine, blocked, workload), `_subentities.py`, `_comments.py`, `_refs.py`. Fields in today's emitted order, which Tier 3 freezes for `search`, `tree` and `graph`; display keys appended.
- Display content (ADR-1224 point 5): the `display` object on every tree node, graph node, search hit and sub-entity; `columns` on `workload` and the sub-entity summaries; a sub-entity kind's plural and container heading; a ref kind's label on `refs` rows and graph edges. The tree DTO's display names carry pronouns as `[display] pronouns` says, which the terminal UI needs instead of its two roster calls.
- Renderers in new modules `_cli/_render/_tree.py`, `_graph.py`, `_search.py`, `_queues.py`, `_subentities.py`, `_comments.py`, `_refs.py`.
- The `_cli` modules this task finishes leave the `_services` import pending list.

## Modules touched

New: the DTO and renderer modules above. Edited: `_cli/_main.py` (`show_any`, `tree`, `graph`, `search`, `inbox`, `mine`, `blocked`, `workload` and their private helpers such as `_tree_hidden_count`, `_mine_row_json`, `_attach_graph_node`), `_cli/_items.py` (refs, the plural listing, sub-entity show, the sub-entity group callback becomes parse-only), `_cli/_common.py` (the `comments` listing registration only), the item-reads section of `_api/_ops.py` and `_services/_bindings.py`, the read-side classes of `_services/_results.py` (`TreeNode`, `SubentityDetail`, `SearchHit`, `WorkloadRow`, `InboxLine`, `MineRow` and the graph results get DTO counterparts or move), `tests/cli/` modules of these groups only. Shared `_common.py` helpers are left in place for TASK-1232 to delete.

## Acceptance

- FEAT-1226 US1 for every command listed: one call, exit-2 refusals unchanged, existence and roster checks in the operation, partial reads still exit 4 after printing, warnings on stderr.
- FEAT-1226 US3: each `--json` prints `data`, or the field its operation names.
- FEAT-1226 US4: display on tree nodes, graph nodes, search hits and sub-entities; columns; kind plurals and headings; ref-kind labels; renderers pass the `_cli/_render/` guard.
- ADR-1224 points 1, 3, 5 and 8 (increment 1). Tier 3 order of `search`, `tree` and `graph` unchanged.

## Test approach (ADR-1172)

- The existing surface suite is the proof. Expected edits: only the whole-document `--json` expectations of these commands, by added display keys; review checks every edited expectation only adds keys.
- New surface cases: 0 (every command here already has `--json` and its cases).
- Guards: none new; the `_services` pending list shrinks.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1228 add-subtask "<title>"`; track with `sq task 1228 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — show, tree, graph and search

<!-- sq:subtask:ST1:body -->
`sq show <id>`, `tree`, `graph` and `search` on one operation each (`GET /v1/items/{id}` reused from TASK-1227 for `sq show`, `GET /v1/tree`, `GET /v1/graph`, `GET /v1/search`). `tree` folds its hidden count and its `--json` blocked flags into the one operation, and its request takes the same filter fields as `sq tree` (the terminal UI calls it). Fields in today's emitted order, which Tier 3 freezes for these three. DTOs in `_api/_dto/_tree.py`, `_graph.py`, `_search.py`; renderers in the matching `_cli/_render/` modules. Existing cases pass; only display keys are added to their `--json` expectations.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — inbox, mine, blocked and workload

<!-- sq:subtask:ST2:body -->
`inbox`, `mine`, `blocked` and `workload` on one operation each (`GET /v1/inbox/{slug}`, `GET /v1/mine/{slug}`, and the paths the table assigns `blocked` and `workload`). The slug's roster check becomes the operation's not-found error with today's message; `_mine_row_json` stops being called. DTOs in `_api/_dto/_queues.py`, renderer in `_cli/_render/_queues.py`. Existing cases pass; only display keys are added.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — refs, comments and sub-entity reads

<!-- sq:subtask:ST3:body -->
`<type> <n> refs`, `<type> <n> comments` and the sub-entity reads (`<type> <n> <kinds>`, `<type> <n> <kind> <k> show`) on one operation each, under `/v1/items/{id}/refs`, `…/comments` and `…/subentities[/{local}]`. The sub-entity group callback only parses. The sub-entity object and the comment row defined here are the shapes TASK-1229's writes return. DTOs in `_api/_dto/_refs.py`, `_comments.py`, `_subentities.py`; renderers in the matching modules. Existing cases pass; only display keys are added.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Display content for item reads

<!-- sq:subtask:ST4:body -->
Display content for the item reads (ADR-1224 point 5): the `display` object on every tree node, graph node, search hit and sub-entity; `columns` on `workload` and the sub-entity summaries; a sub-entity kind's plural and container heading; a ref kind's label on `refs` rows and graph edges; display names with pronouns applied or left out per `[display] pronouns` on tree nodes. Renderers read only the DTO (TASK-1227's guard). Held by the guard and the existing human-output cases.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T23:13:20Z] `architect` Robert Architect:
  - @tech-lead ADR-1224 amended 2026-10-29 (comment ad65a70), points 2, 3 and 4. For this task: `data` is always an object; `tree`, `search`, `inbox`, `mine`, `blocked`, `workload`, `<type> <n> comments` and the sub-entity lists keep their bare-array `--json` by setting the operation's new `json_field` (`items`: the root nodes for `tree`, the hits for `search`), so `columns`, `hidden` and any other sibling go to human mode and HTTP only. `graph`, `refs`, `sq show` and sub-entity show are objects and set none. The US3 acceptance line ("each `--json` prints the operation's `data`") should read "`data`, or the field its operation names". Any display value added to an item row (`mine` rows) goes inside `display`, never beside it.
- [2026-10-28T23:32:32Z] `tech-lead` Olivia Lead:
  - Body updated per the architect (ADR-1224 amended 2026-10-29): the json_field share for this task and the US3 acceptance line ("data, or the field its operation names"). Test count unchanged.
- [2026-10-29T00:33:00Z] `python-dev` Elias Python:
  - - Landed on worktree branch `worktree-agent-a6c1528fd4b8d474e`, commit ee4bdec9 (rebased onto release/0.18 77fac31d first; the worktree had been created from main). Task left InProgress.
      - 11 operations in the item-reads section: `tree`, `graph`, `search`, `inbox`, `mine`, `blocked`, `workload`, `items.refs`, `items.comments`, `items.subentities.list`, `items.subentities.show`; `sq show <id>` reuses `items.show` with an id-only request. `json_field = "items"` on the 8 array commands (guard list extended).
      - DTOs in `_api/_dto/_tree.py`, `_graph.py`, `_search.py`, `_queues.py`, `_refs.py`, `_comments.py`, `_subentities.py`; handlers in `_services/_item_read_ops.py` (`ItemReadOpsMixin`, first `Service` base), projections in `_services/_item_read_dto.py`; renderers in `_cli/_render/` `_tree`, `_graph` (dot and Mermaid serializers moved here from `_services/_refs.py`), `_search`, `_queues`, `_refs`, `_comments` (shared with `_render/_items.py`), `_subentities`.
      - Folded into one call: tree's hidden count, `--json` blocked flags and `--sort`; the inbox/mine slug check; the item existence/type check on refs, comments and sub-entity reads (those verbs and the sub-entity listing and kind group now only parse in the item callback).
      - Display: tree nodes (rendered priority, dimmed, anchor note, pronouns per `[display] pronouns`), graph nodes (rendered priority, edge text, ref kind label), search hits, queue rows (`status_code`), mine rows (`matched` cell), workload rows, refs rows (kind label), sub-entities (kind name/label/plural/heading, summary table); `columns` on mine and workload.
    - Proof: scratch squad (custom `incident` type via override with a badge field, labelled attributes and its own sub-entity kind and ref kind; sub-entity discussions; pronouns on a role and an operator; a partial-read copy with a broken symlink), 227 command lines across plain and FORCE_COLOR before/after: 194 byte-identical, 29 `--json` documents differ only by added `display` keys (every old key kept, in order, with its value), partial reads still exit 4 after printing.
    - Tests: 0 added (1571 passed before and after). Edited, keys added only: the `--json` cases of blocked, workload, tree, graph, search, show, inbox, mine, refs, `<kinds>` and `<kind> show`, now compared as ordered text; guard lists `ALLOWED` (json_field) and `EXTRA_ALLOWED` (`ItemFields`, `MineRow`).
    - Falsified, each red then restored: tree node field order swapped, refs `in` key renamed, graph `edge_label` dropped, mine `matched` emptied, a `json_field` on graph, `MineRow` out of `EXTRA_ALLOWED`, a `_workflow` import in a renderer, the refs binding removed.
    - Deviations:
      - `sq show <id>` now prints labelled attributes in its panel, as `sq <type> <n> show` already does (it was on the old `print_item` path, which lacked them). The only human-output change.
      - `ItemOpsMixin`'s bases gain `CollabMixin` (between `ItemsMixin` and `SubentitiesMixin`) so the MRO stays consistent with `ImportMixin`; `_item_ops._badge_pairs` became `badge_pairs`; `_dto/_items.py` gains the `ItemFields` base under `ItemRow` (fields unchanged); `_item_dto.subentity_display` split out of `subentity_dto`.
      - Sub-entity requests carry `kind`, so a stale verb under a renamed kind keeps its refusal; the sub-entity group resolves the item in the store for its verbs not yet on operations (TASK-1229 removes that).
      - The mine table's priority cell uses the declared field's badge, as `list` does; an item whose type no longer declares `priority` but stores one now shows the raw code there (tree and graph keep the same-name fallback).
      - The `_services` pending list does not shrink: `_main.py`, `_items.py` and `_common.py` still have unmoved commands.
    - Adopter-visible, for @tech-writer: `display` on the `--json` rows of tree, graph, search, inbox, mine, blocked, workload, refs, `<kinds>` and `<kind> show`; labelled attributes in `sq show <id>`. CLAUDE.md now has 15 `Service` bases and should name `_item_read_ops`/`_item_read_dto`. Stale code comments in `clients/vscode/src/domain/graphDiagrams.ts` point at `_services/_refs.py` for the Mermaid helpers, now in `_cli/_render/_graph.py`.
- [2026-10-29T01:02:33Z] `reviewer` Paul Reviewer:
  - Reviewed on REV-1235: F13 (medium, stale sub-entity read verbs crash under a renamed kind), F14 (low, display.priority and the mine/list vs tree/graph priority rule, @architect), F15 (low, display.pronouns unasserted). Parity otherwise byte-identical or additive-only across 190+ command lines. @python-dev
- [2026-10-29T01:14:04Z] `python-dev` Elias Python:
  - Round 2 for REV-1235 F13, F14, F15, commit b55fdf1f on worktree-agent-a6c1528fd4b8d474e (on release/0.18 a8081afe). Gates: pyright 0, ruff clean, tests/meta+cli+check 1607 passed (no new cases; two existing tree cases extended). Removed provisional display key: `display.priority` on tree and graph nodes. @reviewer
- [2026-10-29T05:27:28Z] `manager` Catherine Manager:
  - Done 2026-10-29: its REV-1235 findings are Verified or deferred with a home; full suite 1634 passed on ed499a68.
<!-- sq:discussion:end -->
