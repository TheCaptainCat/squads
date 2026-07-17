---
id: REV-470
sequence_id: 470
type: review
title: 'TASK-464 review: discussion/comments section in item preview (F14)'
status: Approved
author: reviewer
refs:
- TASK-464:addresses
created_at: '2026-07-17T16:33:26Z'
updated_at: '2026-07-17T16:35:03Z'
---
<!-- sq:body -->
Independent review of TASK-464 (REV-448 F14): the collapsible discussion/comments section in the VS Code item-preview webview, built from `sq show <id> --json`'s `discussion` array. Bundles the REV-469 F1 hygiene fix.

## Scope reviewed
Working-tree diff under `clients/vscode/`: `types.ts` (`SqDiscussionEntry`/`SqShowJson`), `sqAdapter.ts` (`getShowJson` + `isSqShowJson`/`isSqDiscussionEntry` guards), `domain/previewDocument.ts` (`buildDiscussionHtml`/`buildCommentHtml`/`DiscussionOutcome` + `.sq-comment*` CSS), `itemPreviewManager.ts` (parallel `getShowJson` fetch + `toDiscussionOutcome` + wiring), `test/fixtures/show-json.json` and the preview/adapter tests; plus the REV-469 F1 fix in `domain/listView.ts`/`domain/treeMapping.ts`.

## Verification
- `npm run check` (tsc strict + eslint --max-warnings 0 + prettier) — PASS.
- `npm test` — 176/176 PASS.
- `npm run test:canary` — 10/10 PASS.
- Fixture faithful: `test/fixtures/show-json.json` is a real `sq show --json` capture (TASK-434's two-comment discussion), exercised end-to-end by `getShowJson`'s parse test.

## Escaping + CSP (security, comment bodies are untrusted) — PASS
- `buildCommentHtml` escapes `author` and `ts` via `escapeHtml`; the body renders through the same `renderMarkdownToHtml` the dossier body already uses. Every plain-text run in that renderer is escaped (`linkifyPlainText` -> `escapeHtml`), inline/fenced code is escaped, link text is escaped and link URLs are scheme-allowlisted (http/https/mailto or a bare item id), and `data-item-id` attribute values are regex-constrained to `[A-Z][A-Z0-9]*-\d+` — no quote/angle-bracket injection path. A comment cannot emit raw HTML.
- Comment bodies render with `renderMermaidFences` defaulting to `false`, so a ```mermaid``` fence in a comment renders as escaped `<pre><code>`, never a live diagram — no script-adjacent surface introduced by the discussion path.
- CSP is unchanged: `default-src 'none'; style-src 'nonce-…'; script-src 'nonce-…'` — no `unsafe-inline`/`unsafe-eval`. The diff only inserts the pre-rendered `discussionHtml` string into the existing document shell.

## Graceful degradation (confirmed)
- No comments (successful but empty `discussion`) -> `buildDiscussionHtml` returns `''` -> no section at all.
- Failed fetch -> `toDiscussionOutcome` yields `{ entries: null, message }` -> an inline failure message inside the same `<details>` shell the graph sections use; `render()` raises the single actionable notification only for the dossier failure, never a second one for the discussion fetch.
- The workflow-cheatsheet panel passes `discussionHtml: ''` — an item-less panel gets no discussion section.
- `getShowJson` is fetched in the same `Promise.all` as the `--raw` dossier / tree / graph — one extra parallel spawn per render, no serialization.

## REV-469 F1 fix (confirmed, no behavior change)
`domain/listView.ts::distinctTypes`/`sortedTypeEntries` and `domain/treeMapping.ts::distinctTypesInTree` now route through `sortTypesByOrder` instead of an inline `.sort(...)`. `sortTypesByOrder` wraps the identical `compareTypesByOrder` comparator, so the ordering is unchanged; `sortTypesByOrder` is now called from production source (no longer a test-only export). The typeOrder suite + full gate stay green.

Note (non-blocking, for the committer): the working tree bundles TASK-457's still-uncommitted files (`typeOrder.ts`, `type-catalog.json`, `treeDataProvider.ts`, `typeOrder.test.ts`, REV-469) with the TASK-464 changes. That is a landing-order artifact, not a defect in this task's code.

Live webview render remains CI/manual (extension-host smoke), consistent with prior tasks in this feature — acceptable.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 470 add-finding "…" --severity medium`; track with `sq review 470 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T16:34:04Z] Paul Reviewer:
  - Recommended verdict: APPROVE. TASK-464 is clean — no findings. Comment bodies (untrusted) are fully escaped through the existing dossier renderer, no injection path; CSP unchanged (default-src none, nonce-only style/script); empty->no section, failed fetch->inline message (no second notification), workflow panel->no discussion; discussion fetched in the existing Promise.all. REV-469 F1 fix routes distinctTypes/distinctTypesInTree through sortTypesByOrder (same comparator, no behavior change; now live, not a dead export). Gates: npm run check clean, npm test 176/176, test:canary 10/10. Leaving status for the approver — not self-approving.
<!-- sq:discussion:end -->
