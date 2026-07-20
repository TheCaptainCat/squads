---
id: FEAT-506
sequence_id: 506
type: feature
title: Preview back/forward navigation
status: Done
parent: EPIC-99
author: product-owner
subentities:
- local_id: US1
  title: As a user browsing linked items in the preview, I want back/forward navigation
    so I can retrace my steps
  status: Done
- local_id: US2
  title: As a user navigating the preview, I want discoverable back/forward controls
  status: Done
created_at: '2026-07-20T12:24:04Z'
updated_at: '2026-07-20T14:12:01Z'
---
<!-- sq:body -->
The item preview lets users click item references and `@<slug>` role mentions to jump to another item, but navigation is one-way: there's no way back to where you were. VS Code's own editor back/forward doesn't help — it tracks editor history, not the webview's internal item navigation.

This feature adds per-panel back/forward history to the preview webview, mirroring the familiar browser back/forward model: step back to a previously-viewed item, step forward again, with controls that are discoverable and clearly inert when there's nowhere to go. It directly complements the recently-shipped @mention linkification (BUG-503), which meaningfully increased how much users click around between items.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 506 add-story "As a <role>, I want … so that …"`; track with `sq feature 506 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As a user browsing linked items in the preview, I want back/forward navigation so I can retrace my steps |
| US2 | Done |  | As a user navigating the preview, I want discoverable back/forward controls |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a user browsing linked items in the preview, I want back/forward navigation so I can retrace my steps

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Acceptance criteria:
- Each preview panel keeps its own back/forward history of the items viewed in it, independent of other open preview panels.
- After clicking through one or more item references or @mentions, invoking Back returns the panel to the previously-viewed item; invoking Forward re-advances to the item that was left.
- Opening a new item by clicking a reference or mention while positioned back in history extends history from that point and drops the old forward stack (standard browser-style truncation) — the discarded items are not reachable via Forward afterward.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a user navigating the preview, I want discoverable back/forward controls

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Acceptance criteria:
- Back/forward controls are visible in the preview panel's title bar (or equivalent affordance) and are reachable via a keybinding, so users don't need to know a command name to find them.
- The Back control is disabled/inert when the panel is at the oldest point in its history (nothing to go back to); the Forward control is disabled/inert when at the newest point (nothing to go forward to).
- A freshly opened preview panel with no navigation yet has both controls disabled/inert.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T12:24:50Z] Nina Product:
  - @manager FEAT-506 'Preview back/forward navigation' authored under EPIC-99 (VS Code extension epic — fits cleanly, unlike the standalone BUG-503 this complements). Draft, 2 stories un-started: US1 (back/forward history, per-panel, standard truncation on new navigation), US2 (discoverable controls, disabled/inert at history ends). Ready for tech-lead breakdown when you pick it up.
- [2026-07-20T12:27:45Z] Olivia Lead:
  - @manager TASK-507 authored (Draft, not dispatched): per-panel back/forward history in the preview webview. ST1->US1 (history stack + forward-stack truncation), ST2->US2 (title-bar buttons + keybinding, inert at history ends). Body cites the real code path (itemPreviewManager.render 'reload' vs 'patch', routeForMessage/routeForTreeSelection) and flags the one non-obvious wiring point: the inert-state context keys are global, so recompute on onDidChangeViewState. Ready for tech-lead dispatch when you pick it up.
- [2026-07-20T13:36:54Z] Pierre Chat:
  - Toolbar polish (live): make the toolbar sticky, move the item title into it (left), push the back/forward nav to the right.
- [2026-07-20T14:09:19Z] Ada Typescript:
  - Toolbar polish landed (live, operator-directed), iterated in 3 rounds on top of the previously-shipped in-content back/forward toolbar (BUG-510):
  - 1) Sticky: position:sticky did NOT work in practice for this content -- verified empirically via CDP (a sticky element scrolled off-screen with the rest of the document instead of pinning, confirmed by reaching into the webview's nested iframe and reading live getBoundingClientRect during a scroll). Root cause not fully pinned down (webview host quirk), so pivoted to position:fixed relative to the preview's own viewport + a spacer div reserving its height in normal flow -- verified this DOES stay pinned while scrolling.
  - 2) Title placement: initially moved the h1 out of the body into the toolbar (truncated), then corrected per your follow-up -- the full h1 stays exactly where it was in the body (never truncated), and the toolbar shows a separate plain-text COPY that ellipsis-truncates, with the full text as its hover title= tooltip.
  - 3) Nav controls: back/forward are now plain arrow glyphs (<-/->), not text buttons, each keeping a title=/aria-label of Back/Forward for hover-tooltip + screen-reader discoverability. Disabled/dimmed at history ends via a real disabled attribute, same as before.
  - Everything else unchanged: keybindings (alt+left/right), the NavigateHistoryMessage wiring, per-panel history.
  - Verified visually at each round, not just by docs: final screenshots at /tmp/claude-1000/-home-pchat-projects-squads/42f41fcf-bb8f-45e0-906f-b4e4f1a87e61/scratchpad/ -- toolbar-final-top-icon-arrows.png (fresh panel, icon arrows, full h1 below), toolbar-final-icons-zoom-both-dimmed.png (both dimmed on fresh history), toolbar-final-scrolled-sticky.png (stays pinned after scrolling, h1 scrolled away), toolbar-final-longtitle-full-h1-in-body.png (long-title item, full multi-line h1 intact in body), toolbar-final-narrow-title-truncated.png + toolbar-final-truncated-zoom-mixed-state.png (narrowed viewport forces the toolbar's copy to ellipsis-truncate while the body h1 stays full; back enabled/forward dimmed, confirmed programmatically too), toolbar-final-narrow-scrolled-sticky.png (still pinned + truncated after scroll).
  - npm run check, npm test (313/313), npm run test:e2e all green.
  - @manager polish pass complete, ready for another live look.
<!-- sq:discussion:end -->
