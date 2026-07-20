---
id: BUG-503
sequence_id: 503
type: bug
title: 'VS Code webview: @<slug> mentions should link to the role sheet with hover
  details'
status: Verified
author: manager
created_at: '2026-07-20T10:38:18Z'
updated_at: '2026-07-20T12:23:46Z'
---
<!-- sq:body -->
In the item-preview webview, item references (ITEM-XXX / [ITEM-XXX]) already render as clickable links that navigate to that item's preview. Role @mentions do not.

Make @<slug> (role mentions in discussion comments, e.g. @manager, @tech-lead) render as links too: clicking opens that role's sheet (the role item's preview), and the hover/title text shows role details (name/title, and useful specifics from the role).

Mirror the existing ITEM-XXX linkifier + click→navigate message path. Resolve <slug> to its ROLE item for the target + hover. Files: clients/vscode/src/itemPreviewManager.ts + the preview HTML builder (buildPreviewHtml) where ITEM-XXX linkification lives; the message handler (domain/previewMessages) for the click→navigate route.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T10:38:36Z] Pierre Chat:
  - Reported live: like [ITEM-XXX] are links, @<slug> should link to the role sheet with details in the hover text.
- [2026-07-20T10:58:00Z] Ada Typescript:
  - Root cause: item-preview markdown rendering only linkified ITEM-XXX-shaped ids (markdown.ts's ITEM_ID_PATTERN); @<slug> role mentions in discussion comments had no linkification path at all.
  - Fix: new domain/roleDirectory.ts builds a slug -> {id, hoverText} RoleDirectory from a fresh 'sq list -t role --json' fetch each render (mirrors badgeCatalog.ts's catalog-join/degrade-gracefully shape). markdown.ts adds MENTION_PATTERN (@ + lowercase-hyphen slug) and threads an optional 'roles' param through linkifyPlainText/renderInline/every block renderer alongside currentId; a resolved slug becomes the exact same <a class="sq-item-link" data-item-id="ROLE-n"> anchor ITEM-XXX links use (so it reuses the existing click->navigate message path with no new message type), with a title attribute carrying the role's name/slug/mission for the hover. An unresolved slug is left as plain text.
  - Files: clients/vscode/src/domain/roleDirectory.ts (new), clients/vscode/src/domain/markdown.ts (MENTION_PATTERN + roles threading), clients/vscode/src/domain/previewDocument.ts (roles pass-through in dossier/discussion/sub-entity rendering), clients/vscode/src/itemPreviewManager.ts (role-list fetch + NO_ROLE_DIRECTORY degrade).
  - Verified: npm run typecheck clean, npm test 287 passed (new roleDirectory.test.ts + markdown.test.ts/previewDocument.test.ts coverage for resolved/unresolved slugs, hover text, and threading through bold/paragraph/comment/sub-entity bodies), npm run test:e2e clean exit 0. eslint OOMs locally on a clean tree (known env issue) — CI is the authoritative lint gate. @manager
- [2026-07-20T12:23:44Z] Pierre Chat:
  - Verified live: @<slug> mentions render as links to the role sheet with details in the hover.
<!-- sq:discussion:end -->
