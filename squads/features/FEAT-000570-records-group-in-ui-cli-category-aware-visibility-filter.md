---
id: FEAT-570
sequence_id: 570
type: feature
title: 'Records group in UI/CLI: category-aware visibility + filter'
status: Done
parent: EPIC-538
author: product-owner
priority: medium
refs:
- FEAT-567
- REV-565
- FEAT-605:depends-on
subentities:
- local_id: US1
  title: category-aware default visibility + empty-view hint + --category filter
  status: Done
- local_id: US2
  title: 'TUI: records as a third tree root'
  status: InProgress
- local_id: US3
  title: 'VS Code extension: dedicated records view'
  status: InProgress
created_at: '2026-07-22T08:39:37Z'
updated_at: '2026-07-23T07:09:27Z'
---
<!-- sq:body -->
## Capability

Give both UI clients (the TUI and the VS Code extension) a `records` group, and
ensure a live-reference record (e.g. an Accepted decision) doesn't disappear from
the default view the way finished work correctly does.

## Why

After migrating a mostly-completed history, `sq tree`/`sq list` look nearly empty
by default — features `Done`, ADRs `Accepted`, bugs `Verified` are all hidden
unless `--all`. Reasonable for finished *work*, but an `Accepted` decision is the
**standing record**, not finished work — hiding the entire decision log by default
is surprising, not merely terse. This is exactly what the `records` category
disambiguates: default visibility for a status is per-role, and a records-category
item's settled statuses carry a role that stays visible while genuinely retired.

## Scope

- `sq workflow types --json` exposes each type's `category` in the catalog both
  clients already fetch (single-sourced taxonomy, no client re-derives it) — this
  is the wire-level enabler both UI changes below build on.
- **Default visibility is consumed from `role.hidden`** (from the status role model,
  FEAT-605): a status's role already carries whether it's hidden from the default
  (non-`--all`) view, so a records-category item in a settled-but-visible role
  (e.g. `Accepted`, `Published`) stays shown, while a settled-and-hidden role
  (e.g. `Superseded`, `Deprecated`, `Cancelled`) hides it — no category-specific
  visibility rule is derived here. `work`-category terminal-hiding
  (Done/Verified/Cancelled) is the same mechanism, unchanged in effect.
- **Empty-view hint**: when a default view is empty (or looks sparse) because
  hidden-role items are excluded, print/render a hint ("N closed items hidden —
  use --all") rather than silently looking broken.
- **A category filter on every filterable surface**: `sq list --category
  roster|work|records`, the TUI filter/sort popup (FEAT-525), and the VS Code
  QuickPick/tree filtering all gain a category dimension alongside today's
  type/status/priority filters.
- **TUI**: the one tree switches its grouping from the `is_meta` boolean to
  `category` — a third root (`records`) alongside `work`/`roster`. Rows also pick
  up role-colour rendering (below).
- **VS Code extension**: a dedicated records view/provider, mirroring how roster
  already has its own provider (`domain/metaView.ts`) separate from the work tree,
  plus role-colour rendering (below).

## Acceptance

- Both clients read `category` off `sq workflow types --json` — neither hardcodes
  or re-derives the roster/work/records split.
- A freshly-migrated squad with `Accepted` ADRs and `Done` features shows the ADRs
  by default and hides the features, without `--all`.
- The category filter works identically across `sq list`, the TUI popup, and the
  VS Code client.
- `sq check` clean; existing `work`/`roster` visibility behaviour unchanged.

## Dependencies

- Depends on FEAT-605 for the role-object model that drives default visibility and
  status colour.
- Depends on FEAT-567 for the `category` axis on the wire catalog.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 570 add-story "As a <role>, I want … so that …"`; track with `sq feature 570 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | category-aware default visibility + empty-view hint + --category filter |
| US2 | InProgress |  | TUI: records as a third tree root |
| US3 | InProgress |  | VS Code extension: dedicated records view |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — category-aware default visibility + empty-view hint + --category filter

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
sq list/tree default visibility is consumed from role.hidden (from the FEAT-605 role model), not re-derived here — a records-category item's settled statuses stay visible while genuinely retired ones hide.

Empty-view hint when hidden-role items are excluded from the default view.

sq list --category roster|work|records flag; wire category onto sq workflow types --json.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — TUI: records as a third tree root

<!-- sq:story:US2:head -->
**Status:** 🟡 In Progress
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Switch the browse tree's grouping from is_meta to category; add the records root alongside work/roster; wire the filter popup's category dimension.

Render row colour from the status role (FEAT-605): join status to role and map role.color intent to a Textual attribute, with a neutral fallback.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — VS Code extension: dedicated records view

<!-- sq:story:US3:head -->
**Status:** 🟡 In Progress
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
New records provider mirroring domain/metaView.ts's separation from the work tree; category filter in the QuickPick/tree.

Render status colour from the role catalog (FEAT-605): fetch the roles catalog, join status to role, and render role.color (ThemeColor with neutral fallback) in place of the removed is_open/terminal fields.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T07:09:26Z] Pierre Chat:
  - Dev-host visual pass done — happy with the Records view, the work-tree exclusion, and role-colored statuses (Accepted shows in its own colour, not greyed). Accepting. Follow-up noted: the Roster section has no filters yet — do that later.
<!-- sq:discussion:end -->
