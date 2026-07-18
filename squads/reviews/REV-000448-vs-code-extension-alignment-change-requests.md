---
id: REV-448
sequence_id: 448
type: review
title: 'VS Code extension alignment: change requests'
status: Approved
author: reviewer
refs:
- EPIC-99
- FEAT-100
subentities:
- local_id: F1
  title: Order type groups by the spec's per-type order field
  status: Verified
  severity: medium
- local_id: F2
  title: Item id sort is lexicographic, not numeric (REV-447 before REV-48)
  status: Verified
  severity: medium
- local_id: F3
  title: 'Group-by-type: make it a view-title icon, not a menu item'
  status: Verified
  severity: medium
- local_id: F4
  title: 'Show-closed: a view-title icon toggle'
  status: Verified
  severity: medium
- local_id: F5
  title: Remove group-by-open/closed
  status: Verified
  severity: medium
- local_id: F6
  title: Add a collapse-all button
  status: Verified
  severity: low
- local_id: F7
  title: Closed items rendered greyed/dimmed in the list
  status: Verified
  severity: medium
- local_id: F8
  title: Title button to open the workflow cheatsheet in the preview
  status: Verified
  severity: medium
- local_id: F9
  title: Item preview gets hijacked (dynamic md preview) — use locked preview or custom
    webview
  status: Verified
  severity: medium
- local_id: F10
  title: Navigable item links in the preview, middle-click opens a new tab (needs
    webview)
  status: Verified
  severity: medium
- local_id: F11
  title: 'Unfoldable mermaid graphs in the preview: item children + item refs, separate
    (needs webview)'
  status: Verified
  severity: medium
- local_id: F12
  title: Second view section for meta items (role/skill/operator) under 3 fixed subfolders
  status: Verified
  severity: medium
- local_id: F13
  title: Use squads-icon-vscode.svg as the extension icon; delete the other svg variants
  status: Verified
  severity: low
- local_id: F14
  title: Display the item's discussion/comments in the preview
  status: Verified
  severity: medium
- local_id: F15
  title: Preview omits the item's sub-entities (stories/subtasks/findings)
  status: Verified
  severity: high
- local_id: F16
  title: Webview panels should show the squads icon in their tab
  status: Verified
  severity: low
- local_id: F17
  title: Watch .squads.json to auto-refresh views + preview (local squads)
  status: Verified
  severity: medium
- local_id: F18
  title: Roster items should not display an assignee
  status: Verified
  severity: low
- local_id: F19
  title: Show priority/severity collection badges in the item hover
  status: Verified
  severity: medium
- local_id: F20
  title: Machine surfaces hardcode 'priority' instead of emitting all spec collections
  status: Verified
  severity: high
- local_id: F21
  title: Type icons are hardcoded to bundled names; add a custom-icon setting
  status: Verified
  severity: low
- local_id: F22
  title: Roster items fall back to circle-outline; give meta types real icons
  status: Verified
  severity: low
- local_id: F23
  title: 'Mermaid graphs: collapse by default + move directly under the frontmatter'
  status: Verified
  severity: medium
- local_id: F24
  title: Ref-graph node labels are cropped inside the node
  status: Verified
  severity: medium
- local_id: F25
  title: Graph nodes should be clickable to navigate to that item
  status: Verified
  severity: medium
- local_id: F26
  title: Activate role="active" + surface status_role so the tree can color active
    items green
  status: Verified
  severity: medium
created_at: '2026-07-17T12:19:57Z'
updated_at: '2026-07-18T21:40:27Z'
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
| F1 | 🟡 medium | Verified |  | Order type groups by the spec's per-type order field |
| F2 | 🟡 medium | Verified |  | Item id sort is lexicographic, not numeric (REV-447 before REV-48) |
| F3 | 🟡 medium | Verified |  | Group-by-type: make it a view-title icon, not a menu item |
| F4 | 🟡 medium | Verified |  | Show-closed: a view-title icon toggle |
| F5 | 🟡 medium | Verified |  | Remove group-by-open/closed |
| F6 | 🟢 low | Verified |  | Add a collapse-all button |
| F7 | 🟡 medium | Verified |  | Closed items rendered greyed/dimmed in the list |
| F8 | 🟡 medium | Verified |  | Title button to open the workflow cheatsheet in the preview |
| F9 | 🟡 medium | Verified |  | Item preview gets hijacked (dynamic md preview) — use locked preview or custom webview |
| F10 | 🟡 medium | Verified |  | Navigable item links in the preview, middle-click opens a new tab (needs webview) |
| F11 | 🟡 medium | Verified |  | Unfoldable mermaid graphs in the preview: item children + item refs, separate (needs webview) |
| F12 | 🟡 medium | Verified |  | Second view section for meta items (role/skill/operator) under 3 fixed subfolders |
| F13 | 🟢 low | Verified |  | Use squads-icon-vscode.svg as the extension icon; delete the other svg variants |
| F14 | 🟡 medium | Verified |  | Display the item's discussion/comments in the preview |
| F15 | 🟠 high | Verified |  | Preview omits the item's sub-entities (stories/subtasks/findings) |
| F16 | 🟢 low | Verified |  | Webview panels should show the squads icon in their tab |
| F17 | 🟡 medium | Verified |  | Watch .squads.json to auto-refresh views + preview (local squads) |
| F18 | 🟢 low | Verified |  | Roster items should not display an assignee |
| F19 | 🟡 medium | Verified |  | Show priority/severity collection badges in the item hover |
| F20 | 🟠 high | Verified |  | Machine surfaces hardcode 'priority' instead of emitting all spec collections |
| F21 | 🟢 low | Verified |  | Type icons are hardcoded to bundled names; add a custom-icon setting |
| F22 | 🟢 low | Verified |  | Roster items fall back to circle-outline; give meta types real icons |
| F23 | 🟡 medium | Verified |  | Mermaid graphs: collapse by default + move directly under the frontmatter |
| F24 | 🟡 medium | Verified |  | Ref-graph node labels are cropped inside the node |
| F25 | 🟡 medium | Verified |  | Graph nodes should be clickable to navigate to that item |
| F26 | 🟡 medium | Verified |  | Activate role="active" + surface status_role so the tree can color active items green |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Order type groups by the spec's per-type order field

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
When grouping by type, order the type groups by the workflow spec's per-type `order` (ItemSpec.order; default epic=10/feature=20/task=30/bug=40/decision=50/review=60/guide=70, un-ordered types last, type-name breaks ties) — not by discovery/alphabetical. REQUIRES a core change first: expose the per-type order on a machine surface (none today — no `sq workflow --json` type catalog; tree/list --json give the type name but not its order). Two parts: (1) sq exposes the per-type order additively; (2) the client sorts type groups by it. Must stay spec-driven — no hardcoded type list in the client.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-18T19:48:09Z] Paul Reviewer:
  - Delivered by TASK-450 (core sq workflow types --json + per-type order) and TASK-457 (client sorts type groups via compareTypesByOrder). Verified on disk.
- [2026-07-18T19:48:31Z] Paul Reviewer:
  - test
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Item id sort is lexicographic, not numeric (REV-447 before REV-48)

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
listView.ts:92 sorts items by `a.id.localeCompare(b.id)` — plain lexicographic, so REV-447 sorts before REV-48 ('447' < '48' char-by-char). Fix: numeric/natural collation — `a.id.localeCompare(b.id, undefined, { numeric: true })`, or better a shared `Intl.Collator(undefined, { numeric: true }).compare` comparator reused everywhere ids/sequence numbers are sorted so this can't recur. This is the item order WITHIN a group; distinct from F1 (type-GROUP order = spec order). A genuine defect, not a preference.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-18T19:48:11Z] Paul Reviewer:
  - Delivered by TASK-454 — shared Intl.Collator({numeric:true}) in idOrder.ts, used by listView + metaView. Verified on disk.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Group-by-type: make it a view-title icon, not a menu item

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Move the group-by-type control from the quick-pick/menu (squads.groupBy) to a view-title-bar icon button (contributes.menus view/title, group: navigation, with a command icon). A direct toggle in the title bar, not a menu selection.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-18T19:48:12Z] Paul Reviewer:
  - Delivered by TASK-454 — group-by-type is a view/title navigation icon (package.json), toggled:squads.groupByType. Verified on disk.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Show-closed: a view-title icon toggle

<!-- sq:finding:F4:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Add a 'show closed' toggle as a view-title icon (navigation group) that includes/excludes closed (terminal) items in the current view. Replaces having to switch to the flat group-by-state view to see closed items. Pairs with F5 (drop open/closed grouping) and F7 (closed rendered greyed).
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-18T19:48:13Z] Paul Reviewer:
  - Delivered by TASK-454 — show-closed is a view/title toggle icon driving the --all fetch. Verified on disk.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Remove group-by-open/closed

<!-- sq:finding:F5:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Drop the group-by-open/closed grouping mode entirely (the state option on squads.groupBy / the listView state grouping). Open/closed becomes a show-closed toggle (F4) plus a greyed visual treatment (F7), not a grouping axis. Group-by-type (F3) stays.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-07-18T19:48:15Z] Paul Reviewer:
  - Delivered by TASK-454 — open/closed grouping axis removed; ViewState carries only filter/groupByType/showClosed. Verified on disk.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Add a collapse-all button

<!-- sq:finding:F6:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
Add a collapse-all control to the tree. Native path: set showCollapseAll: true on the vscode.window.createTreeView registration — gives VS Code's built-in collapse-all title-bar icon, no custom command needed.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-07-18T19:48:16Z] Paul Reviewer:
  - Delivered by TASK-454 — showCollapseAll:true on createTreeView. Verified on disk.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Closed items rendered greyed/dimmed in the list

<!-- sq:finding:F7:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
When closed/terminal items are shown (via F4's toggle), render them visually de-emphasized (greyed) rather than normal — e.g. a muted ThemeColor (disabledForeground / descriptionForeground) on the TreeItem, or resourceUri + a FileDecorationProvider. Open vs closed then reads at a glance without a separate grouping.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-07-18T19:48:17Z] Paul Reviewer:
  - Delivered by TASK-454 — closed nodes rendered with disabledForeground ThemeColor. Verified on disk.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Title button to open the workflow cheatsheet in the preview

<!-- sq:finding:F8:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
Add a view-title button that opens the workflow cheatsheet as rendered markdown in the preview (reuse the squads: virtual-doc + markdown-preview path items already use). REQUIRES a core change first: sq workflow currently emits Rich terminal chrome (267 box-drawing chars; no --raw/--json/md flag) — the same problem sq show had before --raw. Add a clean-markdown mode (e.g. sq workflow --raw): markdown tables + fenced mermaid blocks, no box-drawing. Two parts: (1) core sq workflow --raw; (2) client title button + open in preview. Caveat: VS Code's built-in markdown preview does not render mermaid natively — the diagrams would show as fenced code blocks unless mermaid rendering is added.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-07-18T19:48:18Z] Paul Reviewer:
  - Delivered by TASK-456 — core sq workflow --raw (clean markdown) + client title button opening it in an owned webview with live mermaid (exceeds the md-preview caveat). Verified on disk.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Item preview gets hijacked (dynamic md preview) — use locked preview or custom webview

<!-- sq:finding:F9:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
commands.ts:94 opens the item via markdown.showPreview — VS Code's single DYNAMIC preview that follows the active editor, so opening another markdown file replaces the item preview (loses it). API question answered: there is no clean per-tab pin API — window.tabGroups is read-only, and pinning is the workbench.action.pinEditor command acting on the active tab (clunky, and not the real issue). Fixes: (a) markdown.showLockedPreviewToSide — a locked preview that stays on its own document, built-in, ~one-line swap; (b) render each item into a custom WebviewPanel the extension owns — dedicated tab, never hijacked, and would also enable mermaid rendering (pairs with F8). Recommend (a) as the cheap fix, (b) as the robust option.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-07-18T19:48:20Z] Paul Reviewer:
  - Delivered by TASK-453 — item preview is an owned createWebviewPanel; no markdown.showPreview remains. Verified on disk.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Navigable item links in the preview, middle-click opens a new tab (needs webview)

<!-- sq:finding:F10:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
In the item preview, render item-ID references (parent, refs) as navigable links: click opens that item's preview; middle-click opens it in a NEW tab. Requires the custom WebviewPanel (see F9 option b) — the built-in markdown preview cannot do item-to-item navigation or middle-click-new-tab. No new core surface: refs are already in sq show --json. The webview turns the IDs into links it intercepts and routes to open the target item (same tab on click, new webview panel on middle-click).
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-07-18T19:48:21Z] Paul Reviewer:
  - Delivered by TASK-453 — sq-item-link anchors + click/auxclick routing (middle-click opens a new panel). Verified on disk.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Unfoldable mermaid graphs in the preview: item children + item refs, separate (needs webview)

<!-- sq:finding:F11:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
In the item preview, show two collapsible (unfoldable) mermaid graphs as separate diagrams: (1) the item's children/subtree, (2) the item's ref graph. Requires the custom WebviewPanel (F9 option b) with a bundled mermaid renderer (VS Code's built-in md preview does not render mermaid). Data already exposed, no new core surface: children from sq tree <id> --json; refs from sq graph <id> --json (nested id/type/status/edge_kind/direction/children) or sq graph's fenced-mermaid output. The webview builds/renders both diagrams from those shapes.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-07-18T19:48:22Z] Paul Reviewer:
  - Delivered by TASK-453 — two collapsible sq-graph details (children subtree + ref graph). Verified on disk.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Second view section for meta items (role/skill/operator) under 3 fixed subfolders

<!-- sq:finding:F12:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
Add a second view within the Squads activity-bar container (like Explorer stacks folder-tree + outline + timeline as separate collapsible sections) — contributes.views.squads gets a second entry with its own TreeDataProvider. It hosts the meta/reserved items (role, skill, operator) that the main work tree deliberately excludes, bucketed under 3 fixed subfolders: Roles, Skills, Operators. Not groupable/filterable like work items — just the 3 buckets. Data: sq list --json filtered to the 3 reserved types (already available; this is the complement of the work tree's reserved-type exclusion). Client-only, no new core surface.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-07-18T19:48:23Z] Paul Reviewer:
  - Delivered by TASK-455 — squadsMeta 'Roster' view, META_BUCKETS (Roles/Skills/Operators) fixed buckets. Verified on disk.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Use squads-icon-vscode.svg as the extension icon; delete the other svg variants

<!-- sq:finding:F13:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F13:head:end -->

<!-- sq:finding:F13:body -->
Use resources/squads-icon-vscode.svg (viewBox 0 0 64 64, currentColor fill+stroke — activity-bar-suitable) as the activity-bar icon (package.json viewsContainers icon, currently points at squads-icon-mono.svg). Delete the other 6 svg variants: squads-icon-mono.svg, squads-icon-mono-black.svg, squads-icon-mono-white.svg, squads-icon-color.svg, squads-icon-color-black.svg, squads-icon-color-white.svg. Update .vscodeignore (its current exclusion list names the old variants) so the VSIX ships squads-icon-vscode.svg and nothing else from resources/.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-07-18T19:48:25Z] Paul Reviewer:
  - Delivered by TASK-458 — activity-bar icon points at squads-icon-vscode.svg; variant SVGs removed. Verified on disk.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Display the item's discussion/comments in the preview

<!-- sq:finding:F14:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F14:head:end -->

<!-- sq:finding:F14:body -->
The preview shows the item body but not its discussion. Render the comments as a section in the webview preview. Source: sq show <id> --json's structured 'discussion' array ([{author, ts, body}]) — already exposed (TASK-434), so NO core change; client-only. Ideally a collapsible section, consistent with the children/refs graphs. Per op-pierre.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-07-18T19:48:26Z] Paul Reviewer:
  - Delivered by TASK-464 — discussion rendered as a collapsible section in the preview webview (buildDiscussionHtml). Verified on disk.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Preview omits the item's sub-entities (stories/subtasks/findings)

<!-- sq:finding:F15:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F15:head:end -->

<!-- sq:finding:F15:body -->
The item preview renders body, mermaid graphs (children + refs), and the discussion — but not the item's **sub-entities**. `sq show <id> --json` already exposes a full `subentities` array (each with local_id, title, status, assignee, severity, story, body), yet the preview's JSON model (`types.ts`) maps only `discussion`.

Impact: sub-entities are core to how work is tracked here — a feature's stories, a task's subtasks, a review's findings. Today a feature preview hides its story breakdown, and a review preview hides its findings (this very review would render with its own findings invisible).

Desired: a preview section listing the item's sub-entities — at minimum the head badge line (status / severity / assignee / story) per entity, and ideally each entity's body as collapsible prose, mirroring the discussion section. Order follows the JSON array order.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-07-17T20:12:45Z] Pierre Chat:
  - A grave gap — where are the subitems? The whole point of an item is its breakdown.
- [2026-07-18T21:38:47Z] Catherine Manager:
  - Delivered by TASK-475 (US1) — sub-entities section in the item preview. Reviewed in REV-485, verified on disk.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — Webview panels should show the squads icon in their tab

<!-- sq:finding:F16:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F16:head:end -->

<!-- sq:finding:F16:body -->
The webview panels (item preview + workflow cheatsheet) are created via `createWebviewPanel` with no `iconPath`, so their editor tabs show VS Code's generic default icon.

Desired: set `panel.iconPath` to the squads icon so the tab is recognizable as a squads view. The asset already exists at `resources/squads-icon-vscode.svg` (the activity-bar icon) — reuse it (a single Uri, or {light, dark} if the single SVG doesn't read well in both themes).
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-07-17T20:14:00Z] Pierre Chat:
  - The sq webview should display the squads icon.
- [2026-07-18T21:38:49Z] Catherine Manager:
  - Delivered by TASK-476 (US2) — squads icon on webview panel tabs. Reviewed in REV-485.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Watch .squads.json to auto-refresh views + preview (local squads)

<!-- sq:finding:F17:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F17:head:end -->

<!-- sq:finding:F17:body -->
Today the tree views + item preview refresh only on explicit command (`extension.ts` wires a manual refresh). If work changes on disk (an agent runs `sq`, a git pull), the views go stale until the user hits refresh.

Desired: when the squad is local (its dir resolves to a `file:` path on disk), watch the index file `<squad-dir>/.squads.json` and auto-refresh on change — the activity views (`treeDataProvider`/`metaTreeDataProvider`) and any open item preview.

Feasibility (Pierre asked): yes. `vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(squadDirUri, '.squads.json'))` fires `onDidChange`/`onDidCreate`/`onDidDelete` for that single file even when the squad dir isn't the workspace root; dispose it with the extension. Debounce (the index is written atomically via os.replace, so one change lands as create+change — coalesce) and skip when the resolved squad dir isn't a local file path.

Prereq: the extension must know the squad-dir path. Discovery today only locates the `sq` binary; we need the resolved squad dir (workspace-relative walk-up mirroring `sq`'s own resolution, or a machine-surface command that reports it).
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-07-17T20:16:03Z] Pierre Chat:
  - If the squad is detected to be local, the json index should be watched to auto-refresh the activity view and the item preview.
- [2026-07-18T21:38:51Z] Catherine Manager:
  - Delivered by TASK-477 (US3) — .squads.json filesystem watcher auto-refreshes views + previews (client-side squad-dir resolution; watch-as-trigger only). REV-485.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Roster items should not display an assignee

<!-- sq:finding:F18:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F18:head:end -->

<!-- sq:finding:F18:body -->
The Roster view (roles / skills / operators) builds each item's description as `${status} · ${assignee ?? 'unassigned'}` (`domain/metaView.ts`), same as the work tree. But assignee is meaningless for meta items — every one renders a noise `· unassigned`.

Desired: drop the assignee segment from roster item descriptions. Keep status if it's useful there (roles/skills show Active), or show it alone. Only the work tree (`treeMapping`/`listView`) should carry assignee.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-07-17T20:18:41Z] Pierre Chat:
  - Roster items should not display assignee.
- [2026-07-18T21:38:53Z] Catherine Manager:
  - Delivered by TASK-478 (US4) — roster items drop the assignee segment. REV-485.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — Show priority/severity collection badges in the item hover

<!-- sq:finding:F19:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F19:head:end -->

<!-- sq:finding:F19:body -->
Request: surface collection badges (priority, severity) in the tree-item hover tooltip.

Feasibility: yes, with two caveats worth deciding up front.

State today (`domain/displayNode.ts::buildTooltip`): the tooltip lists id/type, Status, Assignee, Priority (raw code, e.g. `high`), Blocked. Severity is absent.

Caveat 1 — data reach. `sq tree --json` (the tree surface) carries priority but **not** severity (see `treeMapping` header comment). To show severity we must either add it to the tree JSON, or source badges from a richer payload (`list`/`show --json` both carry `severity`).

Caveat 2 — code vs badge glyph. All `--json` surfaces emit the bare **code** (`medium`, `high`), never the rendered badge (`🟠 high`). There is no machine surface exposing the spec's collection→badge vocabulary. So either (a) show the code as text — trivial, spec-agnostic, ships now — or (b) add a small machine surface emitting each collection's badge glyph+label so the client renders the real badge **without hardcoding emoji** (keeps it spec-driven, which matters given collections are fully customizable — ADR-323).

Recommendation: ship (a) now (add severity to the tooltip alongside priority as text); track (b) as the spec-driven badge-glyph enhancement if we want the emoji in-client. A MarkdownString tooltip would let us render glyphs richly if (b) lands.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-07-17T20:23:10Z] Pierre Chat:
  - Can we display the collection badges in the hover? Like priority and/or severity.
- [2026-07-18T21:38:55Z] Catherine Manager:
  - Delivered by TASK-482 (US8) — priority/severity collection badges in the tree hover, rendered spec-driven via the collections catalog. REV-485.
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — Machine surfaces hardcode 'priority' instead of emitting all spec collections

<!-- sq:finding:F20:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F20:head:end -->

<!-- sq:finding:F20:body -->
Principle (op-pierre): squads is a **generic workflow engine**. All spec-declared collections should be surfaced generically. If only `priority` is surfaced, that is the tell that `priority` is **hardcoded** — the surface leaks the bundled defaults instead of reflecting the active spec.

Root cause, confirmed: the engine itself is already generic — `Item.badge_value(code)`/`set_badge_value` reach any spec-declared collection (bundled `priority`/`severity` are dedicated attrs; custom collections like `impact` live in `extra`). But the **machine surface** hardcodes the bundled names:
- `sq tree --json` (`_cli/_main.py` `node()`, ~L510) emits a literal `"priority": it.priority` and nothing else — no severity, no custom collection. A spec that renames priority, drops it, or adds `impact` is misrepresented.
- `sq list --json`/`show --json` are closer (custom collections ride along in `extra`) but still split bundled (top-level `priority`/`severity`) from custom (buried in `extra`) — not a uniform, spec-driven view.

Desired: machine surfaces emit collections generically — e.g. a `badges`/`collections` map `{code: value}` built by iterating the active spec's declared collections (`badges.resolve_collection` / the WorkflowSpec), so any spec's full collection set is faithfully represented with zero hardcoded names. Clients (tree, roster, hover per F19) then render whatever the spec declares.

This is the **root cause behind F19** (severity absent from the tree surface; no glyph vocabulary). Fix F20 at the surface and F19 becomes a straight render of the generic map. Scope note: this is a core CLI/machine-surface change, not a VS Code-only change — likely wants an ADR given it touches the public JSON contract.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
- [2026-07-17T20:26:25Z] Pierre Chat:
  - A good rule: all collections should be surfaced. If only priority is, that means priority is hardcoded. Remember squads is a generic workflow engine.
- [2026-07-18T21:38:57Z] Catherine Manager:
  - Delivered by TASK-481 (US7) + ADR-474 — generic per-item badges map + sq workflow collections --json; no hardcoded collection names. REV-485.
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — Type icons are hardcoded to bundled names; add a custom-icon setting

<!-- sq:finding:F21:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F21:head:end -->

<!-- sq:finding:F21:body -->
The one place the extension hardcodes **work-item type names**: `domain/displayNode.ts` `ICON_BY_TYPE` maps the 7 bundled types (epic/feature/task/bug/decision/review/guide) to codicons. It degrades gracefully (`iconForType` → generic `DEFAULT_ICON` for anything unrecognized), so a renamed/custom type still renders — but with no distinct icon. Root cause: icons aren't on the machine surface (`sq workflow types --json` carries type/order/prefix/reserved, no icon), so the client has no spec-driven source.

(For contrast, the reserved buckets — role/skill/operator in `reservedTypes.ts` — are hardcoded *correctly*: those 3 are fixed by contract. The icon map is the only illegitimate one.)

Resolution (op-pierre): add a VS Code setting for custom type icons — e.g. `squads.typeIcons`: `{ <typeName>: <codicon-id> }`. Layer the user map over the bundled defaults, keep the graceful generic fallback for anything still unmapped. Keeps it client-side and spec-agnostic; no core change. Optionally seed the setting's description with the bundled defaults so adopters see the shape.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
- [2026-07-17T20:48:33Z] Pierre Chat:
  - We can add a setting for the custom type icons.
- [2026-07-18T21:38:59Z] Catherine Manager:
  - Delivered by TASK-479 (US5) — squads.typeIcons setting layered over bundled defaults. REV-485.
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — Roster items fall back to circle-outline; give meta types real icons

<!-- sq:finding:F22:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F22:head:end -->

<!-- sq:finding:F22:body -->
Roster items (role / skill / operator) all render as plain `circle-outline`. Cause: `domain/metaView.ts` calls `iconForType(item.type)`, but `ICON_BY_TYPE` only holds the 7 work-item types — the 3 meta types miss and fall back to `DEFAULT_ICON = 'circle-outline'`.

Desired: distinct codicons for the meta types. Unlike work-item icons (F21), the 3 reserved meta types are contractually fixed, so hardcoding these is fine — add them to `ICON_BY_TYPE` (or a small `META_ICON` map).

Suggested codicons (all built-in, silhouette-style for the people types):
- role → `hubot` (agent = a bot persona) or `account` if you prefer a neutral silhouette
- operator → `account` / `person` (a human silhouette — distinct from the agent role)
- skill → `mortar-board` (or `tools` / `star-full`)

Pierre's ask was a silhouette for the role; `account` gives the classic head-and-shoulders silhouette. Using `hubot` for role vs `account` for operator also visually encodes agent-vs-human, which reads nicely in the roster.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
- [2026-07-17T20:56:31Z] Pierre Chat:
  - Do we have some pretty icons for the roster? They're just circles. A silhouette for the role would be nice.
- [2026-07-18T21:39:01Z] Catherine Manager:
  - Delivered by TASK-478 (US4) — real codicons for role/operator/skill meta types. REV-485.
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — Mermaid graphs: collapse by default + move directly under the frontmatter

<!-- sq:finding:F23:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F23:head:end -->

<!-- sq:finding:F23:body -->
Two changes to the two mermaid graph sections (children/subtree, ref graph):

1. **Collapsed by default.** `buildGraphSection` emits `<details class="sq-graph" open>` — drop the `open` so both fold by default (user expands on demand).
2. **Position directly under the frontmatter.** Today the assembly is `<article>${bodyHtml}</article> ${graphsHtml} ${discussionHtml}` (`buildPreviewHtml`) — graphs sit at the bottom, after the whole body. Move them to just under the item's frontmatter/metadata header, above the prose body, so they're visible without scrolling.

Impl note: `bodyHtml` is currently one rendered blob (`sq show --raw`) covering header + body prose. Placing graphs 'under the frontmatter but above the body' needs the metadata header separated from the prose (render them as two fragments, inject the graphs between), or a simpler first cut: graphs immediately below `<article>`'s top. Decide the exact seam when implementing.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
- [2026-07-17T21:04:12Z] Pierre Chat:
  - The mermaid graphs should be folded by default and appear just under the frontmatter.
- [2026-07-18T21:39:03Z] Catherine Manager:
  - Delivered by TASK-480 (US6) — graphs collapsed by default + repositioned under the frontmatter. REV-485.
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — Ref-graph node labels are cropped inside the node

<!-- sq:finding:F24:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F24:head:end -->

<!-- sq:finding:F24:body -->
Many ref-graph node labels are cropped inside the node — text runs past the node boundary / gets clipped, so ids+titles aren't fully readable.

Likely root cause: mermaid inits with `securityLevel: 'strict'` (`mermaidRenderScript`) and no flowchart config. Strict mode disables htmlLabels, so labels render as non-wrapping SVG `<text>` — long labels overflow the auto-sized node and read as cropped.

Desired: labels fully contained. Options — set `mermaid.initialize({ flowchart: { htmlLabels: ..., wrappingWidth: ... }, ... })` to enable wrapping within the strict CSP if possible; or shorten node labels in the graph source (e.g. id-only nodes with the title in a tooltip); or size nodes to their text. Whatever the mechanism, no label text may be clipped.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
- [2026-07-17T21:04:13Z] Pierre Chat:
  - Many refs labels are cropped inside the node.
- [2026-07-18T21:39:06Z] Catherine Manager:
  - Delivered by TASK-480 (US6) — ref-graph node labels wrap (markdown-string labels + wrappingWidth). REV-485.
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — Graph nodes should be clickable to navigate to that item

<!-- sq:finding:F25:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F25:head:end -->

<!-- sq:finding:F25:body -->
Each node in the preview graphs (children/subtree + ref graph) should be clickable to navigate to that item's preview.

Today click interception covers only `a.sq-item-link` (markdown body links — see F10); mermaid nodes are inert.

Impl: mermaid runs with `securityLevel: 'strict'`, which disables click-callback directives — so wire it post-render instead: after `mermaid.render`, attach click handlers to the node elements (mermaid stamps node ids into the SVG) that post the item id back to the extension host over the **same channel** `a.sq-item-link` already uses (`OPEN_ITEM_COMMAND`), reusing the click/auxclick split (same-panel vs new panel) for free. Prereq: the graph source (`graph_to_mermaid`) must emit stable node ids that map to item ids. Pairs with F10/F11 (webview navigation).
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
- [2026-07-17T21:04:14Z] Pierre Chat:
  - Each item in the graph should be clickable to navigate.
- [2026-07-18T21:39:08Z] Catherine Manager:
  - Delivered by TASK-480 (US6) — graph nodes clickable to navigate. REV-485.
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->

<!-- sq:finding:F26 -->
### F26 — Activate role="active" + surface status_role so the tree can color active items green

<!-- sq:finding:F26:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F26:head:end -->

<!-- sq:finding:F26:body -->
Goal: color 'work in flight' items green in the tree — generically, keyed on a spec-declared semantic role, never on the literal status string (that would be the F20 anti-pattern).

The hook already exists: `StatusSpec.role` (a semantic-status marker, currently only `role="superseded"`, consumed by one `sq check` rule via `WorkflowSpec.status_role`). `role` and `terminal` are orthogonal fields (Superseded carries both), so this is purely additive.

Work:
1. **Spec** (`default_workflow.toml`): add `role = "active"` to the working states — `[statuses.InProgress]` (work items) and `[statuses.Active]` (roster: role/skill/operator). Both are `terminal = false` — no clash.
2. **Machine surface**: expose `status_role` on the JSON surface so the client reads it generically (a status catalog in `--json`, mirroring `sq workflow types --json`; or per-item alongside status). This is the F20 lesson again — style by the spec-declared role, not the name. Likely wants an ADR since it extends the public JSON contract.
3. **Client** (VS Code tree): map `role == "active"` → green. Composes cleanly with the F7 closed-item dimming (disjoint sets — a terminal status is never role=active).

DEFERRED (note, do not do now): consider widening `StatusSpec.role` from `str | None` to `list[str]` — a single status could legitimately carry more than one semantic role. Deferring the multi-role model keeps this increment small; revisit as its own decision (schema change → ADR) if/when a second role needs to co-exist on one status.
<!-- sq:finding:F26:body:end -->

#### Discussion

<!-- sq:finding:F26:discussion -->
- [2026-07-17T21:17:54Z] Pierre Chat:
  - The active role is good — InProgress for work items, Active for the roster. Confirmed no clash with terminal. Defer widening role to list[str].
- [2026-07-18T21:39:10Z] Catherine Manager:
  - Delivered by TASK-483 (US9 core, status_role + role=active) + TASK-484 (US10 client, active items green via the statuses catalog). ADR-474. REV-485.
<!-- sq:finding:F26:discussion:end -->
<!-- sq:finding:F26:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T12:19:59Z] Pierre Chat:
  - This review captures what I don't like and want changed in the extension after using it; it will be the base of a feature to align it with my intent.
- [2026-07-17T20:10:42Z] Pierre Chat:
  - @manager — leaving F1-F12 Open on purpose: I'll close those out with you directly, so don't auto-close them off FEAT-449. New findings (F13+) go on this same review — those are the live ones to action.
- [2026-07-17T21:20:04Z] Pierre Chat:
  - @manager — sequencing: please get the first findings (F1-F12) reviewed and approved/closed first — those are the change requests FEAT-449 already delivered. Only once that batch is settled should we start work on the new findings (F15-F26) from this session. Don't kick off the new batch before the originals are approved.
- [2026-07-18T19:50:05Z] Catherine Manager:
  - F1-F14 verified against on-disk code (reviewer pass) and closed to Verified, each citing its delivering FEAT-449 task (F1→TASK-450/457, F2-F7→TASK-454, F8→TASK-456, F9-F11→TASK-453, F12→TASK-455, F13→TASK-458, F14→TASK-464).
  - Kicking off the F15-F26 alignment batch now: product-owner to author the follow-up feature under EPIC-99 (stories from F15-F26); architect to draft the machine-surface ADRs the findings call for (F20 generic spec-declared collections surface; F26 status_role + role=active). Client work sequences after those decisions.
<!-- sq:discussion:end -->
