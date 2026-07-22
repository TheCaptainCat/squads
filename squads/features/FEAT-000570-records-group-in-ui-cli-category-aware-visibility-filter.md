---
id: FEAT-570
sequence_id: 570
type: feature
title: 'Records group in UI/CLI: category-aware visibility + filter'
status: Draft
parent: EPIC-538
author: product-owner
priority: medium
refs:
- FEAT-567
- REV-565
subentities:
- local_id: US1
  title: category-aware default visibility + empty-view hint + --category filter
  status: Todo
- local_id: US2
  title: 'TUI: records as a third tree root'
  status: Todo
- local_id: US3
  title: 'VS Code extension: dedicated records view'
  status: Todo
created_at: '2026-07-22T08:39:37Z'
updated_at: '2026-07-22T08:40:24Z'
---
<!-- sq:body -->
## Capability

Give both UI clients (the TUI and the VS Code extension) a `records` group, and fold
in REV-565 F9: category-aware default visibility so a live-reference record (e.g. an
Accepted decision) doesn't disappear from the default view the way finished work
correctly does.

## Why (folds REV-565 F9)

F9 (Open, medium): after migrating a mostly-completed history, `sq tree`/`sq list`
look nearly empty by default — features `Done`, ADRs `Accepted`, bugs `Verified` are
all hidden unless `--all`. Reasonable for finished *work*, but an `Accepted` decision
is the **standing record**, not finished work — hiding the entire decision log by
default is surprising, not merely terse. This is exactly what the `records` category
disambiguates: hide-when-terminal is a `work`-category default, not a `records` one.

## Scope

- `sq workflow types --json` exposes each type's `category` in the catalog both
  clients already fetch (single-sourced taxonomy, no client re-derives it) — this is
  the wire-level enabler both UI changes below build on.
- **Default visibility becomes category-aware**: a `records`-category item stays
  visible in the default (non-`--all`) view while it is in a *final-but-live* status
  (e.g. `Accepted`, `Published`) — hidden only once genuinely retired (`Superseded`,
  `Deprecated`, `Cancelled`). `work`-category terminal-hiding (Done/Verified/Cancelled)
  is unchanged. Applies to both `sq list`/`sq tree` and the two UI clients.
- **Empty-view hint**: when a default view is empty (or looks sparse) because
  terminal work items are hidden, print/render a hint ("N closed items hidden — use
  --all") rather than silently looking broken.
- **A category filter on every filterable surface**: `sq list --category
  roster|work|records`, the TUI filter/sort popup (FEAT-525), and the VS Code
  QuickPick/tree filtering all gain a category dimension alongside today's
  type/status/priority filters.
- **TUI**: the one tree switches its grouping from the `is_meta` boolean to
  `category` — a third root (`records`) alongside `work`/`roster`.
- **VS Code extension**: a dedicated records view/provider, mirroring how roster
  already has its own provider (`domain/metaView.ts`) separate from the work tree.

## Acceptance

- Both clients read `category` off `sq workflow types --json` — neither hardcodes
  or re-derives the roster/work/records split.
- A freshly-migrated squad with `Accepted` ADRs and `Done` features shows the ADRs
  by default and hides the features, without `--all`.
- The category filter works identically across `sq list`, the TUI popup, and the
  VS Code client.
- `sq check` clean; existing `work`/`roster` visibility behaviour unchanged.

## Dependencies / ordering

- **Depends on FEAT-567 (Phase A)** for the `category` axis on the wire catalog.
- **Phase C, parallelizable** against the other EPIC-538 Phase C features.
- Cross-ref: REV-565 F9 (folded in here).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 570 add-story "As a <role>, I want … so that …"`; track with `sq feature 570 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | category-aware default visibility + empty-view hint + --category filter |
| US2 | Todo |  | TUI: records as a third tree root |
| US3 | Todo |  | VS Code extension: dedicated records view |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — category-aware default visibility + empty-view hint + --category filter

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
sq list/tree hide-when-terminal becomes category-aware (records hide only when retired); empty-view hint; sq list --category flag; wire category onto sq workflow types --json.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — TUI: records as a third tree root

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Switch the browse tree's grouping from is_meta to category; add the records root alongside work/roster; wire the filter popup's category dimension.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — VS Code extension: dedicated records view

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
New records provider mirroring domain/metaView.ts's separation from the work tree; category filter in the QuickPick/tree.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
