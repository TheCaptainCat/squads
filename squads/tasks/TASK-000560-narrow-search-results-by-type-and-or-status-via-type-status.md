---
id: TASK-560
sequence_id: 560
type: task
title: Narrow search results by type and/or status via --type/--status pass-through
status: Done
parent: FEAT-537
author: tech-lead
assignee: typescript-dev
created_at: '2026-07-21T23:19:30Z'
updated_at: '2026-07-21T23:56:24Z'
---
<!-- sq:body -->
Type/status narrowing for the search QuickPick (US2). The filters map straight to `sq search`'s `--type`/`--status` and AND-compose with the query text server-side — no client-side re-matching.

## Scope
- Add type and status narrowing controls to the search QuickPick (e.g. QuickPick buttons / a companion pick, or the `onDidTriggerButton` affordance) that let the user set an active type and/or status.
- Translate the active narrowing into filter args passed through the TASK-558 `getSearch` filter-args parameter: `--type <type>` and/or `--status <status>`, composed with the query text exactly as the CLI composes them.
- Source the available type and status vocabularies from the existing catalog adapters (`getTypeCatalog` / `getStatusesCatalog`) rather than hardcoding a type or status list.
- Changing a filter re-runs the query through the same submit/debounce path as TASK-559 (busy indicator, last-wins), it does not re-filter the already-returned list.

## Grounding / constraints
- TypeScript. The CLI `--type`/`--status` options are SINGLE-valued (last value wins if repeated), so narrowing is one type and/or one status at a time — pass-through only, do not attempt multi-value OR semantics the engine does not support.
- Absolutely no client-side re-matching or post-filtering of results: the filters are passed to `sq search` and the returned rows are rendered as-is.
- Reuse the pure filter-args builder seam from TASK-559; keep the args-composition logic pure and unit-testable, separate from vscode wiring.

## Acceptance
- Setting a type and/or status re-runs the search with the corresponding `--type`/`--status` args AND-composed with the query; clearing them returns to the unfiltered query.
- The type/status choices come from the spec catalogs, not a hardcoded list.
- vitest unit tests (vitest) assert the filter-args builder produces the exact `--type`/`--status` argv for: type only, status only, both, and neither; and that no client re-matching is applied (given rows are passed through unchanged).
- No sq/ticket IDs in source or test names.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 560 add-subtask "<title>"`; track with `sq task 560 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T23:36:29Z] Ada Typescript:
  - Type/status narrowing wired as QuickPick title-bar buttons (companion pick, vocab from getTypeCatalog/getStatusesCatalog, reserved types excluded); domain/searchFilterArgs.ts builds the --type/--status argv, unit-tested for type-only/status-only/both/neither. Gates green.
<!-- sq:discussion:end -->
