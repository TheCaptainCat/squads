---
id: TASK-602
sequence_id: 602
type: task
title: 'VS Code: add category filter to the search QuickPick'
status: InReview
parent: FEAT-570
author: tech-lead
assignee: typescript-dev
priority: medium
created_at: '2026-07-22T13:00:58Z'
updated_at: '2026-07-22T18:42:44Z'
---
<!-- sq:body -->
Implements FEAT-570 US3 (VS Code QuickPick filter). Add a category dimension to the search QuickPick filtering, alongside the existing type/status narrowing. Depends on TASK-600 (category plumbing).

## VISUAL — requires operator dev-host visual acceptance
Adds a filter control to the QuickPick UX. Lands **InReview**; operator (Pierre) verifies on the Windows `code` CLI dev-host before Done.

## Scope
- `clients/vscode/src/domain/searchFilterArgs.ts`: add `category: string | null` to `SearchNarrowing` (and `NO_NARROWING`), and have `buildSearchFilterArgs` append `--category <value>` when set — matching the `sq list --category` flag TASK-597 adds server-side (single-valued, omitted when null, same shape as `--type`/`--status`).
- `clients/vscode/src/searchQuickPick.ts`: surface a category picker in the QuickPick filter flow consistent with the existing type/status pickers; category options are the fixed three-member catalog.

## Acceptance
- Selecting a category narrows results via the server-side `--category` flag (no client-side re-filtering).
- Clearing the category omits the flag.
- Extension unit tests for `buildSearchFilterArgs` with/without category.
- Operator dev-host visual sign-off before Done.

## Gates
Extension: its own compile + lint + tests. Leave `sq check` clean.

## Role colour
QuickPick result rows pick up role.color -> ThemeColor rendering (neutral fallback) via the roles-catalog join, consistent with the tree/records views; no is_open/terminal reads remain. Depends on FEAT-605.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 602 add-subtask "<title>"`; track with `sq task 602 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:48:24Z] Ada Typescript:
  - domain/searchFilterArgs.ts: SearchNarrowing/NO_NARROWING gain category: string | null; buildSearchFilterArgs appends --category <value> when set, omitted when null, same single-valued shape as --type/--status, AND-composed with the others.
  - searchQuickPick.ts: added a third title-bar button (CATEGORY_FILTER_BUTTON) + pickCategory(), consistent with the existing pickType/pickStatus flow; the category options are the fixed three-member roster/work/records vocabulary (not fetched from a catalog — it's a closed axis, unlike type/status). Title bar reflects the active category narrowing alongside type/status.
  - Gate: tsc/eslint/prettier/vitest all green (386 tests, incl. updated test/searchFilterArgs.test.ts with/without category cases). Awaiting @op-pierre's dev-host visual pass — check: the search QuickPick's third title-bar icon opens a category picker (roster/work/records + 'All categories'), selecting one narrows results via the server-side --category flag with no client-side re-filtering, and it composes correctly with an active type/status filter.
<!-- sq:discussion:end -->
