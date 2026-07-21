---
id: TASK-558
sequence_id: 558
type: task
title: Add sq search --json adapter method + search-hit shape guard
status: Done
parent: FEAT-537
author: tech-lead
assignee: typescript-dev
created_at: '2026-07-21T23:19:29Z'
updated_at: '2026-07-21T23:56:23Z'
---
<!-- sq:body -->
Data layer for the VS Code full-text search QuickPick (US1 foundation). Read-only consumer of the existing `sq search <text> --type --status --json` contract — no new search capability, index, ranking, or searched field on either side.

## Scope
- Add a `getSearch(...)` method to `clients/vscode/src/sqAdapter.ts` that shells out to `sq search <text> --json` through the shared `runSqJson` plumbing (top-level array surface, same as `getList`/`getTree`), returning `SqOutcome<SqSearchHit[]>`.
- Add the result types to `clients/vscode/src/types.ts`: a `SqSearchHit` (`id`, `title`, `type`, `status`, `hits: readonly SqSearchHitRegion[]`) and a `SqSearchHitRegion` (`region`, `location`, `snippet` — all strings, per the CLI contract).
- Add the `isSqSearchHit` shape guard in `sqAdapter.ts` mirroring the existing guards (`isSqListItem` etc.): reject non-objects, require the string fields, require `hits` to be an array of well-formed region objects. Export it (the skew-canary reuses the real predicate, same as the other guards).
- Accept optional filter args (a `readonly string[]` appended before `--json`) so TASK-560 can layer `--type`/`--status` through the same method without a second entry point.

## Grounding / constraints
- TypeScript. Follow the existing adapter conventions exactly: outcome union, `runSqJson`, exported guard, no schema knowledge pinned in the adapter (a skew failure is an ordinary non-zero exit).
- `sq search --json` emits a top-level array of `{id,title,type,status,hits:[{region,location,snippet}]}`; hits may be empty-less but the array itself may be empty (zero matches) — that is success, not an error.
- Do NOT re-match or post-filter corpus text client-side; the adapter only parses what `sq` returned.

## Acceptance
- `getSearch` runs `sq search <text> [filters...] --json` and returns typed hits on exit 0; non-zero exits classify through the existing `classifyNonZeroExit` path unchanged.
- `isSqSearchHit` accepts a valid hit (incl. empty `hits`) and rejects malformed shapes (missing field, non-array `hits`, non-string `snippet`).
- vitest unit tests in `clients/vscode/test/sqAdapter.test.ts` style: a recording-runner argv assertion (the exact `search`/`--json` args), a success-parse case from a fixture, an empty-array (zero results) case, and a shape-mismatch → `parse-error` case. Add a `search.json` fixture under `test/fixtures/`.
- No sq/ticket IDs in source or test names; name tests by behavior.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 558 add-subtask "<title>"`; track with `sq task 558 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T23:28:00Z] Ada Typescript:
  - getSearch + isSqSearchHit added to sqAdapter.ts/types.ts, filter-args seam left for TASK-560; typecheck/lint/format/vitest all green.
<!-- sq:discussion:end -->
