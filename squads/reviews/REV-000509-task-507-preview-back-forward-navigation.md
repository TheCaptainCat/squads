---
id: REV-509
sequence_id: 509
type: review
title: 'TASK-507: preview back/forward navigation'
status: Approved
author: reviewer
refs:
- TASK-507:addresses
created_at: '2026-07-20T12:39:17Z'
updated_at: '2026-07-20T12:40:03Z'
---
<!-- sq:body -->
Independent review of the TASK-507 per-panel back/forward navigation history in the item-preview webview. Reviewed the pure history helper, the manager's per-panel wiring and focused-panel context-key recompute, the command registrations, the package.json contributions, and the extension-host smoke test. Did not build this work.

## Verdict
Approved — no findings.

## Coverage
- History helper (previewHistory.ts): push truncates the forward stack, no-op on re-navigating the current id, back/forward bounded, canStepBack/canStepForward/currentId correct; immutable returns. Unit tests exercise all of these (10 pass).
- Navigation wiring: real navigations (tree selection, in-panel link/@mention) push onto the originating panel's history via navigate(); goBack/goForward only move the index and re-render through the existing 'reload' path; the watcher 'patch' refresh (refreshOpenPreviews/render) never touches the histories map; onDidDispose drops the panel's history entry and clears focusedPanel.
- Per-panel context keys: recomputeContextKeys() reads focusedPanel's history and runs on navigation, back/forward, focus change (onDidChangeViewState active), new-panel open, and dispose. Correct for the multi-panel case.
- Contributions: editor/title/navigation menu + Alt+Left/Right keybindings gated to activeWebviewPanelId == squadsItemPreview (workflow panel unaffected); command enablement on the canGoBack/canGoForward context keys grays the buttons at history ends while keeping them visible.
- No regressions to scroll/mention behavior; no ticket IDs in source/test.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 509 add-finding "…" --severity medium`; track with `sq review 509 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T12:40:03Z] Paul Reviewer:
  - @manager Approved — 0 findings. Independent review of TASK-507 nav-history (previewHistory.ts + manager wiring + commands + package.json contributions + smoke test). History helper truncation/no-op/bounds correct (10 unit tests pass); navigate() pushes on real nav only, goBack/goForward move index + reload, 'patch' refresh leaves history untouched; dispose cleans up. Per-panel context-key recompute (the subtle one) is correct: recomputeContextKeys reads focusedPanel (updated on onDidChangeViewState active:true) and runs on nav/back/forward/focus-change/open/dispose, so switching between two preview tabs updates the buttons. No ticket IDs in source/test. Ready for Done.
<!-- sq:discussion:end -->
