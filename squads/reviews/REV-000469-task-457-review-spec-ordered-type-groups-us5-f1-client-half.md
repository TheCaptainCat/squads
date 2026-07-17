---
id: REV-469
sequence_id: 469
type: review
title: 'TASK-457 review: spec-ordered type groups (US5/F1 client half)'
status: Approved
author: reviewer
refs:
- TASK-457:addresses
subentities:
- local_id: F1
  title: sortTypesByOrder exported but used only by tests, not production source
  status: Fixed
  severity: low
created_at: '2026-07-17T16:18:20Z'
updated_at: '2026-07-17T16:29:05Z'
---
<!-- sq:body -->
Independent review of TASK-457 (order the tree's type groups + type-filter quick-pick by the spec's per-type `order`, consuming `sq workflow types --json`; US5, REV-448 F1 client half).

## Scope reviewed
Working-tree diff under `clients/vscode/`: `types.ts` (`SqTypeCatalogEntry`), `sqAdapter.ts` (`getTypeCatalog`/`isSqTypeCatalogEntry`), new `domain/typeOrder.ts`, `domain/listView.ts`, `domain/treeMapping.ts`, `treeDataProvider.ts` (`orderMapFrom` + parallel fetch), the four touched test files + new `test/typeOrder.test.ts`, new `test/fixtures/type-catalog.json`, and the skew-canary extension.

## Verification
- `npm run check` (tsc strict + eslint --max-warnings 0 + prettier) — PASS.
- `npm test` — 161/161 PASS.
- `npm run test:canary` — 10/10 PASS.
- Fixture faithful: `test/fixtures/type-catalog.json` is byte-for-byte the live `sq workflow types --json` output.

## Spec-driven (confirmed)
Group order and quick-pick order both flow through the single `compareTypesByOrder` comparator over a `TypeOrderMap` built from `sq workflow types --json`. No hardcoded type list or order in the client — a repo-wide scan of the ordering path found no stray type-name literals or inline `localeCompare` type sort outside `typeOrder.ts`. The quick-pick consumes `getKnownTypes()` in the order provided (no re-sort), which is the spec-ordered `knownItemTypes`.

## Comparator correctness (confirmed)
Ascending by `order`; `null`/absent sorts after every ordered type; type-name `localeCompare` tiebreak (both for equal orders and for two unordered types). `?? null` correctly preserves an explicit `order: 0`. Deterministic total order — self-equality and symmetric sign-flip hold (asserted).

## Graceful fallback (confirmed)
A failed/unreachable catalog fetch degrades to `NO_TYPE_ORDER` (empty map → every type unordered → plain type-name sort) via `orderMapFrom`, which only branches on `outcome.kind` and never throws; `buildTypeOrderMap` cannot throw. The tree never breaks on a catalog failure. The catalog is fetched in parallel (`Promise.all`) alongside the tree/list payload — one extra uncached spawn per refresh, reasonable since the spec can change between refreshes.

## Canary (confirmed)
The new `sq workflow types --json` block reuses the real adapter predicate `isSqTypeCatalogEntry`, asserts the key set (`type`/`order`/`prefix`/`reserved`), the ascending-order invariant, presence of a reserved type, and the ≥10-entry floor (7 bundled work types + 3 reserved), plus a fixture-conformance check.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 469 add-finding "…" --severity medium`; track with `sq review 469 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | sortTypesByOrder exported but used only by tests, not production source |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sortTypesByOrder exported but used only by tests, not production source

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
domain/typeOrder.ts exports sortTypesByOrder(types, orderMap), but production source never calls it — listView.ts and treeMapping.ts both sort inline with .sort((a, b) => compareTypesByOrder(orderMap, a, b)). Only test/typeOrder.test.ts uses the wrapper. It is a thin, correct helper (delegates to the comparator under test), so this is purely a hygiene note: either route the two inline sorts through sortTypesByOrder to DRY the pattern, or drop the export. Non-blocking; does not affect behaviour or the gate.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-17T16:29:05Z] Ada Typescript:
  - Fixed: routed listView.ts's distinctTypes and treeMapping.ts's distinctTypesInTree through sortTypesByOrder, folded into TASK-464.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T16:19:04Z] Paul Reviewer:
  - Recommended verdict: APPROVE. Spec-driven ordering, comparator correctness, and graceful fallback all confirmed; npm run check + 161/161 unit + 10/10 canary green; the committed type-catalog fixture is byte-identical to live `sq workflow types --json`.
  - One low, non-blocking finding (F1): `sortTypesByOrder` is exported but only tests use it — DRY or drop, reviewer's discretion, safe to land as-is or defer. No blocking findings.
  - Leaving the review status at InReview for the approver — not self-approving (per process). @tech-lead / @manager for the verdict call.
<!-- sq:discussion:end -->
