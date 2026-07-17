---
id: REV-448
sequence_id: 448
type: review
title: 'VS Code extension alignment: change requests'
status: Requested
author: reviewer
refs:
- EPIC-99
- FEAT-100
subentities:
- local_id: F1
  title: Order type groups by the spec's per-type order field
  status: Open
  severity: medium
- local_id: F2
  title: Item id sort is lexicographic, not numeric (REV-447 before REV-48)
  status: Open
  severity: medium
- local_id: F3
  title: 'Group-by-type: make it a view-title icon, not a menu item'
  status: Open
  severity: medium
- local_id: F4
  title: 'Show-closed: a view-title icon toggle'
  status: Open
  severity: medium
- local_id: F5
  title: Remove group-by-open/closed
  status: Open
  severity: medium
- local_id: F6
  title: Add a collapse-all button
  status: Open
  severity: low
- local_id: F7
  title: Closed items rendered greyed/dimmed in the list
  status: Open
  severity: medium
- local_id: F8
  title: Title button to open the workflow cheatsheet in the preview
  status: Open
  severity: medium
- local_id: F9
  title: Item preview gets hijacked (dynamic md preview) — use locked preview or custom
    webview
  status: Open
  severity: medium
- local_id: F10
  title: Navigable item links in the preview, middle-click opens a new tab (needs
    webview)
  status: Open
  severity: medium
- local_id: F11
  title: 'Unfoldable mermaid graphs in the preview: item children + item refs, separate
    (needs webview)'
  status: Open
  severity: medium
- local_id: F12
  title: Second view section for meta items (role/skill/operator) under 3 fixed subfolders
  status: Open
  severity: medium
- local_id: F13
  title: Use squads-icon-vscode.svg as the extension icon; delete the other svg variants
  status: Open
  severity: low
- local_id: F14
  title: Display the item's discussion/comments in the preview
  status: Open
  severity: medium
created_at: '2026-07-17T12:19:57Z'
updated_at: '2026-07-17T15:34:04Z'
---
<!-- sq:body -->
Change requests from op-pierre after using the read-only browse extension (EPIC-99 / FEAT-100). Each finding is a desired change to align the extension with the operator's intent — a preference/feature review, not a correctness review. This review is the base for a follow-up feature that implements the agreed changes.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 448 add-finding "…" --severity medium`; track with `sq review 448 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Open |  | Order type groups by the spec's per-type order field |
| F2 | 🟡 medium | Open |  | Item id sort is lexicographic, not numeric (REV-447 before REV-48) |
| F3 | 🟡 medium | Open |  | Group-by-type: make it a view-title icon, not a menu item |
| F4 | 🟡 medium | Open |  | Show-closed: a view-title icon toggle |
| F5 | 🟡 medium | Open |  | Remove group-by-open/closed |
| F6 | 🟢 low | Open |  | Add a collapse-all button |
| F7 | 🟡 medium | Open |  | Closed items rendered greyed/dimmed in the list |
| F8 | 🟡 medium | Open |  | Title button to open the workflow cheatsheet in the preview |
| F9 | 🟡 medium | Open |  | Item preview gets hijacked (dynamic md preview) — use locked preview or custom webview |
| F10 | 🟡 medium | Open |  | Navigable item links in the preview, middle-click opens a new tab (needs webview) |
| F11 | 🟡 medium | Open |  | Unfoldable mermaid graphs in the preview: item children + item refs, separate (needs webview) |
| F12 | 🟡 medium | Open |  | Second view section for meta items (role/skill/operator) under 3 fixed subfolders |
| F13 | 🟢 low | Open |  | Use squads-icon-vscode.svg as the extension icon; delete the other svg variants |
| F14 | 🟡 medium | Open |  | Display the item's discussion/comments in the preview |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Order type groups by the spec's per-type order field

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
When grouping by type, order the type groups by the workflow spec's per-type `order` (ItemSpec.order; default epic=10/feature=20/task=30/bug=40/decision=50/review=60/guide=70, un-ordered types last, type-name breaks ties) — not by discovery/alphabetical. REQUIRES a core change first: expose the per-type order on a machine surface (none today — no `sq workflow --json` type catalog; tree/list --json give the type name but not its order). Two parts: (1) sq exposes the per-type order additively; (2) the client sorts type groups by it. Must stay spec-driven — no hardcoded type list in the client.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Item id sort is lexicographic, not numeric (REV-447 before REV-48)

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
listView.ts:92 sorts items by `a.id.localeCompare(b.id)` — plain lexicographic, so REV-447 sorts before REV-48 ('447' < '48' char-by-char). Fix: numeric/natural collation — `a.id.localeCompare(b.id, undefined, { numeric: true })`, or better a shared `Intl.Collator(undefined, { numeric: true }).compare` comparator reused everywhere ids/sequence numbers are sorted so this can't recur. This is the item order WITHIN a group; distinct from F1 (type-GROUP order = spec order). A genuine defect, not a preference.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Group-by-type: make it a view-title icon, not a menu item

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Move the group-by-type control from the quick-pick/menu (squads.groupBy) to a view-title-bar icon button (contributes.menus view/title, group: navigation, with a command icon). A direct toggle in the title bar, not a menu selection.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Show-closed: a view-title icon toggle

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Add a 'show closed' toggle as a view-title icon (navigation group) that includes/excludes closed (terminal) items in the current view. Replaces having to switch to the flat group-by-state view to see closed items. Pairs with F5 (drop open/closed grouping) and F7 (closed rendered greyed).
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Remove group-by-open/closed

<!-- sq:finding:F5:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Drop the group-by-open/closed grouping mode entirely (the state option on squads.groupBy / the listView state grouping). Open/closed becomes a show-closed toggle (F4) plus a greyed visual treatment (F7), not a grouping axis. Group-by-type (F3) stays.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Add a collapse-all button

<!-- sq:finding:F6:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
Add a collapse-all control to the tree. Native path: set showCollapseAll: true on the vscode.window.createTreeView registration — gives VS Code's built-in collapse-all title-bar icon, no custom command needed.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Closed items rendered greyed/dimmed in the list

<!-- sq:finding:F7:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
When closed/terminal items are shown (via F4's toggle), render them visually de-emphasized (greyed) rather than normal — e.g. a muted ThemeColor (disabledForeground / descriptionForeground) on the TreeItem, or resourceUri + a FileDecorationProvider. Open vs closed then reads at a glance without a separate grouping.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Title button to open the workflow cheatsheet in the preview

<!-- sq:finding:F8:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
Add a view-title button that opens the workflow cheatsheet as rendered markdown in the preview (reuse the squads: virtual-doc + markdown-preview path items already use). REQUIRES a core change first: sq workflow currently emits Rich terminal chrome (267 box-drawing chars; no --raw/--json/md flag) — the same problem sq show had before --raw. Add a clean-markdown mode (e.g. sq workflow --raw): markdown tables + fenced mermaid blocks, no box-drawing. Two parts: (1) core sq workflow --raw; (2) client title button + open in preview. Caveat: VS Code's built-in markdown preview does not render mermaid natively — the diagrams would show as fenced code blocks unless mermaid rendering is added.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Item preview gets hijacked (dynamic md preview) — use locked preview or custom webview

<!-- sq:finding:F9:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
commands.ts:94 opens the item via markdown.showPreview — VS Code's single DYNAMIC preview that follows the active editor, so opening another markdown file replaces the item preview (loses it). API question answered: there is no clean per-tab pin API — window.tabGroups is read-only, and pinning is the workbench.action.pinEditor command acting on the active tab (clunky, and not the real issue). Fixes: (a) markdown.showLockedPreviewToSide — a locked preview that stays on its own document, built-in, ~one-line swap; (b) render each item into a custom WebviewPanel the extension owns — dedicated tab, never hijacked, and would also enable mermaid rendering (pairs with F8). Recommend (a) as the cheap fix, (b) as the robust option.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Navigable item links in the preview, middle-click opens a new tab (needs webview)

<!-- sq:finding:F10:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
In the item preview, render item-ID references (parent, refs) as navigable links: click opens that item's preview; middle-click opens it in a NEW tab. Requires the custom WebviewPanel (see F9 option b) — the built-in markdown preview cannot do item-to-item navigation or middle-click-new-tab. No new core surface: refs are already in sq show --json. The webview turns the IDs into links it intercepts and routes to open the target item (same tab on click, new webview panel on middle-click).
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Unfoldable mermaid graphs in the preview: item children + item refs, separate (needs webview)

<!-- sq:finding:F11:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
In the item preview, show two collapsible (unfoldable) mermaid graphs as separate diagrams: (1) the item's children/subtree, (2) the item's ref graph. Requires the custom WebviewPanel (F9 option b) with a bundled mermaid renderer (VS Code's built-in md preview does not render mermaid). Data already exposed, no new core surface: children from sq tree <id> --json; refs from sq graph <id> --json (nested id/type/status/edge_kind/direction/children) or sq graph's fenced-mermaid output. The webview builds/renders both diagrams from those shapes.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Second view section for meta items (role/skill/operator) under 3 fixed subfolders

<!-- sq:finding:F12:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
Add a second view within the Squads activity-bar container (like Explorer stacks folder-tree + outline + timeline as separate collapsible sections) — contributes.views.squads gets a second entry with its own TreeDataProvider. It hosts the meta/reserved items (role, skill, operator) that the main work tree deliberately excludes, bucketed under 3 fixed subfolders: Roles, Skills, Operators. Not groupable/filterable like work items — just the 3 buckets. Data: sq list --json filtered to the 3 reserved types (already available; this is the complement of the work tree's reserved-type exclusion). Client-only, no new core surface.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Use squads-icon-vscode.svg as the extension icon; delete the other svg variants

<!-- sq:finding:F13:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F13:head:end -->

<!-- sq:finding:F13:body -->
Use resources/squads-icon-vscode.svg (viewBox 0 0 64 64, currentColor fill+stroke — activity-bar-suitable) as the activity-bar icon (package.json viewsContainers icon, currently points at squads-icon-mono.svg). Delete the other 6 svg variants: squads-icon-mono.svg, squads-icon-mono-black.svg, squads-icon-mono-white.svg, squads-icon-color.svg, squads-icon-color-black.svg, squads-icon-color-white.svg. Update .vscodeignore (its current exclusion list names the old variants) so the VSIX ships squads-icon-vscode.svg and nothing else from resources/.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Display the item's discussion/comments in the preview

<!-- sq:finding:F14:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F14:head:end -->

<!-- sq:finding:F14:body -->
The preview shows the item body but not its discussion. Render the comments as a section in the webview preview. Source: sq show <id> --json's structured 'discussion' array ([{author, ts, body}]) — already exposed (TASK-434), so NO core change; client-only. Ideally a collapsible section, consistent with the children/refs graphs. Per op-pierre.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T12:19:59Z] Pierre Chat:
  - This review captures what I don't like and want changed in the extension after using it; it will be the base of a feature to align it with my intent.
<!-- sq:discussion:end -->
