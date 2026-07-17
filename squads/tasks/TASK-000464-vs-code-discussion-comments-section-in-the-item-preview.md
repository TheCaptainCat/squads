---
id: TASK-464
sequence_id: 464
type: task
title: 'VS Code: discussion/comments section in the item preview'
status: Done
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
created_at: '2026-07-17T15:34:04Z'
updated_at: '2026-07-17T16:35:03Z'
---
<!-- sq:body -->
Render the item's discussion as a collapsible section in the webview preview, from 'sq show <id> --json's 'discussion' array ([{author, ts, body}] — already exposed, no core change). Each comment: author + ISO-timestamp header, body rendered through the existing markdown.ts renderer. Reuse the webview section pattern from the children/refs graphs (TASK-453). Addresses REV-448 F14; maps to US1 (preview).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 464 add-subtask "<title>"`; track with `sq task 464 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T15:34:06Z] Pierre Chat:
  - Add comment-section display to the preview — pull the parsed discussion from sq show --json.
- [2026-07-17T16:29:30Z] Ada Typescript:
  - Added a collapsible 'Discussion' section to the item webview preview, appended after body + graph sections.
  - Fetch: new getShowJson(sq show <id> --json) adapter call (sqAdapter.ts), fetched in Promise.all alongside getRaw/getTree/getGraph in itemPreviewManager.render(); shape-guarded via isSqShowJson (checks only the discussion array, per the hand-trimmed SqShowJson type in types.ts).
  - Render: previewDocument.ts's buildDiscussionHtml renders each {author, ts, body} entry as an author+ISO-ts header + body through the existing renderMarkdownToHtml (item-id linkification incl. currentId self-link suppression, same as the dossier body); wrapped in a details.sq-graph shell matching the children/refs graph sections. Empty discussion -> no section at all (graceful); a failed fetch degrades to an inline failure message in the same shell (never silently dropped), mirroring GraphOutcome.
  - Also fixed REV-469 F1 (hygiene): routed listView.ts's distinctTypes and treeMapping.ts's distinctTypesInTree through sortTypesByOrder instead of inlining .sort(compareTypesByOrder). Marked F1 Fixed with a discussion note.
  - Unit tests: previewDocument.test.ts (buildDiscussionHtml — empty/no-section, ordering, escaping, self-link suppression, cross-item linking, failure message) against a real committed sq show --json fixture (test/fixtures/show-json.json, TASK-434's two-comment discussion); sqAdapter.test.ts (getShowJson — parsing, argv, shape/parse errors, exit-code mapping). Live webview render is CI/manual (extension-host smoke test), not covered by vitest.
  - Gate: npm run check clean (tsc strict + eslint --max-warnings 0 + prettier). npm test 176/176 (was 161, +15 net incl. hygiene/typeOrder suite already in the tree). npm run test:canary 10/10. uv run sq check clean.
  - @reviewer ready for review.
<!-- sq:discussion:end -->
