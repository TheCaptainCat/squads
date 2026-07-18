---
id: FEAT-471
sequence_id: 471
type: feature
title: VS Code extension alignment — batch 2 (F15-F26)
status: Done
parent: EPIC-99
author: product-owner
subentities:
- local_id: US1
  title: 'Preview: render item''s sub-entities'
  status: Done
- local_id: US2
  title: Webview panel tab icon
  status: Done
- local_id: US3
  title: Watch .squads.json for view/preview auto-refresh
  status: Done
- local_id: US4
  title: 'Roster display polish: no assignee, real meta-type icons'
  status: Done
- local_id: US5
  title: Custom type-icon VS Code setting
  status: Done
- local_id: US6
  title: 'Graph presentation: collapse, reposition, label wrap, clickable nodes'
  status: Done
- local_id: US7
  title: 'Machine surface: generic spec-driven collection badges'
  status: Done
- local_id: US8
  title: 'Hover tooltip: priority/severity badges'
  status: Done
- local_id: US9
  title: 'Machine surface: status_role for active-role coloring'
  status: Done
- local_id: US10
  title: 'Tree: color active-role items green'
  status: Done
created_at: '2026-07-18T19:51:27Z'
updated_at: '2026-07-18T21:40:28Z'
---
<!-- sq:body -->
## Scope

Second batch of VS Code extension alignment change requests from op-pierre,
recorded as REV-448 findings F15-F26 (F1-F14 delivered under FEAT-449). Each
finding has a precise "Desired" spec in the review — this feature's stories
implement them.

Most of this batch is client-only (the VS Code extension), with two
exceptions that touch the public JSON contract:

- **F20** — machine surfaces stop hardcoding `priority` and instead emit all
  spec-declared collections generically. The architect is drafting an ADR for
  this now; treat as pending ADR until it lands.
- **F26** — a new `status_role` machine surface (semantic "active" status
  role) alongside a `role = "active"` spec addition. Also pending an ADR
  (extends the public JSON contract), drafted by the architect now.

Everything else in this batch is client-only: no new core/machine surface,
implemented entirely in the VS Code extension.

## Sequencing

- F19 (hover badges, client) depends on F20 (generic collections machine
  surface, core) landing first — F19 renders whatever the F20 surface emits,
  it should not hardcode `priority`/`severity` itself.
- F26's client half (color active items green) depends on F26's own machine
  surface half (`status_role`) landing first.
- Do not start F19/F20/F26 tech-lead task breakdown before the relevant ADR
  is Accepted.

See story bodies for the finding IDs and desired behavior each one covers.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 471 add-story "As a <role>, I want … so that …"`; track with `sq feature 471 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Preview: render item's sub-entities |
| US2 | Done |  | Webview panel tab icon |
| US3 | Done |  | Watch .squads.json for view/preview auto-refresh |
| US4 | Done |  | Roster display polish: no assignee, real meta-type icons |
| US5 | Done |  | Custom type-icon VS Code setting |
| US6 | Done |  | Graph presentation: collapse, reposition, label wrap, clickable nodes |
| US7 | Done |  | Machine surface: generic spec-driven collection badges |
| US8 | Done |  | Hover tooltip: priority/severity badges |
| US9 | Done |  | Machine surface: status_role for active-role coloring |
| US10 | Done |  | Tree: color active-role items green |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Preview: render item's sub-entities

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Covers REV-448 F15 (High). The item preview currently renders body, mermaid graphs (children+refs), and discussion, but omits the item's sub-entities array (stories/subtasks/findings) even though sq show --json already exposes it fully.

Desired: a preview section listing sub-entities in JSON array order — at minimum each entity's head badge line (status/severity/assignee/story), ideally each entity's body as collapsible prose mirroring the discussion section. Client-only, no new core surface.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Webview panel tab icon

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Covers REV-448 F16 (Low). Webview panels (item preview + workflow cheatsheet) are created via createWebviewPanel with no iconPath, so their editor tabs show VS Code's generic default icon.

Desired: set panel.iconPath to the squads icon (resources/squads-icon-vscode.svg, already used as the activity-bar icon) — a single Uri, or {light, dark} if one SVG doesn't read well in both themes. Client-only, no new core surface.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Watch .squads.json for view/preview auto-refresh

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Covers REV-448 F17 (Medium). Tree views + item preview only refresh on explicit command today; if work changes on disk (an agent runs sq, a git pull) the views go stale until the user hits refresh.

Desired: when the squad is local (file: path), watch <squad-dir>/.squads.json (vscode.workspace.createFileSystemWatcher + RelativePattern) and auto-refresh the activity views and any open item preview on change; debounce (atomic os.replace writes land as create+change) and skip when the squad dir isn't a local file path; dispose the watcher with the extension.

Prereq: the extension needs the resolved squad-dir path, not just the sq binary location — per the review, mirror sq's own workspace-relative walk-up resolution or add a machine-surface command that reports it. Client-only, no new core JSON surface (the prereq is a resolution detail, not a contract change).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Roster display polish: no assignee, real meta-type icons

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
Covers REV-448 F18 (Low) and F22 (Low), both in domain/metaView.ts — the Roster view (role/skill/operator).

F18: roster item descriptions build '${status} · ${assignee ?? unassigned}', same as the work tree, but assignee is meaningless for meta items and renders noise. Desired: drop the assignee segment from roster descriptions; keep status alone. Only the work tree keeps assignee.

F22: roster items all fall back to the generic circle-outline icon because ICON_BY_TYPE only holds the 7 work-item types. Desired: give the 3 meta types real codicons (review suggests role -> hubot, operator -> account/person, skill -> mortar-board) — hardcoding these 3 is fine since role/skill/operator are contractually fixed (unlike F21's work-item types). Client-only, no new core surface.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Custom type-icon VS Code setting

<!-- sq:story:US5:head -->
**Status:** 🟢 Done
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
Covers REV-448 F21 (Low). The one place the extension hardcodes work-item type names is displayNode.ts's ICON_BY_TYPE (the 7 bundled types -> codicons); it degrades gracefully to a generic icon for anything unrecognized, but a renamed/custom type gets no distinct icon, and icons aren't on the machine surface (sq workflow types --json has no icon field).

Desired (op-pierre): add a VS Code setting, e.g. squads.typeIcons: { <typeName>: <codicon-id> }, layered over the bundled defaults, keeping the graceful generic fallback for anything still unmapped. Optionally seed the setting description with the bundled defaults so adopters see the shape. Client-only, no core change.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Graph presentation: collapse, reposition, label wrap, clickable nodes

<!-- sq:story:US6:head -->
**Status:** 🟢 Done
<!-- sq:story:US6:head:end -->

<!-- sq:story:US6:body -->
Covers REV-448 F23 (Medium), F24 (Medium), F25 (Medium) — presentation and interaction fixes to the preview's two mermaid graphs (children/subtree, ref graph). Client-only, no new core surface.

F23: graphs render <details open> at the bottom of the preview (after the whole body). Desired: collapsed by default (drop 'open'), and positioned directly under the item's frontmatter/metadata header, above the prose body, so they're visible without scrolling — needs the metadata header separated from the rendered body prose (or a simpler first cut placing graphs right below <article>'s top); exact seam is an implementation decision.

F24: node labels are cropped/clipped inside nodes, likely because mermaid's securityLevel: 'strict' disables htmlLabels so labels render as non-wrapping SVG text. Desired: no label text may be clipped — via flowchart htmlLabels/wrappingWidth config within the strict CSP if possible, shorter id-only labels with title in a tooltip, or nodes sized to their text.

F25: graph nodes aren't clickable. Desired: clicking a node navigates to that item, reusing the same open-item channel/click-vs-auxclick split already used for item links in the preview (F10/F11) — wire click handlers post-render (mermaid strict mode disables click directives) using the stable node ids that graph_to_mermaid already emits.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Machine surface: generic spec-driven collection badges

<!-- sq:story:US7:head -->
**Status:** 🟢 Done
<!-- sq:story:US7:head:end -->

<!-- sq:story:US7:body -->
Covers REV-448 F20 (High). Per op-pierre: squads is a generic workflow engine — all spec-declared collections should be surfaced generically. Today only priority is surfaced on the tree JSON; that's the tell that priority is hardcoded rather than spec-driven.

Root cause per the review: the engine (Item.badge_value/set_badge_value) is already generic, but the machine surface hardcodes bundled names — sq tree --json emits a literal priority field only (no severity, no custom collections); sq list/show --json split bundled priority/severity from custom collections buried in extra rather than a uniform view.

Desired: machine surfaces emit collections generically, e.g. a badges/collections map {code: value} built by iterating the active spec's declared collections, so any spec's full collection set is represented with zero hardcoded names.

Core CLI/machine-surface change touching the public JSON contract — pending ADR (architect drafting now). Do not scope tech-lead tasks until that ADR is Accepted. This is the root-cause fix that US8 (F19) depends on.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — Hover tooltip: priority/severity badges

<!-- sq:story:US8:head -->
**Status:** 🟢 Done
<!-- sq:story:US8:head:end -->

<!-- sq:story:US8:body -->
Covers REV-448 F19 (Medium). Request: surface priority/severity collection badges in the tree-item hover tooltip. Today's tooltip (displayNode.ts buildTooltip) shows id/type/Status/Assignee/Priority(raw code)/Blocked — severity is absent entirely.

Depends on US7 (F20): once machine surfaces emit the generic collections map, this story is a straight render of that map (whatever the spec declares) rather than hand-adding a severity field or hardcoding a badge-glyph vocabulary.

Per the review's own recommendation, an interim step (ship as text codes, not emoji glyphs) is possible before US7 lands, but the spec-driven glyph rendering the review actually asks for needs US7's collections surface first. Sequence tech-lead tasks for this story after US7's ADR is Accepted and its core change ships.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — Machine surface: status_role for active-role coloring

<!-- sq:story:US9:head -->
**Status:** 🟢 Done
<!-- sq:story:US9:head:end -->

<!-- sq:story:US9:body -->
Covers REV-448 F26's machine-surface half (Medium). Goal: color 'work in flight' items green in the tree, generically keyed on a spec-declared semantic role — never on the literal status string (the F20 anti-pattern).

Work: (1) spec — default_workflow.toml adds role = "active" to the working states ([statuses.InProgress] for work items, [statuses.Active] for roster role/skill/operator); role and terminal are orthogonal (Superseded already carries both), so this is additive. (2) machine surface — expose status_role on the JSON surface (a status catalog in --json mirroring sq workflow types --json, or per-item alongside status) so the client reads it generically.

Core change extending the public JSON contract — pending ADR (architect drafting now). Do not scope tech-lead tasks until that ADR is Accepted. US10 (the client coloring) depends on this story landing first.

Explicitly deferred per the review, not part of this story: widening StatusSpec.role from str|None to list[str]. Revisit as its own decision if/when a status needs more than one semantic role.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — Tree: color active-role items green

<!-- sq:story:US10:head -->
**Status:** 🟢 Done
<!-- sq:story:US10:head:end -->

<!-- sq:story:US10:body -->
Covers REV-448 F26's client half (Medium). Once US9's status_role surface lands, map role == "active" -> green in the VS Code tree (work tree + roster). Composes cleanly with F7's closed-item dimming (disjoint sets — a terminal status is never role=active).

Depends on US9 — do not start this story's tasks until US9's machine surface (and its pending ADR) has landed; the client must read status_role generically off the surface, never hardcode which status name means 'active'.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T21:40:28Z] Catherine Manager:
  - FEAT-471 complete: all 10 stories (US1-US10) Done, tasks 475-484 Done. Core surfaces (US7/US9) implement ADR-474; client work consumes them spec-driven. Batch-reviewed in REV-485 (Approved; F1/F3 low fixes Verified, F2 WontFix). Full Python suite green + 252 vitest + 14 skew-canary. REV-448 F15-F26 closed to Verified. Not committed (Pierre owns commits).
<!-- sq:discussion:end -->
