---
id: REV-615
sequence_id: 615
type: review
title: 'FEAT-570 UI (US2 TUI + US3 VS Code): records group + role-join migration'
status: Approved
author: reviewer
refs:
- FEAT-570:addresses
subentities:
- local_id: F1
  title: Records view ignores squads.typeIcons override
  status: Verified
  severity: low
created_at: '2026-07-22T17:56:21Z'
updated_at: '2026-07-22T18:00:29Z'
---
<!-- sq:body -->
Independent CODE-correctness review of FEAT-570 UI — US2 (TUI) + US3 (VS Code), consuming the ADR-604 role model + category axis. Scope: uncommitted diff in src/squads/_tui, tests/tui, clients/vscode. Visual acceptance deferred to the operator dev-host pass; this review covers correctness, contract completeness, and migration soundness only.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 615 add-finding "…" --severity medium`; track with `sq review 615 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Verified |  | Records view ignores squads.typeIcons override |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Records view ignores squads.typeIcons override

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
recordsTreeDataProvider.refresh() calls buildRecordsView with a hardcoded {} for iconOverrides, so the squads.typeIcons user setting (which the work tree threads via getTypeIconOverrides) does not reach records leaves. Because decision/guide (and any custom records type) are category-excluded from the work tree, they render ONLY in the records view — so a typeIcons override for a records type has no effect anywhere in the UI. Low/non-blocking: icon-override polish, not a correctness or contract break; buildRecordsView already accepts the param. Fix = thread getTypeIconOverrides() into the provider, matching treeDataProvider.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-22T17:59:32Z] Ada Typescript:
  - Fixed: exported getTypeIconOverrides() from treeDataProvider.ts and threaded it into recordsTreeDataProvider.refresh()'s buildRecordsView call (was a hardcoded {}), matching the work-tree provider's call site exactly. Gate re-run green: tsc --noEmit, eslint --max-warnings 0, vitest run (386/386).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:56:58Z] Paul Reviewer:
  - RECOMMENDED VERDICT: Approve (approve-with-nit). F1 is low/non-blocking icon polish; no correctness, contract, or migration defect found. Manager to set final status per distinct-party rule.
  - Gates ALL GREEN. TS: tsc 0 errors; eslint 0 warnings; vitest 386/386; skew canary 16/16 against live sq. Python: pyright 0/0; ruff check + format clean; pytest tests/tui green (incl. new test_status_role_colour.py, 4 tests).
  - Focus #1 (is_open/terminal fully gone + role-join complete): CONFIRMED. No src reads is_open/terminal/is_meta off any --json payload — remaining hits are comment prose, the CLI-'terminal' word, and canary NEGATIVE assertions (not.toHaveProperty). resolveRole two-step join (status->role name->role spec) is wired through EVERY consumer: treeMapping, metaView, listView, recordsView, and both new-catalog fetches in treeDataProvider + metaTreeDataProvider + recordsTreeDataProvider. Shape guards (isSqRoleCatalogEntry, isSqTypeCatalogEntry requires category) present; canary strengthened + roles-catalog.json fixture matches live.
  - Focus #2 (closed vs hidden decouple): correct. DisplayNode.closed=role.settled, hidden=role.hidden, independent. emphasisForNode precedence blocked>hidden>colour(non-neutral)>none is correct; Accepted->in_force (settled+visible+info) renders charts.blue, NOT dimmed — verified in code + canary.
  - Focus #3 (category plumbing/records view): single-sourced via typeCategory.ts/buildCategoryMap; isReservedType is category-driven and degrades to roster-only on empty catalog (records stay in work tree, never dropped); recordsView buckets are spec-derived (recordsTypes), each declared type present, numeric-id order; search --category single-valued + omitted when null. Records provider fetches --all (records always visible).
  - Focus #4 (skew canary): real assertion of the new shape, not weakened — asserts is_open/terminal ABSENT + new category/roles shape; passes against live sq.
  - US2 (TUI): 3-root split reads spec.items[type].category (a closed 3-literal, so groups[category] cannot KeyError); roots fixed order + always present; Text.assemble bracket-safety preserved; role colour via spec.role_for, hidden dimming via spec.hidden_by_default (no re-derived sets). _filter.py threads category + spec into ItemFilter; is_empty() correctly excludes spec. _ROLE_STYLES/_GROUP_LABELS allowlisted in the mutable-state guard (_GROUP_ORDER is a tuple, needs none).
- [2026-07-22T18:00:27Z] Catherine Manager:
  - Manager verification: re-ran the VS Code gate myself (tsc --noEmit clean, eslint 0 warnings, vitest 386/386, skew-canary 16/16 vs live sq) + confirmed is_open/terminal fully gone with resolveRole joins wired through every consumer; F1 fix present in recordsTreeDataProvider.ts (getTypeIconOverrides threaded into buildRecordsView). Python side: full suite green, tui tests + colour test pass. Approving.
<!-- sq:discussion:end -->
