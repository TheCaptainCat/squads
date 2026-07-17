---
id: FEAT-449
sequence_id: 449
type: feature
title: 'VS Code extension: interactive preview & display refinements'
status: Done
parent: EPIC-99
author: product-owner
refs:
- REV-448:addresses
- FEAT-100
subentities:
- local_id: US1
  title: Interactive item preview (custom webview)
  status: Done
- local_id: US2
  title: Toolbar & display controls
  status: Done
- local_id: US3
  title: Meta-items view section
  status: Done
- local_id: US4
  title: Workflow cheatsheet view
  status: Done
- local_id: US5
  title: Type-group ordering
  status: Done
- local_id: US6
  title: Extension icon swap
  status: Done
created_at: '2026-07-17T13:07:35Z'
updated_at: '2026-07-17T16:35:27Z'
---
<!-- sq:body -->
The outcome: an interactive, operator-aligned browse experience in VS Code, built on top of FEAT-100's read-only browse increment. This is the next EPIC-99 increment, seeded by REV-448 — the operator's change requests after actually using the shipped extension (findings F1-F13).

Two slices, sequenced differently:

- **Core prerequisite slice** (small, in `sq` itself): expose the per-type `order` on a machine surface (F1) and add a clean-markdown `sq workflow --raw` mode (F8). The tech lead will cut these as core tasks; the client-side stories that depend on them (type-group ordering, the cheatsheet button) can't start until they land.
- **Client slice** (the bulk of the work, in `clients/vscode/`): everything else. The architectural pivot is dropping the built-in dynamic markdown preview for an owned custom `WebviewPanel` — that single change unlocks navigable item links, middle-click-new-tab, and unfoldable mermaid graphs, none of which the built-in preview can do. The toolbar/display fixes and the meta-items view section are independent of the webview pivot and of each other.

Grouped into stories below by user-facing outcome; each story's body lists the REV-448 findings it covers.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 449 add-story "As a <role>, I want … so that …"`; track with `sq feature 449 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Interactive item preview (custom webview) |
| US2 | Done |  | Toolbar & display controls |
| US3 | Done |  | Meta-items view section |
| US4 | Done |  | Workflow cheatsheet view |
| US5 | Done |  | Type-group ordering |
| US6 | Done |  | Extension icon swap |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Interactive item preview (custom webview)

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an operator, I want the item preview in its own dedicated tab that never gets hijacked by opening another markdown file, so that it stays put while I read.

Architectural backbone: replaces the built-in markdown preview with an owned custom WebviewPanel (F9) — a dedicated tab, never stolen by another preview.

Once on a webview, render item-ID references (parent, refs) as navigable links: click opens that item's preview, middle-click opens it in a new tab (F10).

Also render two separate collapsible mermaid graphs in the preview: the item's children/subtree, and its ref graph (F11) — data already available from sq tree --json and sq graph --json.

Covers REV-448 findings: F9, F10, F11.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Toolbar & display controls

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an operator, I want display and grouping controls as one-click view-title icons instead of buried in a menu, so that browsing the tree is faster.

Numeric id sort (not lexicographic) within a group, e.g. REV-447 before REV-48 (F2).

Group-by-type becomes a view-title icon toggle instead of a quick-pick menu item (F3).

Add a show-closed view-title icon toggle that includes/excludes terminal items in the current view (F4).

Drop the group-by-open/closed grouping mode entirely — open/closed becomes the show-closed toggle plus a visual treatment, not a grouping axis (F5).

Add a collapse-all button (native showCollapseAll on the tree view registration) (F6).

When closed items are shown, render them visually de-emphasized/greyed rather than normal (F7).

Covers REV-448 findings: F2, F3, F4, F5, F6, F7.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Meta-items view section

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an operator, I want to browse role/skill/operator meta items in their own view section, so that they don't clutter the work-item tree but are still reachable.

Add a second view section within the Squads activity-bar container (contributes.views.squads gets a second entry with its own TreeDataProvider), alongside the existing work tree.

Bucket meta items under 3 fixed subfolders: Roles, Skills, Operators. Not groupable/filterable like the work tree — just the 3 buckets.

Client-only: data is sq list --json filtered to the 3 reserved types, the complement of the work tree's existing reserved-type exclusion. No new core surface.

Covers REV-448 finding: F12.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Workflow cheatsheet view

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As an operator, I want a title button that opens the workflow cheatsheet as rendered markdown, so that I can check the lifecycle rules without leaving the editor.

Add a view-title button that opens the workflow cheatsheet in the preview, reusing the existing squads: virtual-doc + markdown-preview path items already use.

Depends on the core prerequisite slice: sq workflow --raw, a clean-markdown mode (markdown tables + fenced mermaid blocks, no box-drawing) — the same gap sq show had before --raw landed.

Caveat carried from REV-448: VS Code's built-in markdown preview does not render mermaid natively, so the cheatsheet's diagrams show as fenced code blocks unless this view is later moved onto the custom webview (US1).

Covers REV-448 finding: F8.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Type-group ordering

<!-- sq:story:US5:head -->
**Status:** 🟢 Done
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As an operator, I want type groups ordered by the spec's declared per-type order, so that the tree reads epic-feature-task-bug-...-guide rather than alphabetically.

Depends on the core prerequisite slice: sq exposing the workflow spec's per-type order (ItemSpec.order) on a machine surface — no --json type catalog exposes it today.

Client then sorts type groups by that order (un-ordered types last, type-name breaks ties). Must stay spec-driven: no hardcoded type list in the client.

Covers REV-448 finding: F1.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Extension icon swap

<!-- sq:story:US6:head -->
**Status:** 🟢 Done
<!-- sq:story:US6:head:end -->

<!-- sq:story:US6:body -->
As an operator, I want the activity-bar icon to be the dedicated VS Code variant, not a repurposed mono icon, so that it looks intentional in the sidebar.

Use resources/squads-icon-vscode.svg as the activity-bar icon in package.json's viewsContainers entry.

Delete the other 6 svg variants (mono, mono-black, mono-white, color, color-black, color-white) and update .vscodeignore so the VSIX ships only squads-icon-vscode.svg from resources/.

Covers REV-448 finding: F13.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
