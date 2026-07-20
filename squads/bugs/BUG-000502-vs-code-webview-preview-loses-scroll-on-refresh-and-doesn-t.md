---
id: BUG-502
sequence_id: 502
type: bug
title: VS Code webview preview loses scroll on refresh and doesn't reset to top on
  navigation
status: Verified
author: manager
created_at: '2026-07-20T10:38:17Z'
updated_at: '2026-07-20T12:23:42Z'
---
<!-- sq:body -->
Symptom: the item-preview webview mishandles scroll on two events (analogous to the tree collapse in the earlier tree-view bug).

1) On auto-refresh (the .squads.json watcher → refreshOpenPreviews), the preview jumps back to the top / loses the reader's scroll position. Refresh re-renders by reassigning panel.webview.html wholesale (itemPreviewManager.ts ~257/294), which reloads the webview and resets scroll. Expected: a same-item refresh preserves scroll position.

2) On NAVIGATION to a different item (clicking an item link, opening another item into the reused panel), the preview should scroll back to the TOP — a new item should start at its top, not inherit the previous item's scroll offset.

Fix must distinguish the two: same-item refresh = preserve scroll; navigate-to-new-item = reset to top. Likely approach: stop clobbering .html on refresh — update content via postMessage and restore the saved scroll (webview getState/setState), and on navigation explicitly scroll to top. Files: clients/vscode/src/itemPreviewManager.ts + the preview HTML builder (buildPreviewHtml).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T10:38:34Z] Pierre Chat:
  - Reported live: the webview also resets on refresh; and it should scroll back to the top on navigation.
- [2026-07-20T10:57:50Z] Ada Typescript:
  - Root cause: refreshOpenPreviews reassigned panel.webview.html on every same-item refresh, reloading the webview page (scroll resets to 0), with no distinction from navigating to a different item.
  - Fix: render() now takes 'reload' | 'patch'. refreshOpenPreviews uses 'patch' — postMessage(UpdateContentMessage) with fresh article/sub-entities/discussion HTML, patched into stable #sq-article/#sq-subentities/#sq-discussion mounts via innerHTML (no page reload, scroll untouched), then re-runs mermaid via a re-callable window.__sqRenderMermaid. Every navigation path (new panel, tree click, link click) keeps 'reload' (fresh webview.html), which now explicitly does window.scrollTo(0, 0) on parse.
  - Files: clients/vscode/src/itemPreviewManager.ts (render mode split), clients/vscode/src/domain/previewDocument.ts (buildArticleHtml, mount ids, patch listener, re-callable mermaid render), clients/vscode/src/domain/previewMessages.ts (UPDATE_CONTENT_COMMAND/UpdateContentMessage).
  - Verified: npm run typecheck clean, npm test 287 passed (incl. new coverage for mount points/patch listener/explicit scrollTo), npm run test:e2e clean exit 0. eslint OOMs locally on a clean tree (known env issue, unrelated to this change) — CI is the authoritative lint gate. @manager
- [2026-07-20T12:23:41Z] Pierre Chat:
  - Verified live: scroll position holds across refresh; navigating to another item lands at the top.
<!-- sq:discussion:end -->
