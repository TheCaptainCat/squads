---
id: BUG-728
sequence_id: 728
type: bug
title: VS Code preview does not render sub-entity discussion
status: Verified
author: qa
priority: medium
refs:
- REV-726:addresses
- BUG-727:depends-on
created_at: '2026-08-03T07:45:57Z'
updated_at: '2026-08-03T13:59:23Z'
---
<!-- sq:body -->
The item-preview webview renders the item-level discussion section, but a sub-entity pane (story/subtask/finding) shows only header + head-badges + body — no comments, so a comment added to a finding or story is invisible in the VS Code preview even once the sub-entity carries discussion data.

Site: clients/vscode/src/domain/previewDocument.ts — buildSubEntitySection composes `<div class="sq-subentity">${header}${head}${body}</div>`, with no discussion element; the TypeScript SubEntity type (clients/vscode/src/types.ts) likewise has no discussion field, so there is nothing to bind even if a discussion element were added.

Depends on BUG-727 (sub-entity discussion missing from show --json): the client's sole data source is `sq show --json`, which does not carry sub-entity discussion at all today, so this cannot be fixed by client-side work alone — it needs the JSON field to exist first, then its own rendering work (a per-sub-entity comments block, mirroring buildDiscussionHtml/renderComment) on top.

Impact: an operator working through the VS Code preview cannot see finding- or story-level discussion, the surface where this project's own convention places decisions and state-at-a-point-in-time notes.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T07:59:59Z] Olivia Lead:
  - Fixed by TASK-730, scoped as its own client-side rendering work rather than a recompile: the TypeScript sub-entity type needs the field and the pane needs a comments block.
- [2026-08-03T11:11:19Z] Ada Typescript:
  - Fixed by TASK-730 (ST1+ST2): SqSubEntity now carries an optional discussion field, isSqSubEntity accepts it as optional (skew-safe), and buildSubEntityHtml renders it via a new buildSubEntityDiscussionHtml that mirrors buildDiscussionHtml's markup/escaping/fold-away-when-empty behaviour.
  - Unit-tested (sqAdapter.test.ts, previewDocument.test.ts) incl. the older-sq skew case; tsc --noEmit and eslint (type-aware, complexity) pass at the pinned TypeScript 6.0.3. Visual confirmation in a real VS Code webview needs the operator's dev host and is not covered here.
- [2026-08-03T13:59:21Z] Pierre Chat:
  - Verified in the dev host: a comment on a story or finding is now visible in the preview.
<!-- sq:discussion:end -->
