---
id: BUG-510
sequence_id: 510
type: bug
title: Preview back/forward title-bar buttons don't render (Alt+arrows work)
status: Verified
author: manager
refs:
- FEAT-506
created_at: '2026-07-20T12:50:49Z'
updated_at: '2026-07-20T13:36:51Z'
---
<!-- sq:body -->
In the item-preview webview, the back/forward COMMANDS work via Alt+Left/Right (so history + commands + the activeWebviewPanelId when-clause are all correct), but the title-bar arrow buttons contributed to editor/title/navigation never appear.

Config looks correct: commands squads.previewBack/Forward have icons ($(arrow-left)/$(arrow-right)) and enablement (squads.previewCanGoBack/Forward); the menu items use when: activeWebviewPanelId == squadsItemPreview (matches VIEW_TYPE 'squadsItemPreview'; same when-clause the working keybindings use).

Prime hypothesis: inline editor/title actions are HIDDEN (not grayed) when their command enablement evaluates false — so if the previewCanGoBack/Forward context keys aren't true at render/update time, the buttons never show, which also breaks the intended gray-at-ends behavior. Diagnose in the dev host: confirm whether it's enablement-hiding vs the context keys not updating vs editor/title/navigation not rendering for this webview panel. Likely fix: make the buttons visible whenever the preview is the active panel (when-clause only) and let the command no-op at history ends (as Alt+arrow already does), rather than gating visibility on enablement — or ensure the context keys are reliably set and confirm VS Code grays rather than hides.

Files: clients/vscode/package.json (commands enablement + editor/title/navigation menu), clients/vscode/src/itemPreviewManager.ts (recomputeContextKeys / focusedPanel wiring).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T12:50:55Z] Pierre Chat:
  - Reported live in the dev host: alt+arrow work, but not the title bar arrows.
- [2026-07-20T13:05:09Z] Ada Typescript:
  - Root cause: VS Code's editor/title/navigation inline toolbar HIDES a command whose 'enablement' evaluates false rather than graying it (unlike editor context menus, which show disabled items). The two commands had enablement: squads.previewCanGoBack/previewCanGoForward, so any time those context keys weren't true the buttons vanished entirely -- confirmed via VS Code's own docs (enablement applies across all menus/keybindings; only 'when' gates a menu item's visibility) plus a corroborating upstream report of inline toolbar icons not rendering their disabled visual state (microsoft/vscode#149075). Alt+Left/Right worked because the keybinding's 'when' never referenced those keys.
  - Fix: dropped 'enablement' from squads.previewBack/previewForward in package.json -- the editor/title/navigation menu entries now show purely on the existing when: activeWebviewPanelId == squadsItemPreview, same clause the working keybindings use. goBack/goForward already no-op at the ends of history (itemPreviewManager.ts's stepHistory bails when the step is a no-op), so the buttons render always and are simply inert at the ends -- matching what Alt+Left/Right already did. Removed the now-dead squads.previewCanGoBack/previewCanGoForward context-key plumbing (recomputeContextKeys + the two setContext calls) since nothing reads them anymore; kept the per-panel focusedPanel/onDidChangeViewState tracking since goBack/goForward still need it to target the correct panel's history.
  - Gray-at-ends is dropped per the priority call (render+work > cosmetic disable); can revisit with a webview-side rendered state if wanted later.
  - Verified: npm run check (tsc+lint+format) clean, npm test 297/297 green, npm run test:e2e exit 0.
  - Visual confirmation of the buttons deferred to the operator's Windows dev host per the coordinator's note -- the WSLg diagnostic instance I ran here is flagged unreliable for this and I'm not treating anything I saw there as confirmation either way.
  - @manager fix landed, ready for the operator's real dev-host check.
- [2026-07-20T13:15:33Z] Catherine Manager:
  - Reopened: dropping enablement did not surface the title-bar buttons in the operator's real Windows host. editor/title likely doesn't render contributed buttons for a plain webview panel. Pivoting to an in-preview back/forward toolbar (HTML we control), verified by screenshot rather than docs.
- [2026-07-20T13:31:58Z] Ada Typescript:
  - GROUND TRUTH, this time actually verified: launched the .vscode-test dev host, focused an open item-preview panel (BUG-510 itself), and screenshotted it via CDP. Confirmed the editor/title/navigation buttons do NOT render at all -- not even VS Code's own built-in editor-history 'Go Back'/'Go Forward' icons show for a webview panel's title area, and squads.previewBack/Forward appear nowhere in the DOM. This holds with enablement already dropped, so the earlier enablement-hiding theory was wrong: editor/title/navigation just doesn't reliably surface inline buttons for a plain createWebviewPanel panel in this VS Code build, full stop.
  - Fix (pivot, per the mandate): added a back/forward toolbar rendered INSIDE the preview HTML, top of <article> (domain/previewDocument.ts's buildHistoryToolbarHtml -- two <button> elements with a real disabled attribute at each end of history, wired via a new NavigateHistoryMessage (domain/previewMessages.ts) posted through the existing click-to-message path and handled per-panel in itemPreviewManager.ts's handleMessage/stepHistoryFor. Recomputed from the panel's live PreviewHistory on every render, reload and patch alike, so it never goes stale. Dropped the dead editor/title/navigation menu contribution from package.json; kept the squads.previewBack/previewForward commands + alt+left/alt+right keybindings as a secondary path (still work, unaffected).
  - Verified visually, not just by docs, this time: 5 screenshots at /tmp/claude-1000/-home-pchat-projects-squads/42f41fcf-bb8f-45e0-906f-b4e4f1a87e61/scratchpad/ -- diagnosis-titlebar-buttons-absent.png (title bar confirmed empty), fix-toolbar-both-disabled-fresh-panel.png (fresh panel, both dimmed), fix-toolbar-back-enabled-forward-disabled.png + fix-toolbar-midhistory-full-window.png (after navigating to a 2nd item: Back enabled, Forward dimmed), fix-toolbar-after-back-click-forward-enabled.png (clicked Back -> returned to this item, Forward now enabled, Back dimmed -- oldest entry).
  - npm run check, npm test (308/308), npm run test:e2e all green.
  - @manager fix re-landed with visual proof this time, ready for the operator's real dev-host check.
- [2026-07-20T13:36:48Z] Pierre Chat:
  - Verified live in the Windows host: the in-preview back/forward toolbar renders and works.
<!-- sq:discussion:end -->
